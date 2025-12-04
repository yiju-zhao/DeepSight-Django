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
        self._predicate_cache: dict[str, str] = {}
        self._openai_client = None

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
            model_name = config.get("default_model", "gpt-5-nano")
            helper_model = config.get("helper_model")
            provider = str(config.get("llm_provider", "openai")).lower()

            if provider == "xinference":
                # Configure LM to talk to Xinference via OpenAI-compatible API
                api_base = settings.XINFERENCE_API_BASE or "http://localhost:9997/v1"
                api_key = settings.XINFERENCE_API_KEY or "not empty"
                max_tokens = int(config.get("max_tokens", 1024))

                self._lm = LM(
                    model=provider + "/" + model_name,
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

    def _get_openai_client(self):
        """
        Get or create OpenAI client instance (lazy initialization).

        Returns:
            OpenAI client instance

        Raises:
            ValueError: If OPENAI_API_KEY is not configured
        """
        if self._openai_client is None:
            from openai import OpenAI

            api_key = settings.OPENAI_API_KEY
            if not api_key:
                raise ValueError("OPENAI_API_KEY not configured in settings")
            self._openai_client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized for predicate generation")

        return self._openai_client

    def _generate_filter_predicate(self, user_query: str) -> str:
        """
        Use OpenAI LLM to convert user query into proper LOTUS sem_filter predicate.

        The LLM generates only the predicate part (e.g., "is about machine learning")
        which is then combined with column references: "{title} or {abstract} [predicate]"

        Args:
            user_query: Raw user query (e.g., "machine learning papers")

        Returns:
            Properly formatted LOTUS predicate (e.g., "{title} or {abstract} is about machine learning")

        Raises:
            No exceptions - falls back to simple template on any error
        """
        # Handle empty query
        if not user_query or not user_query.strip():
            return "{title} or {abstract} is not empty"

        user_query = user_query.strip()

        # Check cache first
        if user_query in self._predicate_cache:
            logger.debug(f"Using cached predicate for query: {user_query}")
            return self._predicate_cache[user_query]

        # Generate predicate using OpenAI
        try:
            client = self._get_openai_client()

            prompt = f"""You are a query translator for LOTUS semantic filtering system.

Convert the user's natural language query into a predicate phrase that completes the filter condition.

Your output will be combined with column references like: "{{title}} or {{abstract}} [YOUR OUTPUT]"

RULES:
1. Generate ONLY the predicate phrase (do NOT include column references)
2. Be specific and natural

EXAMPLES:
User query: "machine learning papers"
Output: "is about machine learning"

User query: "positive sentiment reviews"
Output: "expresses positive sentiment"

User query: "papers on deep learning for computer vision"
Output: "discusses deep learning applied to computer vision"

User query: "research requiring mathematical background"
Output: "requires knowledge of mathematics"

User query: "neural networks"
Output: "is about neural networks"

Now convert this query (output ONLY the predicate phrase):
User query: "{user_query}"
Output:"""

            response = client.chat.completions.create(
                model="gpt-5.1",
                messages=[{"role": "user", "content": prompt}],
            )

            predicate_part = response.choices[0].message.content.strip()

            # Remove quotes if LLM added them
            predicate_part = predicate_part.strip('"').strip("'")

            # Construct final predicate
            final_predicate = f"{{title}} or {{abstract}} {predicate_part}"

            # Cache the result
            self._predicate_cache[user_query] = final_predicate

            logger.info(f"Generated predicate for '{user_query}': {final_predicate}")
            return final_predicate

        except Exception as e:
            logger.warning(f"Failed to generate predicate via OpenAI, using fallback: {e}")
            # Fallback to simple template
            fallback_predicate = f"{{title}} or {{abstract}} is about {user_query}"
            self._predicate_cache[user_query] = fallback_predicate
            return fallback_predicate

    def _generate_topk_instruction(self, user_query: str) -> str:
        """
        Use OpenAI LLM to convert user query into proper LOTUS sem_topk instruction.

        The LLM generates a ranking question in the format:
        "Which {title} or {abstract} is most [criteria]?"

        Args:
            user_query: Raw user query (e.g., "machine learning papers")

        Returns:
            Properly formatted LOTUS topk instruction (e.g., "Which {title} or {abstract} is most related to machine learning?")

        Raises:
            No exceptions - falls back to simple template on any error
        """
        # Handle empty query
        if not user_query or not user_query.strip():
            return "Which {title} or {abstract} is most relevant?"

        user_query = user_query.strip()

        # Check cache first (use different cache key to distinguish from filter predicates)
        cache_key = f"topk:{user_query}"
        if cache_key in self._predicate_cache:
            logger.debug(f"Using cached topk instruction for query: {user_query}")
            return self._predicate_cache[cache_key]

        # Generate topk instruction using OpenAI
        try:
            client = self._get_openai_client()

            prompt = f"""You are a query translator for LOTUS semantic ranking system.

Convert the user's natural language query into a ranking question for selecting top-K results.

Your output will be combined with column references like: "Which {{title}} or {{abstract}} [YOUR OUTPUT]?"

RULES:
1. Generate ONLY the ranking criteria phrase (do NOT include "Which" or column references)
2. Start with "is most" or "is least" followed by the ranking dimension
3. Use comparative language (most/least related, most relevant, most exciting, etc.)
4. Focus on ranking criteria, not filtering conditions

EXAMPLES:
User query: "machine learning papers"
Output: "is most related to machine learning"

User query: "research on neural networks"
Output: "is most relevant to neural networks research"

User query: "exciting computer vision work"
Output: "is most exciting in the field of computer vision"

User query: "papers requiring mathematics"
Output: "is most focused on mathematical methods"

User query: "positive sentiment reviews"
Output: "is most positive in sentiment"

Now convert this query (output ONLY the ranking criteria phrase):
User query: "{user_query}"
Output:"""

            response = client.chat.completions.create(
                model="gpt-5.1",
                messages=[{"role": "user", "content": prompt}],
            )

            criteria_part = response.choices[0].message.content.strip()

            # Remove quotes if LLM added them
            criteria_part = criteria_part.strip('"').strip("'")

            # Construct final instruction as a ranking question
            final_instruction = f"Which {{title}} or {{abstract}} {criteria_part}?"

            # Cache the result
            self._predicate_cache[cache_key] = final_instruction

            logger.info(f"Generated topk instruction for '{user_query}': {final_instruction}")
            return final_instruction

        except Exception as e:
            logger.warning(f"Failed to generate topk instruction via OpenAI, using fallback: {e}")
            # Fallback to simple template
            fallback_instruction = f"Which {{title}} or {{abstract}} is most related to {user_query}?"
            self._predicate_cache[cache_key] = fallback_instruction
            return fallback_instruction

    def _publications_to_dataframe(self, publications: list[Publication]) -> pd.DataFrame:
        """
        Convert Publication objects to DataFrame for Lotus processing.

        Combines title and abstract into a single semantic_text field
        for semantic search.

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
            # Combine title + abstract for semantic search
            semantic_text = f"{pub.title or ''} {pub.abstract or ''}".strip()

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

        Uses LLM to generate proper LOTUS predicates from user queries.

        Args:
            df: DataFrame of publications with 'title' and 'abstract' columns
            query: Natural language semantic query from user

        Returns:
            Filtered DataFrame
        """
        # Generate proper LOTUS predicate using LLM
        filter_instruction = self._generate_filter_predicate(query)
        logger.info(f"User query: {query}")
        logger.info(f"Generated predicate: {filter_instruction}")

        filtered_df = df.sem_filter(filter_instruction)
        logger.info(f"Filtered to {len(filtered_df)} publications")
        return filtered_df

    def _apply_semantic_topk(
        self, filtered_df: pd.DataFrame, query: str, topk: int | None
    ) -> pd.DataFrame:
        """
        Apply Lotus semantic top-k ranking on a filtered DataFrame.

        Uses LLM-generated ranking instruction (e.g., "Which {title} or {abstract} is most related to X?")

        Args:
            filtered_df: DataFrame after semantic filtering
            query: Natural language semantic query from user
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

        # Generate ranking instruction using LLM
        topk_instruction = self._generate_topk_instruction(query)
        logger.info(f"Applying top-{actual_topk} ranking with instruction: {topk_instruction}")

        return filtered_df.sem_topk(topk_instruction, K=actual_topk, method="heap")

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

    def semantic_filter(
        self, publication_ids: list[str], query: str, topk: int | None = 20
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
        max_pubs = settings.LOTUS_CONFIG.get("max_publications", 10000)
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
