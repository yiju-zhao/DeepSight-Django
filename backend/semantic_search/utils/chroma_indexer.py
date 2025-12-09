"""
Utility functions for indexing publications to Chroma vector store.

This module provides functions to index Publication objects into Chroma
during import operations.
"""

import logging
import concurrent.futures
from typing import Any

from django.conf import settings

from conferences.models import Publication

logger = logging.getLogger(__name__)


def index_publication_to_chroma(
    publication: Publication,
    chroma_vector_store: Any = None,
    batch_mode: bool = False
) -> bool:
    """
    Index a single publication to Chroma vector store.

    Args:
        publication: Publication instance to index
        chroma_vector_store: Optional pre-initialized Chroma instance (for batch operations)
        batch_mode: If True, returns Document instead of indexing immediately

    Returns:
        bool: True if successful, False otherwise
    """
    # Skip if Chroma is disabled
    config = settings.CHROMA_CONFIG
    if not config.get("enabled", True) or not config.get("persist_dir"):
        return False

    try:
        from langchain_core.documents import Document

        # Prepare content (title + abstract)
        content = f"{publication.title or ''} {publication.abstract or ''}".strip()
        if not content:
            logger.warning(f"Skipping publication {publication.id}: no content")
            return False

        # Prepare metadata
        metadata = {
            "publication_id": str(publication.id),
            "instance_id": publication.instance.instance_id if publication.instance else None,
        }

        document = Document(page_content=content, metadata=metadata)

        # If batch mode, return the document for later batch processing
        if batch_mode:
            return document  # type: ignore

        # Otherwise, index immediately
        if chroma_vector_store is None:
            # Initialize Chroma on-demand
            chroma_vector_store = _get_chroma_vector_store()
            if chroma_vector_store is None:
                return False

        chroma_vector_store.add_documents([document])
        logger.debug(f"Indexed publication {publication.id} to Chroma")
        return True

    except ImportError as e:
        logger.warning(f"Chroma dependencies not installed: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to index publication {publication.id} to Chroma: {e}", exc_info=True)
        return False


def batch_index_publications_to_chroma(
    publications: list[Publication],
    batch_size: int = 1000,
    max_workers: int = 4
) -> dict[str, int]:
    """
    Batch index multiple publications to Chroma vector store using parallel processing.

    Args:
        publications: List of Publication instances to index
        batch_size: Number of publications to process in each batch
        max_workers: Number of parallel threads to use for indexing

    Returns:
        dict with 'indexed' and 'failed' counts
    """
    config = settings.CHROMA_CONFIG
    if not config.get("enabled", True) or not config.get("persist_dir"):
        logger.info("Chroma disabled, skipping vector indexing")
        return {"indexed": 0, "failed": 0}

    try:
        from langchain_core.documents import Document

        # Initialize Chroma once to check connectivity/configuration
        # Note: Each thread should ideally get its own client or use the thread-safe one,
        # but for LangChain/Chroma, sharing the instance for HTTP calls is usually fine.
        # For local SQLite, we might hit write locks, but ThreadPool helps with the 
        # embedding generation latency which is usually the bottleneck.
        vector_store = _get_chroma_vector_store()
        if vector_store is None:
            logger.warning("Failed to initialize Chroma, skipping vector indexing")
            return {"indexed": 0, "failed": 0}

        # Step 1: Pre-process all publications into Documents in the main thread.
        # This prevents Django DB connection issues inside threads.
        all_documents = []
        for pub in publications:
            content = f"{pub.title or ''} {pub.abstract or ''}".strip()
            if not content:
                continue
            
            metadata = {
                "publication_id": str(pub.id),
                "instance_id": pub.instance.instance_id if pub.instance else None,
            }
            all_documents.append(Document(page_content=content, metadata=metadata))

        total_docs = len(all_documents)
        if total_docs == 0:
            return {"indexed": 0, "failed": 0}

        logger.info(f"Prepared {total_docs} documents for indexing. Starting parallel execution with {max_workers} workers.")

        indexed = 0
        failed = 0

        # Helper function for the thread pool
        def _process_batch(batch_docs):
            try:
                # Re-fetching vector store inside thread can sometimes be safer depending on the client,
                # but passing the main one works for most HTTP-based embedding/vector services.
                # If using local SQLite Chroma, writes are serialized anyway, but embeddings happen in parallel.
                vector_store.add_documents(batch_docs)
                return len(batch_docs)
            except Exception as e:
                logger.error(f"Batch indexing failed: {e}")
                raise e

        # Step 2: Submit batches to ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i in range(0, total_docs, batch_size):
                batch = all_documents[i : i + batch_size]
                futures.append(executor.submit(_process_batch, batch))

            # Step 3: Collect results
            for future in concurrent.futures.as_completed(futures):
                try:
                    count = future.result()
                    indexed += count
                    # Optional: Log progress
                    if indexed % (batch_size * max_workers) == 0:
                         logger.info(f"Progress: {indexed}/{total_docs} indexed...")
                except Exception:
                    # The exception is already logged in _process_batch
                    # We assume the whole batch failed
                    failed += batch_size  # Estimate based on batch size, though exact mapping is lost

        logger.info(f"Chroma indexing complete: {indexed} indexed, {failed} failed")
        return {"indexed": indexed, "failed": failed}

    except ImportError as e:
        logger.warning(f"Chroma dependencies not installed: {e}")
        return {"indexed": 0, "failed": 0}
    except Exception as e:
        logger.error(f"Batch indexing failed: {e}", exc_info=True)
        return {"indexed": 0, "failed": 0}


