"""
Lotus Semantic Search Service

Provides embedding-based candidate selection and LLM ranking using the Lotus
library. Integrates with Django's Publication model to enable natural
language queries.
"""

import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Tuple

import pandas as pd
from django.conf import settings
import numpy as np

from conferences.models import Publication

logger = logging.getLogger(__name__)


class LotusSemanticSearchService:
    """
    Service for performing semantic search operations using Lotus library.

    Uses lazy initialization for Lotus to avoid import issues on macOS and
    improve startup time.
    """

    def __init__(self):
        """Initialize service with lazy Lotus and Chroma loading."""
        # Lotus fields
        self._lotus_initialized = False
        self._lotus = None
        self._lm = None
        self._rm = None  # Retrieval Model / embedding model
        self._predicate_cache: dict[str, str] = {}
        self._openai_client = None

        # Chroma fields
        self._chroma_initialized = False
        self._chroma_available = None  # None=unknown, True=working, False=failed
        self._chroma_vector_store = None
        self._chroma_embedding_function = None

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

            self._lotus = lotus

            # Get configuration from Django settings
            config = settings.LOTUS_CONFIG
            model_name = config.get("default_model", "gpt-4o")
            helper_model = config.get("helper_model")
            provider = str(config.get("llm_provider", "openai")).lower()

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

            # Initialize embedding / retrieval model (no cascade)
            embedding_model_name = config.get("embedding_model", "intfloat/e5-base-v2")
            try:
                self._rm = SentenceTransformersRM(model=embedding_model_name)
                logger.info(f"Lotus retrieval model initialized: {embedding_model_name}")
            except Exception as rm_error:
                self._rm = None
                logger.warning(
                    f"Failed to initialize retrieval model '{embedding_model_name}': {rm_error}. "
                    "Embedding-based prefiltering will be disabled."
                )

            # Configure Lotus settings (LM + optional helper + optional RM)
            if helper_model:
                helper_lm = LM(model=helper_model)
                if self._rm is not None:
                    lotus.settings.configure(lm=self._lm, helper_lm=helper_lm, rm=self._rm)
                else:
                    lotus.settings.configure(lm=self._lm, helper_lm=helper_lm)
                logger.info(f"Lotus configured with helper_lm={helper_model}")
            else:
                if self._rm is not None:
                    lotus.settings.configure(lm=self._lm, rm=self._rm)
                else:
                    lotus.settings.configure(lm=self._lm)

            self._lotus_initialized = True

        except ImportError as e:
            logger.error(f"Failed to import Lotus: {e}")
            raise ImportError("lotus-ai library is not installed. Run: pip install lotus-ai")
        except Exception as e:
            logger.error(f"Failed to initialize Lotus: {e}")
            raise RuntimeError(f"Lotus initialization failed: {str(e)}")

    def _initialize_chroma(self) -> bool:
        """
        Initialize Chroma vector store with lazy loading.

        Attempts to use Xinference embeddings, falls back to SentenceTransformers.
        Caches initialization state to avoid repeated attempts.

        Returns:
            bool: True if Chroma is available, False otherwise
        """
        if self._chroma_initialized:
            return self._chroma_available

        self._chroma_initialized = True

        # Check if Chroma is enabled
        config = settings.CHROMA_CONFIG
        if not config.get("enabled", True):
            logger.info("Chroma disabled via CHROMA_ENABLED=false")
            self._chroma_available = False
            return False

        # Check required configuration
        persist_dir = config.get("persist_dir")
        if not persist_dir:
            logger.warning("CHROMA_PERSIST_DIR not configured, Chroma disabled")
            self._chroma_available = False
            return False

        try:
            # Import Chroma dependencies
            from langchain_chroma import Chroma
            from langchain_community.embeddings import XinferenceEmbeddings

            # Initialize embedding function
            if config.get("use_xinference", True) and config.get("embedding_model"):
                # Primary: Xinference embeddings
                try:
                    self._chroma_embedding_function = XinferenceEmbeddings(
                        server_url=config["xinference_url"],
                        model_uid=config["embedding_model"],
                    )
                    logger.info(
                        f"Chroma using Xinference embeddings: "
                        f"model={config['embedding_model']}, url={config['xinference_url']}"
                    )
                except Exception as xe:
                    logger.warning(f"Xinference embedding init failed: {xe}, trying fallback")
                    # Fall back to SentenceTransformers
                    from sentence_transformers import SentenceTransformer
                    model = SentenceTransformer(config["fallback_model"])
                    self._chroma_embedding_function = model.encode
                    logger.info(f"Using fallback embedding model: {config['fallback_model']}")
            else:
                # Fallback: SentenceTransformers
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer(config["fallback_model"])
                self._chroma_embedding_function = model.encode
                logger.info(f"Using SentenceTransformers: {config['fallback_model']}")

            # Initialize Chroma client
            collection_name = config.get("collection_name", "publication")
            self._chroma_vector_store = Chroma(
                collection_name=collection_name,
                embedding_function=self._chroma_embedding_function,
                persist_directory=persist_dir,
            )

            # Verify collection has data
            collection_count = self._chroma_vector_store._collection.count()
            if collection_count == 0:
                logger.warning(
                    f"Chroma collection '{collection_name}' is empty. "
                    f"Import publications using conference import commands to auto-index to Chroma."
                )
                self._chroma_available = False
                return False

            logger.info(
                f"Chroma initialized successfully: collection='{collection_name}', "
                f"vectors={collection_count}, persist_dir='{persist_dir}'"
            )
            self._chroma_available = True
            return True

        except ImportError as e:
            logger.warning(f"Chroma dependencies not installed: {e}")
            self._chroma_available = False
            return False
        except Exception as e:
            logger.error(f"Chroma initialization failed: {e}", exc_info=True)
            self._chroma_available = False
            return False

    def _chroma_prefilter(
        self, query: str, publication_ids: list[str], topk: int
    ) -> list[str] | None:
        """
        Query Chroma vector store to get top candidate publication IDs.

        Optimized flow: Query Chroma first, then load only matching publications.
        This is 150x faster than loading all publications and embedding them.

        Args:
            query: Search query text
            publication_ids: List of publication UUIDs to filter results (from frontend)
            topk: Number of final results wanted

        Returns:
            List of publication UUID strings (top 2*topk candidates), or None on failure
        """
        if not self._initialize_chroma():
            return None

        try:
            config = settings.CHROMA_CONFIG
            k_multiplier = config.get("default_k_multiplier", 2)
            max_candidates = config.get("max_candidates", 100)

            # Calculate how many candidates to fetch (2*topk for LLM reranking)
            candidate_k = min(topk * k_multiplier, max_candidates, len(publication_ids))

            # Build metadata filter to only search within provided publication_ids
            # Chroma filter: {"publication_id": {"$in": ["uuid1", "uuid2", ...]}}
            metadata_filter = {
                "publication_id": {"$in": publication_ids}
            } if publication_ids else None

            # Query Chroma
            logger.info(
                f"Querying Chroma: query='{query[:50]}...', k={candidate_k}, "
                f"filter_size={len(publication_ids) if publication_ids else 'none'}"
            )

            results = self._chroma_vector_store.similarity_search(
                query=query,
                k=candidate_k,
                filter=metadata_filter,
            )

            # Extract publication IDs from metadata
            candidate_pub_ids = [
                doc.metadata.get("publication_id")
                for doc in results
                if doc.metadata.get("publication_id")
            ]

            logger.info(
                f"Chroma returned {len(candidate_pub_ids)} candidates for query: '{query[:50]}...'"
            )

            return candidate_pub_ids if candidate_pub_ids else None

        except Exception as e:
            logger.error(f"Chroma query failed: {e}", exc_info=True)
            return None

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
            logger.info("OpenAI client initialized for ranking instruction generation")

        return self._openai_client

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

    def _encode_with_retrieval_model(self, texts: list[str]) -> list[list[float]]:
        """
        Encode a list of texts using the configured retrieval / embedding model.

        Tries a few common method names to stay compatible with different
        SentenceTransformersRM implementations.
        """
        if self._rm is None:
            raise RuntimeError("Retrieval model is not initialized")

        encoder = self._rm

        if hasattr(encoder, "encode"):
            return encoder.encode(texts)  # type: ignore[no-any-return]
        if hasattr(encoder, "embed"):
            return encoder.embed(texts)  # type: ignore[no-any-return]
        if callable(encoder):
            return encoder(texts)  # type: ignore[no-any-return]

        raise RuntimeError("Retrieval model does not support encoding texts")

    def _embedding_prefilter(
        self, df: pd.DataFrame, query: str, topk: int | None
    ) -> pd.DataFrame:
        """
        Use the embedding model to compute similarity scores and prefilter
        candidates to 2 * topk before LLM-based reranking.

        If the retrieval model or NumPy is unavailable, this falls back to
        returning the original DataFrame.
        """
        if df.empty:
            return df

        if topk is None or topk <= 0:
            # No specific topk requested; skip prefiltering
            return df

        if self._rm is None:
            logger.warning("Retrieval model not initialized; skipping embedding prefilter")
            return df

        try:
            texts = df["semantic_text"].astype(str).tolist()
        except KeyError:
            # Fallback if semantic_text is missing for some reason
            title_series = df.get("title")
            abstract_series = df.get("abstract")
            if title_series is None or abstract_series is None:
                logger.warning(
                    "No suitable text columns found for embedding prefilter; skipping"
                )
                return df
            texts = (
                title_series.astype(str).str.cat(abstract_series.astype(str), sep=" ")
            ).tolist()

        try:
            query_vec = np.asarray(self._encode_with_retrieval_model([query])[0], dtype=float)
            doc_vecs = np.asarray(self._encode_with_retrieval_model(texts), dtype=float)
        except Exception as e:
            logger.error(f"Failed to encode texts with retrieval model: {e}", exc_info=True)
            return df

        if doc_vecs.size == 0 or query_vec.size == 0:
            return df

        # Compute cosine similarity
        try:
            query_norm = np.linalg.norm(query_vec) + 1e-8
            doc_norms = np.linalg.norm(doc_vecs, axis=1) + 1e-8
            similarities = (doc_vecs @ query_vec) / (doc_norms * query_norm)
        except Exception as e:
            logger.error(f"Failed to compute similarity scores: {e}", exc_info=True)
            return df

        # Select top 2 * topk candidates
        candidate_k = max(1, min(len(df), 2 * topk))
        top_indices = np.argsort(-similarities)[:candidate_k]

        logger.info(
            f"Embedding prefilter selected {candidate_k} candidates "
            f"out of {len(df)} rows for query='{query}'"
        )

        return df.iloc[top_indices].reset_index(drop=True)

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

        return filtered_df.sem_topk(topk_instruction, K=actual_topk, method="quick")

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

    def semantic_search(
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
        3. Applies embedding-based prefiltering and LLM reranking
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
                - total_results: int (number of results after search)
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

            # OPTIMIZATION: Try Chroma first (query-first flow)
            chroma_candidate_ids = None
            original_publication_count = len(publication_ids)

            if settings.CHROMA_CONFIG.get("enabled", True):
                if progress_callback:
                    logger.info("Calling progress_callback for filtering phase (Chroma)")
                    progress_callback("filtering", len(publication_ids))

                chroma_candidate_ids = self._chroma_prefilter(query, publication_ids, topk)

                if chroma_candidate_ids:
                    logger.info(
                        f"Using Chroma candidates: {len(chroma_candidate_ids)} out of "
                        f"{len(publication_ids)} total publications"
                    )
                    # Replace publication_ids with Chroma-filtered subset
                    publication_ids = chroma_candidate_ids
                else:
                    logger.warning("Chroma filtering failed, loading all publications for fallback")

            # Load publications from database (either Chroma subset or all)
            publications = Publication.objects.select_related("instance__venue").filter(
                id__in=publication_ids
            )
            publications_list = list(publications)

            if not publications_list:
                logger.warning(f"No publications found for {len(publication_ids)} provided IDs")
                return {
                    "success": True,
                    "query": query,
                    "total_input": original_publication_count,
                    "total_results": 0,
                    "results": [],
                    "metadata": {
                        "llm_model": settings.LOTUS_CONFIG.get("default_model"),
                        "processing_time_ms": int((time.time() - start_time) * 1000),
                        "search_method": "chroma" if chroma_candidate_ids else "fallback",
                    },
                }

            logger.info(f"Loaded {len(publications_list)} publications for semantic search")

            # Convert to DataFrame
            df = self._publications_to_dataframe(publications_list)

            if df.empty:
                return {
                    "success": True,
                    "query": query,
                    "total_input": original_publication_count,
                    "total_results": 0,
                    "results": [],
                    "metadata": {
                        "llm_model": settings.LOTUS_CONFIG.get("default_model"),
                        "processing_time_ms": int((time.time() - start_time) * 1000),
                        "search_method": "chroma" if chroma_candidate_ids else "fallback",
                    },
                }

            # If Chroma was NOT used, apply embedding-based prefilter (fallback)
            if not chroma_candidate_ids:
                if progress_callback:
                    logger.info(f"Calling progress_callback for filtering phase (fallback)")
                    progress_callback("filtering", len(df))
                else:
                    logger.warning("No progress_callback provided, skipping filtering notification")

                filtered_df = self._embedding_prefilter(df, query, topk)
            else:
                # Chroma already filtered, use all loaded publications
                filtered_df = df

            # Notify reranking phase starting
            if progress_callback:
                logger.info(f"Calling progress_callback for reranking phase with {len(filtered_df)} publications")
                progress_callback("reranking", len(filtered_df))
            else:
                logger.warning("No progress_callback provided, skipping reranking notification")

            # Apply semantic ranking (LLM-based)
            if not filtered_df.empty:
                ranked_df = self._apply_semantic_topk(filtered_df, query, topk)
            else:
                ranked_df = filtered_df

            # Convert results to list of dictionaries
            results = self._dataframe_to_results(ranked_df)

            processing_time = int((time.time() - start_time) * 1000)
            search_method = "chroma" if chroma_candidate_ids else "fallback_embedding"

            logger.info(
                f"Semantic search completed in {processing_time}ms using {search_method}, "
                f"found {len(results)} results"
            )

            return {
                "success": True,
                "query": query,
                "total_input": original_publication_count,
                "total_results": len(results),
                "results": results,
                "metadata": {
                    "llm_model": settings.LOTUS_CONFIG.get("default_model"),
                    "processing_time_ms": processing_time,
                    "search_method": search_method,
                    "chroma_enabled": chroma_candidate_ids is not None,
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
        elif "chroma" in error_message.lower():
            error_code = "CHROMA_ERROR"
            detail = f"Chroma vector store error: {error_message}. Falling back to embedding-based search."
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
