"""
Celery tasks for semantic search operations.

Provides async processing for semantic search across large datasets.
"""

import json
import logging
from typing import Any

import redis
from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from .services import lotus_semantic_search_service

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="semantic_search.stream_search")
def semantic_search_streaming_task(
    self, publication_ids: list[str], query: str, topk: int, job_id: str
) -> dict[str, Any]:
    """
    Perform streaming semantic search on all publications at once.

    Processes all publications in a single operation, publishing results
    to Redis for SSE streaming to the frontend.

    Args:
        self: Celery task instance
        publication_ids: List of publication UUIDs to search
        query: Natural language search query
        topk: Number of top results to return
        job_id: Unique job identifier for this search

    Returns:
        Final search results dictionary
    """
    total_publications = len(publication_ids)

    logger.info(
        f"Starting semantic search job {job_id}: "
        f"{total_publications} publications, query='{query[:50]}...'"
    )

    def publish_progress(phase: str, count: int):
        """Publish progress for different semantic search phases."""
        if phase == "filtering":
            _publish_progress(
                job_id,
                {
                    "type": "filtering",
                    "total": count,
                    "message": f"Filtering {count} publications...",
                },
            )
        elif phase == "reranking":
            _publish_progress(
                job_id,
                {
                    "type": "reranking",
                    "total": count,
                    "message": f"Reranking {count} publications...",
                },
            )

    try:
        # Publish initial status
        _publish_progress(
            job_id,
            {
                "type": "started",
                "total": total_publications,
                "query": query,
            },
        )

        # Update task progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": total_publications,
            },
        )

        # Process all publications at once with semantic filtering and ranking
        logger.info(f"Job {job_id}: Processing all {total_publications} publications")

        result = lotus_semantic_search_service.semantic_filter(
            publication_ids=publication_ids,
            query=query,
            topk=topk,
            progress_callback=publish_progress,
        )

        if result["success"]:
            # Extract only IDs and relevance scores for streaming
            final_result_ids = [
                {
                    "id": str(pub["id"]),
                    "relevance_score": float(pub.get("relevance_score", 0))
                }
                for pub in result["results"]
            ]
        else:
            final_result_ids = []
            logger.error(f"Job {job_id}: Semantic search failed: {result.get('detail', 'Unknown error')}")

        logger.info(
            f"Job {job_id}: Completed with {len(final_result_ids)} final results"
        )

        # Publish completion
        completion_data = {
            "type": "complete",
            "total_results": len(final_result_ids),
            "final_result_ids": final_result_ids,
            "query": query,
        }
        _publish_progress(job_id, completion_data)

        # Store final results in cache for 1 hour
        cache.set(f"semantic_search_results:{job_id}", final_result_ids, timeout=3600)

        return {
            "success": True,
            "job_id": job_id,
            "total_results": len(final_result_ids),
            "result_ids": final_result_ids,
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
    redis_client: redis.Redis | None = None

    try:
        redis_client = redis.Redis.from_url(
            settings.CELERY_BROKER_URL, decode_responses=True
        )

        channel = f"semantic_search:{job_id}"
        message = json.dumps(data)
        redis_client.publish(channel, message)

        # Also store latest progress in cache for recovery
        cache_key = f"semantic_search_progress:{job_id}"
        cache.set(cache_key, json.dumps(data), timeout=3600)

        logger.debug(f"Published progress for job {job_id}: {data.get('type')}")

    except Exception as e:
        logger.error(f"Failed to publish progress for job {job_id}: {e}")

    finally:
        if redis_client is not None:
            try:
                redis_client.close()
            except Exception:
                pass
