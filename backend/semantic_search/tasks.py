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
        # Calculate total batches upfront
        total_batches = (total_publications + batch_size - 1) // batch_size

        # Publish initial status
        _publish_progress(
            job_id,
            {
                "type": "started",
                "total": total_publications,
                "total_batches": total_batches,
                "processed": 0,
                "progress": 0.0,
                "query": query,
            },
        )

        # Process in batches
        for i in range(0, total_publications, batch_size):
            batch_ids = publication_ids[i : i + batch_size]
            batch_num = (i // batch_size) + 1

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

            batch_result_ids = []
            try:
                # Step 1: semantic filter on this batch (no top-k yet)
                batch_filtered_df = lotus_semantic_search_service.filter_publications(
                    publication_ids=batch_ids,
                    query=query,
                )

                if not batch_filtered_df.empty:
                    all_filtered_frames.append(batch_filtered_df)

                    # Extract only publication IDs for streaming
                    # Frontend will fetch full details using bulk endpoint
                    batch_result_ids = [
                        {
                            "id": str(row["id"]),
                            "relevance_score": float(row.get("relevance_score", 0))
                        }
                        for _, row in batch_filtered_df.iterrows()
                    ]
            except Exception as batch_error:
                logger.error(
                    f"Job {job_id}: Batch {batch_num} failed with error: {str(batch_error)}",
                    exc_info=True
                )
                # Continue with next batch instead of failing entire job

            # Always publish progress for every batch (even if failed)
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
                    "batch_result_ids": batch_result_ids,
                    "batch_count": len(batch_result_ids),
                },
            )

            logger.info(
                f"Job {job_id}: Batch {batch_num}/{total_batches} completed with {len(batch_result_ids)} results"
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
            # Extract only IDs from final ranked results
            final_result_ids = [
                {
                    "id": str(row["id"]),
                    "relevance_score": float(row.get("relevance_score", 0))
                }
                for _, row in ranked_df.iterrows()
            ]
        else:
            final_result_ids = []

        logger.info(
            f"Job {job_id}: Completed with {len(final_result_ids)} final results"
        )

        # Publish completion
        completion_data = {
            "type": "complete",
            "total_results": len(final_result_ids),
            "final_result_ids": final_result_ids,  # Changed from final_results
            "query": query,
        }
        _publish_progress(job_id, completion_data)

        # Store final results in cache for 1 hour
        cache.set(f"semantic_search_results:{job_id}", final_result_ids, timeout=3600)

        return {
            "success": True,
            "job_id": job_id,
            "total_results": len(final_result_ids),
            "result_ids": final_result_ids,  # Changed from results
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
