"""
Celery tasks for semantic search operations.

Provides async batch processing for semantic search across large datasets.
"""

import json
import logging
import time
from typing import Any

from celery import shared_task
from django.core.cache import cache

from .services import lotus_semantic_search_service

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="semantic_search.stream_search")
def semantic_search_streaming_task(
    self, publication_ids: list[str], query: str, topk: int, job_id: str
) -> dict[str, Any]:
    """
    Perform streaming semantic search on publications in batches.

    Processes publications in batches of 100, publishing intermediate results
    to Redis for SSE streaming to the frontend.

    Args:
        self: Celery task instance
        publication_ids: List of publication UUIDs to search
        query: Natural language search query
        topk: Number of top results to return per batch
        job_id: Unique job identifier for this search

    Returns:
        Final search results dictionary
    """
    batch_size = 100
    all_results = []
    all_filtered_frames = []
    total_publications = len(publication_ids)

    logger.info(
        f"Starting streaming semantic search job {job_id}: "
        f"{total_publications} publications, query='{query[:50]}...'"
    )

    try:
        # Publish initial status
        _publish_progress(
            job_id,
            {
                "type": "started",
                "total": total_publications,
                "processed": 0,
                "progress": 0.0,
                "query": query,
            },
        )

        # Process in batches
        for i in range(0, total_publications, batch_size):
            batch_ids = publication_ids[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_publications + batch_size - 1) // batch_size

            logger.info(
                f"Job {job_id}: Processing batch {batch_num}/{total_batches} "
                f"({len(batch_ids)} publications)"
            )

            # Update task progress
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i + len(batch_ids),
                    "total": total_publications,
                    "batch": batch_num,
                    "total_batches": total_batches,
                },
            )

            # Step 1: semantic filter on this batch (no top-k yet)
            batch_filtered_df = lotus_semantic_search_service.filter_publications(
                publication_ids=batch_ids,
                query=query,
            )

            if not batch_filtered_df.empty:
                all_filtered_frames.append(batch_filtered_df)

                # For streaming, convert current batch to incremental results.
                # These are intermediate and may not reflect the final global
                # top-k ordering.
                batch_results = lotus_semantic_search_service._dataframe_to_results(  # type: ignore[attr-defined]
                    batch_filtered_df
                )
                all_results.extend(batch_results)

                progress = (i + len(batch_ids)) / total_publications
                _publish_progress(
                    job_id,
                    {
                        "type": "batch",
                        "batch_num": batch_num,
                        "total_batches": total_batches,
                        "processed": i + len(batch_ids),
                        "total": total_publications,
                        "progress": progress,
                        "batch_results": batch_results,
                        "batch_count": len(batch_results),
                    },
                )

                logger.info(
                    f"Job {job_id}: Batch {batch_num} completed with {len(batch_results)} results"
                )
            else:
                logger.info(
                    f"Job {job_id}: Batch {batch_num} completed with no matching results"
                )

        # Step 2: final global top-k ranking across all filtered results
        if all_filtered_frames:
            import pandas as pd

            combined_df = pd.concat(all_filtered_frames, ignore_index=True)
            ranked_df = lotus_semantic_search_service._apply_semantic_topk(  # type: ignore[attr-defined]
                combined_df,
                query=query,
                topk=topk,
            )
            final_results = lotus_semantic_search_service._dataframe_to_results(  # type: ignore[attr-defined]
                ranked_df
            )
        else:
            final_results = []

        logger.info(
            f"Job {job_id}: Completed with {len(final_results)} final results "
            f"(from {len(all_results)} total)"
        )

        # Publish completion
        completion_data = {
            "type": "complete",
            "total_results": len(final_results),
            "final_results": final_results,
            "query": query,
        }
        _publish_progress(job_id, completion_data)

        # Store final results in cache for 1 hour
        cache.set(f"semantic_search_results:{job_id}", final_results, timeout=3600)

        return {
            "success": True,
            "job_id": job_id,
            "total_results": len(final_results),
            "results": final_results,
        }

    except Exception as e:
        logger.error(f"Job {job_id}: Failed with error: {str(e)}", exc_info=True)

        # Publish error
        _publish_progress(
            job_id,
            {
                "type": "error",
                "error": "SEARCH_FAILED",
                "detail": str(e),
            },
        )

        return {
            "success": False,
            "job_id": job_id,
            "error": str(e),
        }


def _publish_progress(job_id: str, data: dict) -> None:
    """
    Publish progress update to Redis for SSE streaming.

    Args:
        job_id: Job identifier
        data: Progress data dictionary
    """
    try:
        from .utils.redis_pubsub import publish_to_channel

        channel = f"semantic_search:{job_id}"
        publish_to_channel(channel, data)

        # Also store latest progress in cache for recovery
        cache_key = f"semantic_search_progress:{job_id}"
        cache.set(cache_key, json.dumps(data), timeout=3600)

        logger.debug(f"Published progress for job {job_id}: {data.get('type')}")

    except Exception as e:
        logger.error(f"Failed to publish progress for job {job_id}: {e}")
