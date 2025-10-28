"""
Shared helper functions for Celery tasks.

This module contains common functionality used across different task modules.
"""

import logging
from typing import Any

from asgiref.sync import async_to_sync
from core.utils.sse import publish_notebook_event
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from ..exceptions import ValidationError
from ..constants import ParsingStatus, ContentType, SseStatus
from ..models import BatchJob, BatchJobItem, KnowledgeBaseItem, Notebook

User = get_user_model()
logger = logging.getLogger(__name__)


def _validate_task_inputs(
    url: str = None,
    notebook_id: str = None,
    user_id: int = None,
    file_data: bytes = None,
    filename: str = None,
) -> None:
    """Validate common task inputs."""
    if url is not None and not url:
        raise ValidationError("URL cannot be empty")
    if notebook_id is not None and not notebook_id:
        raise ValidationError("Notebook ID is required")
    if user_id is not None and not user_id:
        raise ValidationError("User ID is required")
    if file_data is not None and not file_data:
        raise ValidationError("File data cannot be empty")
    if filename is not None and not filename:
        raise ValidationError("Filename cannot be empty")


def _get_notebook_and_user(notebook_id: str, user_id: int) -> tuple[Notebook, Any]:
    """Get notebook and user objects with validation."""
    try:
        user = User.objects.get(id=user_id)
        notebook = get_object_or_404(Notebook, id=notebook_id, user=user)
        return notebook, user
    except User.DoesNotExist:
        raise ValidationError(f"User {user_id} not found")


def _get_or_create_knowledge_item(
    kb_item_id: str = None, notebook: Notebook = None, title: str = None
) -> KnowledgeBaseItem:
    """Get existing knowledge item or create new one if needed."""
    if kb_item_id:
        try:
            return KnowledgeBaseItem.objects.get(id=kb_item_id, notebook=notebook)
        except KnowledgeBaseItem.DoesNotExist:
            logger.error(
                f"KnowledgeBaseItem {kb_item_id} not found in notebook {notebook.id}"
            )
            raise ValidationError(f"Knowledge item {kb_item_id} not found")

    # Create new knowledge item if no ID provided
    if not title:
        raise ValidationError("Title is required for new knowledge items")

    return KnowledgeBaseItem(
        notebook=notebook,
        title=title,
        content_type=ContentType.DOCUMENT,
        parsing_status=ParsingStatus.QUEUEING,
        notes=f"Processing {title}",
        tags=[],
        metadata={},
    )


def _update_batch_item_status(
    batch_job_id: str | None,
    upload_id: str,
    status: str,
    error: str | None = None,
) -> None:
    """Update the status of a batch job item."""
    if not batch_job_id:
        return

    try:
        batch_item = BatchJobItem.objects.get(
            batch_job_id=batch_job_id, upload_id=upload_id
        )
        batch_item.status = status
        if error:
            batch_item.error_message = error
        batch_item.save()
        logger.info(
            f"Updated batch item {upload_id} in job {batch_job_id} to status {status}"
        )
    except BatchJobItem.DoesNotExist:
        logger.warning(
            f"Batch job item not found: batch_job_id={batch_job_id}, upload_id={upload_id}"
        )


def _check_batch_completion(batch_job_id: str | None) -> None:
    """Check if all items in a batch job are completed and update job status."""
    if not batch_job_id:
        return

    try:
        batch_job = BatchJob.objects.get(id=batch_job_id)
        items = batch_job.items.all()

        if not items.exists():
            logger.warning(f"Batch job {batch_job_id} has no items")
            return

        total = items.count()
        completed = items.filter(status="completed").count()
        failed = items.filter(status="failed").count()

        # If all items are either completed or failed
        if completed + failed == total:
            if failed > 0:
                batch_job.status = "completed_with_errors"
            else:
                batch_job.status = "completed"
            batch_job.save()
            logger.info(
                f"Batch job {batch_job_id} completed: {completed}/{total} successful, {failed}/{total} failed"
            )
    except BatchJob.DoesNotExist:
        logger.warning(f"Batch job {batch_job_id} not found during completion check")


def _handle_task_completion(
    kb_item: KnowledgeBaseItem,
    result: dict,
    upload_id: str | None = None,
    batch_job_id: str | None = None,
) -> None:
    """Handle successful task completion with SSE events and batch job updates."""
    try:
        # Publish SSE success event
        async_to_sync(publish_notebook_event)(
            notebook_id=str(kb_item.notebook.id),
            entity="source",
            entity_id=str(kb_item.id),
            status=SseStatus.SUCCESS,
            payload={
                "title": kb_item.title,
                "content_type": kb_item.content_type,
                "upload_id": upload_id,
            },
        )

        # Update batch job item if applicable
        if upload_id and batch_job_id:
            _update_batch_item_status(
                batch_job_id=batch_job_id,
                upload_id=upload_id,
                status="completed",
            )
            _check_batch_completion(batch_job_id)

        logger.info(
            f"Task completion handled successfully for KB item {kb_item.id}"
        )
    except Exception as e:
        logger.exception(f"Error in task completion handler: {e}")


def _handle_task_error(
    error: Exception,
    notebook_id: str,
    kb_item_id: str | None = None,
    upload_id: str | None = None,
    batch_job_id: str | None = None,
    context: str = "task",
) -> None:
    """Handle task errors with SSE events and batch job updates."""
    error_message = str(error)
    logger.exception(f"Error in {context}: {error_message}")

    try:
        # Publish SSE failure event
        async_to_sync(publish_notebook_event)(
            notebook_id=notebook_id,
            entity="source",
            entity_id=kb_item_id or "unknown",
            status=SseStatus.FAILURE,
            payload={
                "error": error_message,
                "context": context,
                "upload_id": upload_id,
            },
        )

        # Update batch job item if applicable
        if upload_id and batch_job_id:
            _update_batch_item_status(
                batch_job_id=batch_job_id,
                upload_id=upload_id,
                status="failed",
                error=error_message,
            )
            _check_batch_completion(batch_job_id)

    except Exception as e:
        logger.exception(f"Error in task error handler: {e}")
