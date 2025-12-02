"""
Lotus Semantic Search Service

Provides semantic filtering and ranking capabilities using the Lotus library.
Integrates with Django's Publication model to enable natural language queries.
"""

import logging
import time
from typing import Any

import pandas as pd
from django.conf import settings

from conferences.models import Publication

logger = logging.getLogger(__name__)


class LotusSemanticSearchService:
    """
    Service for performing semantic search operations using Lotus library.

    Uses lazy initialization for Lotus to avoid import issues on macOS and
    improve startup time.
    """

    def __init__(self):
        """Initialize service with lazy Lotus loading."""
        self._lotus_initialized = False
        self._lotus = None
        self._lm = None

    def _initialize_lotus(self):
        """
        Initialize Lotus library with configured LLM model.

        Performs lazy import of Lotus to avoid macOS fork() issues
        and only initializes when actually needed.
        """
        if self._lotus_initialized:
            return

        try:
            # Lazy import for macOS compatibility (similar to agents/)
            import lotus
            from lotus.models import LM

            self._lotus = lotus

            # Get configuration from Django settings
            config = settings.LOTUS_CONFIG
            model_name = config.get("default_model", "gpt-4o-mini")
            helper_model = config.get("helper_model")
            provider = str(config.get("llm_provider", "openai")).lower()

            if provider == "xinference":
                # Configure LM to talk to Xinference via OpenAI-compatible API
                api_base = settings.XINFERENCE_API_BASE or "http://localhost:9997/v1"
                api_key = settings.XINFERENCE_API_KEY or "not empty"
                max_tokens = int(config.get("max_tokens", 1024))

                self._lm = LM(
                    model=model_name,
                    api_base=api_base,
                    api_key=api_key,
                    max_tokens=max_tokens,
                )
                lotus.settings.configure(lm=self._lm)

                logger.info(
                    "Lotus initialized with Xinference provider: "
                    f"model={model_name}, api_base={api_base}"
                )
            else:
                # Default OpenAI-compatible provider (e.g., OpenAI, Azure, etc.)
                self._lm = LM(model=model_name)

                if helper_model:
                    helper_lm = LM(model=helper_model)
                    lotus.settings.configure(lm=self._lm, helper_lm=helper_lm)
                else:
                    lotus.settings.configure(lm=self._lm)

                logger.info(f"Lotus initialized with provider={provider}, model={model_name}")

            self._lotus_initialized = True

        except ImportError as e:
            logger.error(f"Failed to import Lotus: {e}")
            raise ImportError("lotus-ai library is not installed. Run: pip install lotus-ai")
        except Exception as e:
            logger.error(f"Failed to initialize Lotus: {e}")
            raise RuntimeError(f"Lotus initialization failed: {str(e)}")

    def _publications_to_dataframe(self, publications: list[Publication]) -> pd.DataFrame:
        """
        Convert Publication objects to DataFrame for Lotus processing.

        Combines title, abstract, and keywords into a single semantic_text field
        for more comprehensive semantic search.

        Args:
            publications: List of Publication model instances

        Returns:
            DataFrame with columns: id, semantic_text, title, abstract, authors,
                                  keywords, rating, venue, year
        """
        if not publications:
            return pd.DataFrame()

        data = {
            "id": [],
            "semantic_text": [],
            "title": [],
            "abstract": [],
            "authors": [],
            "keywords": [],
            "rating": [],
            "venue": [],
            "year": [],
        }

        for pub in publications:
            # Combine title + abstract + keywords for semantic search
            semantic_text = f"{pub.title or ''} {pub.abstract or ''} {pub.keywords or ''}"
            semantic_text = semantic_text.strip()

            data["id"].append(str(pub.id))
            data["semantic_text"].append(semantic_text)
            data["title"].append(pub.title or "")
            data["abstract"].append(pub.abstract or "")
            data["authors"].append(pub.authors or "")
            data["keywords"].append(pub.keywords or "")
            data["rating"].append(float(pub.rating) if pub.rating else 0.0)
            data["venue"].append(pub.instance.venue.name if pub.instance and pub.instance.venue else "")
            data["year"].append(pub.instance.year if pub.instance else None)

        return pd.DataFrame(data)

    def _apply_semantic_filter(self, df: pd.DataFrame, query: str) -> pd.DataFrame:
        """
        Apply Lotus semantic filter on a publications DataFrame.

        Args:
            df: DataFrame of publications
            query: Natural language semantic query

        Returns:
            Filtered DataFrame
        """
        filter_instruction = f"{{semantic_text}} is relevant to the query: {query}"
        logger.info(f"Applying semantic filter: {filter_instruction}")

        filtered_df = df.sem_filter(filter_instruction)
        logger.info(f"Filtered to {len(filtered_df)} publications")
        return filtered_df

    def _apply_semantic_topk(
        self, filtered_df: pd.DataFrame, query: str, topk: int | None
    ) -> pd.DataFrame:
        """
        Apply Lotus semantic top-k ranking on a filtered DataFrame.

        Args:
            filtered_df: DataFrame after semantic filtering
            query: Natural language semantic query
            topk: Number of top results to keep; if None, keep all

        Returns:
            Ranked DataFrame
        """
        if filtered_df.empty:
            return filtered_df

        if topk is None:
            actual_topk = len(filtered_df)
        else:
            actual_topk = min(topk, len(filtered_df))

        topk_instruction = f"Rank {{semantic_text}} by relevance to: {query}"
        logger.info(f"Applying top-{actual_topk} ranking")

        return filtered_df.sem_topk(topk_instruction, K=actual_topk)

    def _dataframe_to_results(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """
        Convert a ranked publications DataFrame to result dictionaries.

        Args:
            df: Ranked DataFrame

        Returns:
            List of result dictionaries including relevance_score
        """
        results: list[dict[str, Any]] = []
        total = len(df)

        if total == 0:
            return results

        for position, row in enumerate(df.itertuples(index=False), start=1):
            relevance_score = 1.0 - ((position - 1) / max(total, 1)) * 0.5

            results.append(
                {
                    "id": getattr(row, "id"),
                    "title": getattr(row, "title"),
                    "abstract": getattr(row, "abstract"),
                    "authors": getattr(row, "authors"),
                    "keywords": getattr(row, "keywords"),
                    "rating": float(getattr(row, "rating")),
                    "venue": getattr(row, "venue"),
                    "year": getattr(row, "year"),
                    "relevance_score": round(relevance_score, 3),
                }
            )

        return results

    def filter_publications(
        self, publication_ids: list[str], query: str
    ) -> pd.DataFrame:
        """
        Perform semantic filtering on publications and return a DataFrame.

        This performs only filtering (no top-k selection) and is intended
        for batch/streaming workflows.
        """
        if not publication_ids:
            return pd.DataFrame()

        self._initialize_lotus()

        publications = Publication.objects.select_related("instance__venue").filter(
            id__in=publication_ids
        )
        publications_list = list(publications)

        if not publications_list:
            logger.warning(
                "No publications found for provided IDs during filter_publications",
            )
            return pd.DataFrame()

        df = self._publications_to_dataframe(publications_list)
        if df.empty:
            return df

        return self._apply_semantic_filter(df, query)

    def semantic_filter(
        self, publication_ids: list[str], query: str, topk: int | None = 50
    ) -> dict[str, Any]:
        """
        Perform semantic search on publications using Lotus.

        This is the main API method that:
        1. Loads publications by IDs
        2. Converts to DataFrame
        3. Applies Lotus semantic filtering
        4. Returns top-k ranked results

        Args:
            publication_ids: List of publication UUID strings to search within
            query: Natural language semantic query
            topk: Number of top results to return (default: 10)

        Returns:
            Dictionary containing:
                - success: bool
                - query: str (the input query)
                - total_input: int (number of input publications)
                - total_results: int (number of results after filtering)
                - results: list of dicts with publication data + relevance_score
                - metadata: dict with llm_model and processing_time_ms

        Raises:
            ValueError: If publication_ids is empty or invalid
            RuntimeError: If Lotus operations fail
        """
        start_time = time.time()

        # Validate inputs
        if not publication_ids:
            return {
                "success": True,
                "query": query,
                "total_input": 0,
                "total_results": 0,
                "results": [],
                "metadata": {
                    "llm_model": settings.LOTUS_CONFIG.get("default_model"),
                    "processing_time_ms": 0,
                },
            }

        # Check max publications limit
        max_pubs = settings.LOTUS_CONFIG.get("max_publications", 1000)
        if len(publication_ids) > max_pubs:
            logger.warning(
                f"Publication IDs count ({len(publication_ids)}) exceeds max ({max_pubs}). "
                f"Truncating to first {max_pubs}."
            )
            publication_ids = publication_ids[:max_pubs]

        try:
            # Initialize Lotus if not already done
            self._initialize_lotus()

            # Load publications from database
            publications = Publication.objects.select_related("instance__venue").filter(
                id__in=publication_ids
            )
            publications_list = list(publications)

            if not publications_list:
                logger.warning(f"No publications found for {len(publication_ids)} provided IDs")
                return {
                    "success": True,
                    "query": query,
                    "total_input": len(publication_ids),
                    "total_results": 0,
                    "results": [],
                    "metadata": {
                        "llm_model": settings.LOTUS_CONFIG.get("default_model"),
                        "processing_time_ms": int((time.time() - start_time) * 1000),
                    },
                }

            logger.info(f"Loaded {len(publications_list)} publications for semantic search")

            # Convert to DataFrame
            df = self._publications_to_dataframe(publications_list)

            if df.empty:
                return {
                    "success": True,
                    "query": query,
                    "total_input": len(publication_ids),
                    "total_results": 0,
                    "results": [],
                    "metadata": {
                        "llm_model": settings.LOTUS_CONFIG.get("default_model"),
                        "processing_time_ms": int((time.time() - start_time) * 1000),
                    },
                }

            # Apply semantic filter then ranking as separate steps
            filtered_df = self._apply_semantic_filter(df, query)

            if not filtered_df.empty:
                ranked_df = self._apply_semantic_topk(filtered_df, query, topk)
            else:
                ranked_df = filtered_df

            # Convert results to list of dictionaries
            results = self._dataframe_to_results(ranked_df)

            processing_time = int((time.time() - start_time) * 1000)
            logger.info(f"Semantic search completed in {processing_time}ms, found {len(results)} results")

            return {
                "success": True,
                "query": query,
                "total_input": len(publication_ids),
                "total_results": len(results),
                "results": results,
                "metadata": {
                    "llm_model": settings.LOTUS_CONFIG.get("default_model"),
                    "processing_time_ms": processing_time,
                },
            }

        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}", exc_info=True)
            return self._handle_lotus_error(e, query, len(publication_ids))

    def _handle_lotus_error(self, error: Exception, query: str, input_count: int) -> dict:
        """
        Handle Lotus operation errors gracefully.

        Args:
            error: The exception that occurred
            query: The semantic query that failed
            input_count: Number of input publications

        Returns:
            Error response dictionary
        """
        error_type = type(error).__name__
        error_message = str(error)

        # Categorize common errors
        if "api" in error_message.lower() or "openai" in error_message.lower():
            error_code = "LLM_API_ERROR"
            detail = "Failed to connect to LLM API. Check API key and network connection."
        elif "rate limit" in error_message.lower():
            error_code = "RATE_LIMIT_ERROR"
            detail = "LLM API rate limit exceeded. Please try again later."
        elif "timeout" in error_message.lower():
            error_code = "TIMEOUT_ERROR"
            detail = "Semantic search timed out. Try reducing the number of publications."
        else:
            error_code = "SEMANTIC_SEARCH_ERROR"
            detail = f"Semantic search failed: {error_message}"

        logger.error(
            f"Semantic search error [{error_code}]: {detail}",
            extra={"query": query, "input_count": input_count, "error_type": error_type},
        )

        return {
            "success": False,
            "query": query,
            "total_input": input_count,
            "total_results": 0,
            "results": [],
            "error": error_code,
            "detail": detail,
            "metadata": {
                "llm_model": settings.LOTUS_CONFIG.get("default_model"),
                "processing_time_ms": 0,
            },
        }


# Singleton instance (following DeepSight pattern from conferences/services.py)
lotus_semantic_search_service = LotusSemanticSearchService()
