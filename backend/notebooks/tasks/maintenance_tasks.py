"""
Maintenance tasks for notebooks app.

This module contains tasks for cleanup, health checks, and testing.
"""

import logging
from datetime import datetime, timedelta

from celery import shared_task
from django.utils import timezone

from ..models import BatchJob, KnowledgeBaseItem

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_batch_jobs():
    """
    Cleanup old completed batch jobs (older than 7 days).

    This task removes batch jobs older than 7 days to prevent database bloat.
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=7)
        old_jobs = BatchJob.objects.filter(
            status__in=["completed", "failed", "partially_completed"],
            updated_at__lt=cutoff_date,
        )

        count = old_jobs.count()
        old_jobs.delete()

        logger.info(f"Cleaned up {count} old batch jobs")
        return {"cleaned_jobs": count}

    except Exception as e:
        logger.error(f"Error cleaning up old batch jobs: {e}")
        raise


@shared_task
def test_caption_generation_task(kb_item_id: str):
    """Test task to verify caption generation works."""
    logger.info(f"Test caption generation task called with kb_item_id: {kb_item_id}")
    return {"test": "successful", "kb_item_id": kb_item_id}


@shared_task
def health_check_task():
    """
    Simple health check task for monitoring Celery workers.

    Returns:
        dict: Health status with timestamp
    """
    logger.info("Health check task executed successfully")
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "worker": "celery",
    }