def delete_publications_from_chroma(
    instance_id: str = None,
    publication_ids: list[str] = None
) -> dict[str, int]:
    """
    Delete publications from Chroma vector store.

    Args:
        instance_id: Instance ID to delete all publications for that instance
        publication_ids: List of publication IDs to delete

    Returns:
        dict with 'deleted' count and 'success' boolean
    """
    config = settings.CHROMA_CONFIG
    if not config.get("enabled", True) or not config.get("persist_dir"):
        logger.info("Chroma disabled, skipping vector deletion")
        return {"deleted": 0, "success": True}

    if not instance_id and not publication_ids:
        logger.warning("No instance_id or publication_ids provided for deletion")
        return {"deleted": 0, "success": False}

    try:
        # Initialize Chroma
        vector_store = _get_chroma_vector_store()
        if vector_store is None:
            logger.warning("Failed to initialize Chroma, skipping vector deletion")
            return {"deleted": 0, "success": False}

        # Delete by instance_id filter
        if instance_id:
            try:
                # Chroma uses 'where' filter for metadata-based deletion
                vector_store.delete(where={"instance_id": instance_id})
                logger.info(f"Deleted all publications for instance {instance_id} from Chroma")
                return {"deleted": -1, "success": True}  # -1 indicates unknown count
            except Exception as e:
                logger.error(f"Failed to delete by instance_id {instance_id}: {e}")
                return {"deleted": 0, "success": False}

        # Delete by publication IDs
        if publication_ids:
            try:
                deleted = 0
                for pub_id in publication_ids:
                    try:
                        vector_store.delete(where={"publication_id": str(pub_id)})
                        deleted += 1
                    except Exception as e:
                        logger.error(f"Failed to delete publication {pub_id}: {e}")

                logger.info(f"Deleted {deleted} publications from Chroma")
                return {"deleted": deleted, "success": True}
            except Exception as e:
                logger.error(f"Failed to delete publications: {e}")
                return {"deleted": 0, "success": False}

    except ImportError as e:
        logger.warning(f"Chroma dependencies not installed: {e}")
        return {"deleted": 0, "success": False}
    except Exception as e:
        logger.error(f"Deletion failed: {e}", exc_info=True)
        return {"deleted": 0, "success": False}


def _get_chroma_vector_store():
    """
    Initialize and return Chroma vector store.

    Returns:
        Chroma instance or None if initialization fails
    """
    try:
        from langchain_chroma import Chroma
        from langchain_community.embeddings import XinferenceEmbeddings
        from sentence_transformers import SentenceTransformer

        config = settings.CHROMA_CONFIG

        # Initialize embedding function
        if config.get("use_xinference") and config.get("embedding_model"):
            try:
                embedding_function = XinferenceEmbeddings(
                    server_url=config["xinference_url"],
                    model_uid=config["embedding_model"],
                )
                logger.info(f"Using Xinference embeddings: {config['embedding_model']}")
            except Exception as xe:
                logger.warning(f"Xinference init failed: {xe}, using fallback")
                model = SentenceTransformer(config["fallback_model"])
                embedding_function = model.encode
        else:
            model = SentenceTransformer(config["fallback_model"])
            embedding_function = model.encode

        # Initialize Chroma
        collection_name = config.get("collection_name", "publication")
        vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=embedding_function,
            persist_directory=config["persist_dir"],
        )

        return vector_store

    except ImportError as e:
        logger.warning(f"Chroma dependencies not installed: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Chroma: {e}", exc_info=True)
        return None
