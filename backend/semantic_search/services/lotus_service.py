"""
Lotus Semantic Search Service

Provides semantic filtering and ranking capabilities using the Lotus library.
Integrates with Django's Publication model to enable natural language queries.
"""

import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Tuple

import pandas as pd
from django.conf import settings

from conferences.models import Publication

logger = logging.getLogger(__name__)


def _calculate_total_speedup(
    filter_stats: dict | None, topk_stats: dict | None = None
) -> float:
    """
    Calculate total speedup from filter cascade operations.

    Args:
        filter_stats: Cascade stats from filtering
        topk_stats: Cascade stats from topk ranking (not used, kept for future)

    Returns:
        Speedup factor from filter operation
    """
    if not filter_stats:
        return 1.0

    if "speedup_factor" in filter_stats:
        return filter_stats["speedup_factor"]

    return 1.0


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
        self._rm = None  # Retrieval Model (embedding)
        self._vs = None  # Vector Store (Faiss)
        self._cascade_enabled = False
        self._CascadeArgs = None
        self._ProxyModel = None
        self._index_cache: dict[str, bool] = {}
        self._predicate_cache: dict[str, str] = {}
        self._openai_client = None

    def _initialize_lotus(self):
        """
        Initialize Lotus library with LLM and cascade components.

        Performs lazy import of Lotus to avoid macOS fork() issues.
        Configures:
        - LM (Language Model): Oracle model for semantic operations
        - RM (Retrieval Model): Embedding model for cascade proxy
        - VS (Vector Store): Faiss for efficient similarity search
        """
        if self._lotus_initialized:
            return

        try:
            # Lazy import for macOS compatibility
            import lotus
            from lotus.models import LM, SentenceTransformersRM
            from lotus.vector_store import FaissVS
            from lotus.types import CascadeArgs, ProxyModel

            self._lotus = lotus

            # Store cascade types for later use
            self._CascadeArgs = CascadeArgs
            self._ProxyModel = ProxyModel

            # Get configuration from Django settings
            config = settings.LOTUS_CONFIG
            model_name = config.get("default_model", "gpt-4o")
            helper_model = config.get("helper_model")
            provider = str(config.get("llm_provider", "openai")).lower()
            use_cascade = config.get("use_cascade", True)

            # Initialize Language Model (Oracle)
            if provider == "xinference":
                # Xinference provider configuration
                api_base = settings.XINFERENCE_API_BASE or "http://localhost:9997/v1"
                api_key = settings.XINFERENCE_API_KEY or "not empty"
                max_tokens = int(config.get("max_tokens", 1024))

                self._lm = LM(
                    model=provider + "/" + model_name,
                    api_base=api_base,
                    api_key=api_key,
                    max_tokens=max_tokens,
                )
                logger.info(
                    f"Lotus LM initialized with Xinference: "
                    f"model={model_name}, api_base={api_base}"
                )
            else:
                # OpenAI-compatible provider
                self._lm = LM(model=model_name)
                logger.info(f"Lotus LM initialized: provider={provider}, model={model_name}")

            # Initialize cascade components if enabled
            if use_cascade:
                try:
                    # Initialize Retrieval Model (Embedding proxy)
                    embedding_model = config.get("embedding_model", "intfloat/e5-base-v2")
                    self._rm = SentenceTransformersRM(model=embedding_model)
                    logger.info(f"Lotus RM initialized: model={embedding_model}")

                    # Initialize Vector Store (Faiss)
                    self._vs = FaissVS()
                    logger.info("Lotus VS initialized: FaissVS")

                    # Configure lotus with all components
                    if helper_model:
                        helper_lm = LM(model=helper_model)
                        lotus.settings.configure(
                            lm=self._lm,
                            helper_lm=helper_lm,
                            rm=self._rm,
                            vs=self._vs
                        )
                        logger.info(f"Lotus configured with helper_lm={helper_model}")
                    else:
                        lotus.settings.configure(
                            lm=self._lm,
                            rm=self._rm,
                            vs=self._vs
                        )

                    self._cascade_enabled = True
                    logger.info("Lotus cascade optimization ENABLED")

                except Exception as cascade_error:
                    # Graceful fallback: cascade initialization failed
                    logger.warning(
                        f"Failed to initialize cascade components: {cascade_error}. "
                        "Falling back to non-cascade mode."
                    )

                    # Configure without cascade
                    if helper_model:
                        helper_lm = LM(model=helper_model)
                        lotus.settings.configure(lm=self._lm, helper_lm=helper_lm)
                    else:
                        lotus.settings.configure(lm=self._lm)

                    self._cascade_enabled = False
                    self._rm = None
                    self._vs = None
                    logger.info("Lotus cascade optimization DISABLED (fallback)")
            else:
                # Cascade explicitly disabled in config
                if helper_model:
                    helper_lm = LM(model=helper_model)
                    lotus.settings.configure(lm=self._lm, helper_lm=helper_lm)
                else:
                    lotus.settings.configure(lm=self._lm)

                self._cascade_enabled = False
                self._rm = None
                self._vs = None
                logger.info("Lotus cascade optimization DISABLED (config)")

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

    def _index_dataframe(self, df: pd.DataFrame, force_reindex: bool = False) -> pd.DataFrame:
        """
        Index DataFrame for cascade optimization.

        Creates Faiss index for semantic search column. Uses in-memory indexing
        with cache to avoid re-indexing the same data.

        Args:
            df: DataFrame with 'title' and 'abstract' columns
            force_reindex: Force re-indexing even if already indexed

        Returns:
            Indexed DataFrame (modified in-place, but returned for chaining)
        """
        if not self._cascade_enabled:
            logger.debug("Cascade disabled, skipping indexing")
            return df

        if df.empty:
            logger.debug("Empty DataFrame, skipping indexing")
            return df

        # Check if already indexed (using DataFrame ID as cache key)
        df_id = id(df)
        cache_key = f"df_{df_id}"

        if not force_reindex and self._index_cache.get(cache_key, False):
            logger.debug(f"DataFrame {df_id} already indexed, skipping")
            return df

        try:
            # Create temporary directory for index storage
            # LOTUS requires a directory path for sem_index
            temp_dir = tempfile.mkdtemp(prefix="lotus_index_")
            index_dir = Path(temp_dir)

            logger.info(
                f"Indexing DataFrame with {len(df)} rows for cascade optimization"
            )
            start_time = time.time()

            # Index using 'title' column
            # LOTUS will create embeddings and store in Faiss
            df = df.sem_index("title", str(index_dir))

            index_time = time.time() - start_time
            logger.info(
                f"DataFrame indexed in {index_time:.2f}s "
                f"(index_dir={index_dir})"
            )

            # Mark as indexed in cache
            self._index_cache[cache_key] = True

            return df

        except Exception as e:
            logger.error(f"Failed to index DataFrame: {e}", exc_info=True)
            logger.warning("Continuing without indexing (will use standard filtering)")
            return df

    def _apply_semantic_filter(
        self, df: pd.DataFrame, query: str
    ) -> Tuple[pd.DataFrame, dict[str, Any]]:
        """
        Apply Lotus semantic filter with cascade optimization.

        Uses embedding model proxy to pre-filter candidates before expensive
        LLM calls. Returns both filtered DataFrame and cascade statistics.

        Args:
            df: DataFrame of publications with 'title' and 'abstract' columns
            query: Natural language semantic query from user

        Returns:
            Tuple of (filtered_df, cascade_stats)
            - filtered_df: DataFrame after semantic filtering
            - cascade_stats: Dict with cascade performance metrics or None
        """
        # Generate proper LOTUS predicate using LLM
        filter_instruction = self._generate_filter_predicate(query)
        logger.info(f"User query: {query}")
        logger.info(f"Generated predicate: {filter_instruction}")

        cascade_stats = None

        if self._cascade_enabled:
            try:
                # Create CascadeArgs from settings
                config = settings.LOTUS_CONFIG
                cascade_args = self._CascadeArgs(
                    recall_target=config.get("cascade_recall_target", 0.9),
                    precision_target=config.get("cascade_precision_target", 0.9),
                    failure_probability=config.get("cascade_failure_probability", 0.2),
                    sampling_percentage=config.get("cascade_sampling_percentage", 0.5),
                    proxy_model=self._ProxyModel.EMBEDDING_MODEL
                )

                logger.info(
                    f"Applying cascade filter: "
                    f"recall={cascade_args.recall_target}, "
                    f"precision={cascade_args.precision_target}, "
                    f"proxy=EMBEDDING_MODEL"
                )

                # Apply semantic filter WITH cascade and get stats
                filtered_df, stats = df.sem_filter(
                    filter_instruction,
                    cascade_args=cascade_args,
                    return_stats=True
                )

                cascade_stats = self._process_cascade_stats(stats, "filter")

                logger.info(
                    f"Cascade filter complete: {len(filtered_df)} results, "
                    f"proxy_evals={cascade_stats.get('proxy_evaluations', 0)}, "
                    f"llm_evals={cascade_stats.get('llm_evaluations', 0)}, "
                    f"speedup={cascade_stats.get('speedup_factor', 1.0):.2f}x"
                )

            except Exception as cascade_error:
                logger.error(
                    f"Cascade filtering failed: {cascade_error}. "
                    "Falling back to standard filtering.",
                    exc_info=True
                )
                # Fallback to non-cascade
                filtered_df = df.sem_filter(filter_instruction)
                cascade_stats = {"cascade_error": str(cascade_error)}
        else:
            # Standard filtering (no cascade)
            logger.info("Applying standard filter (cascade disabled)")
            filtered_df = df.sem_filter(filter_instruction)

        logger.info(f"Filtered to {len(filtered_df)} publications")
        return filtered_df, cascade_stats

    def _process_cascade_stats(
        self, stats: dict, operation: str
    ) -> dict[str, Any]:
        """
        Process and normalize cascade statistics from LOTUS.

        Args:
            stats: Raw statistics from LOTUS cascade operation
            operation: Operation type ("filter" or "topk") for logging context

        Returns:
            Normalized statistics dictionary with calculated metrics
        """
        try:
            # Extract core metrics from LOTUS stats
            # Note: Actual keys depend on LOTUS version, adjust if needed
            proxy_evals = stats.get("proxy_evaluations", 0)
            llm_evals = stats.get("llm_evaluations", 0)
            total_evals = proxy_evals + llm_evals

            # Calculate derived metrics
            proxy_percentage = (proxy_evals / total_evals * 100) if total_evals > 0 else 0
            speedup_factor = (total_evals / max(llm_evals, 1)) if llm_evals > 0 else 1.0

            processed_stats = {
                "operation": operation,
                "proxy_evaluations": proxy_evals,
                "llm_evaluations": llm_evals,
                "total_evaluations": total_evals,
                "proxy_percentage": round(proxy_percentage, 2),
                "speedup_factor": round(speedup_factor, 2),
                "recall": stats.get("recall", None),
                "precision": stats.get("precision", None),
                "raw_stats": stats  # Include raw stats for debugging
            }

            logger.info(
                f"Cascade {operation} stats: "
                f"proxy={proxy_evals}, llm={llm_evals}, "
                f"proxy%={proxy_percentage:.1f}%, speedup={speedup_factor:.2f}x"
            )

            return processed_stats

        except Exception as e:
            logger.error(f"Failed to process cascade stats: {e}", exc_info=True)
            return {
                "operation": operation,
                "processing_error": str(e),
                "raw_stats": stats
            }

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
        self,
        publication_ids: list[str],
        query: str,
        topk: int | None = 20,
        progress_callback: Callable[[str, int], None] | None = None
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

            # Index DataFrame for cascade optimization
            df = self._index_dataframe(df)

            # Notify filtering phase starting
            if progress_callback:
                progress_callback("filtering", len(df))

            # Apply semantic filter with cascade stats
            filtered_df, filter_stats = self._apply_semantic_filter(df, query)

            # Notify reranking phase starting
            if progress_callback:
                progress_callback("reranking", len(filtered_df))

            # Apply semantic ranking (no cascade)
            if not filtered_df.empty:
                ranked_df = self._apply_semantic_topk(filtered_df, query, topk)
            else:
                ranked_df = filtered_df

            # Convert results to list of dictionaries
            results = self._dataframe_to_results(ranked_df)

            processing_time = int((time.time() - start_time) * 1000)
            logger.info(f"Semantic search completed in {processing_time}ms, found {len(results)} results")

            # Compile cascade statistics
            cascade_metadata = {}
            if self._cascade_enabled:
                cascade_metadata = {
                    "cascade_enabled": True,
                    "filter_stats": filter_stats,
                    "total_speedup": _calculate_total_speedup(filter_stats)
                }
            else:
                cascade_metadata = {"cascade_enabled": False}

            return {
                "success": True,
                "query": query,
                "total_input": len(publication_ids),
                "total_results": len(results),
                "results": results,
                "metadata": {
                    "llm_model": settings.LOTUS_CONFIG.get("default_model"),
                    "processing_time_ms": processing_time,
                    "cascade": cascade_metadata,
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
        elif "cascade" in error_message.lower() or "index" in error_message.lower():
            error_code = "CASCADE_ERROR"
            detail = f"Cascade optimization failed: {error_message}. Operation may have fallen back to standard mode."
        elif "embedding" in error_message.lower():
            error_code = "EMBEDDING_ERROR"
            detail = f"Embedding model error: {error_message}. Check embedding model configuration."
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
