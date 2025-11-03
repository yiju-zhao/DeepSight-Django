"""
URL and file processing tasks for notebooks app.

This module contains tasks for parsing URLs, processing documents, uploading files,
and generating image captions.
"""

import logging
import os
from typing import Any
from uuid import uuid4

from asgiref.sync import async_to_sync
from celery import shared_task
from core.utils.sse import publish_notebook_event
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404

from ..constants import CaptioningStatus, ContentType, ParsingStatus
from ..exceptions import FileProcessingError, URLProcessingError, ValidationError
from ..ingestion import IngestionOrchestrator
from ..models import KnowledgeBaseImage, KnowledgeBaseItem
from ._helpers import (
    _check_batch_completion,
    _get_notebook_and_user,
    _update_batch_item_status,
    _validate_task_inputs,
)
from .ragflow_tasks import upload_to_ragflow_task

logger = logging.getLogger(__name__)


# Initialize ingestion orchestrator
def _get_ingestion_orchestrator() -> IngestionOrchestrator:
    """Get configured ingestion orchestrator instance."""
    mineru_base_url = os.getenv("MINERU_BASE_URL", "http://localhost:8008")

    # Transcription provider configuration
    transcription_provider = os.getenv("TRANSCRIPTION_PROVIDER", "whisperx")

    # WhisperX configuration
    whisperx_model_name = os.getenv("WHISPERX_MODEL_NAME", "large-v2")
    whisperx_device = os.getenv("WHISPERX_DEVICE", "auto")
    whisperx_compute_type = os.getenv("WHISPERX_COMPUTE_TYPE")
    whisperx_batch_size = int(os.getenv("WHISPERX_BATCH_SIZE", "16"))
    whisperx_language = os.getenv("WHISPERX_LANGUAGE")
    whisperx_use_vad = os.getenv("WHISPERX_VAD", "0") == "1"
    whisperx_cache_dir = os.getenv("WHISPERX_CACHE_DIR")

    # Xinference configuration (fallback)
    xinference_url = os.getenv("XINFERENCE_URL", "http://localhost:9997")
    xinference_model_uid = os.getenv(
        "XINFERENCE_WHISPER_MODEL_UID", "Bella-whisper-large-v3-zh"
    )

    return IngestionOrchestrator(
        mineru_base_url=mineru_base_url,
        transcription_provider=transcription_provider,
        whisperx_model_name=whisperx_model_name,
        whisperx_device=whisperx_device,
        whisperx_compute_type=whisperx_compute_type,
        whisperx_batch_size=whisperx_batch_size,
        whisperx_language=whisperx_language,
        whisperx_use_vad=whisperx_use_vad,
        whisperx_cache_dir=whisperx_cache_dir,
        xinference_url=xinference_url,
        xinference_model_uid=xinference_model_uid,
        logger=logger,
    )


# ============================================================================
# LOCAL HELPER FUNCTIONS
# These are specific to processing tasks and handle completion/error logic
# ============================================================================


def _handle_task_completion(
    kb_item: KnowledgeBaseItem,
    batch_item_id: str = None,
    batch_job_id: str = None,
    upload_file_id: str = None,
    upload_url_id: str = None,
) -> dict[str, Any]:
    """Handle common task completion logic.

    File parsing is now complete - mark as 'done' immediately so frontend can use it.
    Caption generation and other post-processing run independently.
    """
    # Mark parsing as done immediately - file is ready for use
    kb_item.parsing_status = ParsingStatus.DONE
    kb_item.save(update_fields=["parsing_status", "updated_at"])

    logger.info(f"KB item {kb_item.id} marked as 'done' - ready for frontend use")

    # Note: Final display is gated by RagFlow completion; avoid publishing
    # a premature SUCCESS here to reduce noise and duplicate events.

    # Chain RagFlow upload task to ensure content is fully saved
    try:
        upload_to_ragflow_task.delay(str(kb_item.id))
        logger.info(f"Chained RagFlow upload task for KB item {kb_item.id}")
    except Exception as e:
        logger.error(
            f"Failed to chain RagFlow upload task for KB item {kb_item.id}: {e}"
        )
        # Don't fail the main task if chaining fails

    # Schedule caption generation after all processing is complete
    try:
        # Count images in database
        image_count = KnowledgeBaseImage.objects.filter(
            knowledge_base_item=kb_item
        ).count()

        if image_count > 0:
            kb_item.captioning_status = CaptioningStatus.PENDING
            kb_item.save(update_fields=["captioning_status", "updated_at"])

            generate_image_captions_task.delay(str(kb_item.id))
            logger.info(
                f"Scheduled caption generation for KB item {kb_item.id} with {image_count} images"
            )
        else:
            kb_item.captioning_status = CaptioningStatus.NOT_REQUIRED
            kb_item.save(update_fields=["captioning_status", "updated_at"])
            logger.info(f"No images for KB item {kb_item.id} - captioning not required")
    except Exception as caption_error:
        logger.warning(
            f"Failed to schedule caption generation for KB item {kb_item.id}: {caption_error}"
        )

    # Update batch status
    _update_batch_item_status(
        batch_job_id, upload_file_id or upload_url_id, "completed"
    )
    _check_batch_completion(batch_job_id)

    return {"file_id": str(kb_item.id), "status": "completed"}


def _handle_task_error(
    kb_item: KnowledgeBaseItem,
    error: Exception,
    batch_item_id: str = None,
    batch_job_id: str = None,
    upload_file_id: str = None,
    upload_url_id: str = None,
) -> None:
    """Handle common task error logic."""
    # Update KB item status
    if kb_item:
        kb_item.parsing_status = ParsingStatus.FAILED
        kb_item.metadata = kb_item.metadata or {}
        kb_item.metadata["error_message"] = str(error)
        kb_item.save(update_fields=["parsing_status", "metadata"])

        # Publish FAILURE event via SSE
        if kb_item.notebook:
            publish_notebook_event(
                notebook_id=str(kb_item.notebook.id),
                entity="source",
                entity_id=str(kb_item.id),
                status="FAILURE",
                payload={
                    "error": str(error),
                    "upload_file_id": upload_file_id,
                    "upload_url_id": upload_url_id,
                    "title": kb_item.title,
                },
            )

    # Update batch item status
    _update_batch_item_status(
        batch_job_id,
        upload_file_id or upload_url_id,
        "failed",
        error=str(error),
    )
    _check_batch_completion(batch_job_id)


# ============================================================================
# PARSE TASKS - Simple URL parsing that creates/updates KB items
# ============================================================================


@shared_task(bind=True)
def parse_url_task(
    self,
    url: str,
    upload_url_id: str,
    notebook_id: str,
    user_id: int,
    kb_item_id: str = None,
):
    """
    Celery task to parse a URL asynchronously.

    Args:
        url: URL to parse
        upload_url_id: Unique ID for this upload
        notebook_id: ID of the notebook
        user_id: ID of the user
        kb_item_id: ID of the existing KB item (optional)

    Returns:
        dict: Result with success status and file_id
    """
    try:
        _validate_task_inputs(url=url, notebook_id=notebook_id, user_id=user_id)
        notebook, user = _get_notebook_and_user(notebook_id, user_id)

        # Get existing KB item or create new one
        if kb_item_id:
            kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id, notebook=notebook)
            logger.info(f"Using existing KB item {kb_item.id} for URL: {url}")
        else:
            kb_item = KnowledgeBaseItem.objects.create(
                notebook=notebook,
                title=f"Processing: {url[:100]}",
                content_type=ContentType.WEBPAGE,
                parsing_status=ParsingStatus.QUEUEING,
                notes=f"URL: {url}",
                tags=[],
                metadata={"url": url, "upload_url_id": upload_url_id},
            )
            logger.info(f"Created KB item {kb_item.id} for URL: {url}")

        # Update status to parsing
        kb_item.parsing_status = ParsingStatus.PARSING
        kb_item.save(update_fields=["parsing_status"])

        # Process the URL using new ingestion orchestrator
        orchestrator = _get_ingestion_orchestrator()

        # Use async_to_sync to run the async method
        result = async_to_sync(orchestrator.ingest_url)(
            url=url,
            user_pk=user_id,
            notebook_id=notebook_id,
            mode="webpage",  # Default to webpage mode
            kb_item_id=str(kb_item.id),
        )

        # Get the file_id from result (should be same as kb_item.id)
        file_id = result.file_id

        if not file_id:
            kb_item.parsing_status = ParsingStatus.FAILED
            kb_item.save(update_fields=["parsing_status"])
            raise URLProcessingError("URL processing did not return a file_id")

        # Refresh KB item from database to get updated content
        kb_item.refresh_from_db()

        # Mark as done if processing completed successfully
        kb_item.parsing_status = ParsingStatus.DONE
        kb_item.save(update_fields=["parsing_status"])

        logger.info(f"Successfully parsed URL to KB item {file_id}")

        # Chain RagFlow upload task
        upload_to_ragflow_task.apply_async(args=[str(file_id)])

        return {"success": True, "file_id": file_id, "upload_url_id": upload_url_id}

    except Exception as e:
        logger.exception(f"Failed to parse URL {url}: {e}")

        # Mark KB item as failed if it exists
        try:
            if "kb_item" in locals():
                kb_item.parsing_status = ParsingStatus.FAILED
                kb_item.metadata = kb_item.metadata or {}
                kb_item.metadata["error"] = str(e)
                kb_item.save(update_fields=["parsing_status", "metadata"])
        except Exception:
            pass

        return {"success": False, "error": str(e)}


@shared_task(bind=True)
def parse_url_with_media_task(
    self,
    url: str,
    upload_url_id: str,
    notebook_id: str,
    user_id: int,
    kb_item_id: str = None,
):
    """
    Celery task to parse a URL with media extraction asynchronously.

    Args:
        url: URL to parse
        upload_url_id: Unique ID for this upload
        notebook_id: ID of the notebook
        user_id: ID of the user
        kb_item_id: ID of the existing KB item (optional)

    Returns:
        dict: Result with success status and file_id
    """
    try:
        _validate_task_inputs(url=url, notebook_id=notebook_id, user_id=user_id)
        notebook, user = _get_notebook_and_user(notebook_id, user_id)

        # Get existing KB item or create new one
        if kb_item_id:
            kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id, notebook=notebook)
            logger.info(
                f"Using existing KB item {kb_item.id} for URL with media: {url}"
            )
        else:
            kb_item = KnowledgeBaseItem.objects.create(
                notebook=notebook,
                title=f"Processing with media: {url[:100]}",
                content_type=ContentType.WEBPAGE,
                parsing_status=ParsingStatus.QUEUEING,
                notes=f"URL with media: {url}",
                tags=[],
                metadata={
                    "url": url,
                    "upload_url_id": upload_url_id,
                    "extract_media": True,
                },
            )
            logger.info(f"Created KB item {kb_item.id} for URL with media: {url}")

        # Update status to parsing
        kb_item.parsing_status = ParsingStatus.PARSING
        kb_item.save(update_fields=["parsing_status"])

        # Process the URL with media using new ingestion orchestrator
        orchestrator = _get_ingestion_orchestrator()

        # Use async_to_sync to run the async method
        result = async_to_sync(orchestrator.ingest_url)(
            url=url,
            user_pk=user_id,
            notebook_id=notebook_id,
            mode="media",  # Media mode for audio/video
            kb_item_id=str(kb_item.id),
        )

        # Get the file_id from result
        file_id = result.file_id

        if not file_id:
            kb_item.parsing_status = ParsingStatus.FAILED
            kb_item.save(update_fields=["parsing_status"])
            raise URLProcessingError("URL processing did not return a file_id")

        # Refresh KB item from database
        kb_item.refresh_from_db()

        # Mark as done
        kb_item.parsing_status = ParsingStatus.DONE
        kb_item.save(update_fields=["parsing_status"])

        logger.info(f"Successfully parsed URL with media to KB item {file_id}")

        # Chain RagFlow upload task
        upload_to_ragflow_task.apply_async(args=[str(file_id)])

        return {"success": True, "file_id": file_id, "upload_url_id": upload_url_id}

    except Exception as e:
        logger.exception(f"Failed to parse URL with media {url}: {e}")

        # Mark KB item as failed if it exists
        try:
            if "kb_item" in locals():
                kb_item.parsing_status = ParsingStatus.FAILED
                kb_item.metadata = kb_item.metadata or {}
                kb_item.metadata["error"] = str(e)
                kb_item.save(update_fields=["parsing_status", "metadata"])
        except Exception:
            pass

        return {"success": False, "error": str(e)}


@shared_task(bind=True)
def parse_document_url_task(
    self,
    url: str,
    upload_url_id: str,
    notebook_id: str,
    user_id: int,
    kb_item_id: str = None,
):
    """
    Celery task to parse a document URL asynchronously.

    Args:
        url: Document URL to parse
        upload_url_id: Unique ID for this upload
        notebook_id: ID of the notebook
        user_id: ID of the user
        kb_item_id: ID of the existing KB item (optional)

    Returns:
        dict: Result with success status and file_id
    """
    try:
        _validate_task_inputs(url=url, notebook_id=notebook_id, user_id=user_id)
        notebook, user = _get_notebook_and_user(notebook_id, user_id)

        # Get existing KB item or create new one
        if kb_item_id:
            kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id, notebook=notebook)
            logger.info(f"Using existing KB item {kb_item.id} for document URL: {url}")
        else:
            kb_item = KnowledgeBaseItem.objects.create(
                notebook=notebook,
                title=f"Processing document: {url[:100]}",
                content_type=ContentType.DOCUMENT,
                parsing_status=ParsingStatus.QUEUEING,
                notes=f"Document URL: {url}",
                tags=[],
                metadata={
                    "url": url,
                    "upload_url_id": upload_url_id,
                    "document_only": True,
                },
            )
            logger.info(f"Created KB item {kb_item.id} for document URL: {url}")

        # Update status to parsing
        kb_item.parsing_status = ParsingStatus.PARSING
        kb_item.save(update_fields=["parsing_status"])

        # Process the document URL using new ingestion orchestrator
        orchestrator = _get_ingestion_orchestrator()

        # Use async_to_sync to run the async method
        result = async_to_sync(orchestrator.ingest_url)(
            url=url,
            user_pk=user_id,
            notebook_id=notebook_id,
            mode="document",  # Document mode for PDF/PPTX
            kb_item_id=str(kb_item.id),
        )

        # Get the file_id from result
        file_id = result.file_id

        if not file_id:
            kb_item.parsing_status = ParsingStatus.FAILED
            kb_item.save(update_fields=["parsing_status"])
            raise URLProcessingError("URL processing did not return a file_id")

        # Refresh KB item from database
        kb_item.refresh_from_db()

        # Mark as done
        kb_item.parsing_status = ParsingStatus.DONE
        kb_item.save(update_fields=["parsing_status"])

        logger.info(f"Successfully parsed document URL to KB item {file_id}")

        # Chain RagFlow upload task
        upload_to_ragflow_task.apply_async(args=[str(file_id)])

        return {"success": True, "file_id": file_id, "upload_url_id": upload_url_id}

    except Exception as e:
        logger.exception(f"Failed to parse document URL {url}: {e}")

        # Mark KB item as failed if it exists
        try:
            if "kb_item" in locals():
                kb_item.parsing_status = ParsingStatus.FAILED
                kb_item.metadata = kb_item.metadata or {}
                kb_item.metadata["error"] = str(e)
                kb_item.save(update_fields=["parsing_status", "metadata"])
        except Exception:
            pass

        return {"success": False, "error": str(e)}


# ============================================================================
# PROCESS TASKS - Full URL/file processing with SSE and batch support
# ============================================================================


@shared_task(bind=True)
def process_url_task(
    self,
    url: str,
    notebook_id: str,
    user_id: int,
    upload_url_id: str = None,
    batch_job_id: str = None,
    batch_item_id: str = None,
    kb_item_id: str = None,
):
    """Process a single URL asynchronously."""
    kb_item = None

    try:
        # Validate inputs
        _validate_task_inputs(url=url, notebook_id=notebook_id, user_id=user_id)

        # Get required objects
        notebook, user = _get_notebook_and_user(notebook_id, user_id)

        # Update batch item status
        _update_batch_item_status(batch_job_id, upload_url_id, "processing")

        # Get or create knowledge item
        from ..utils.helpers import clean_title

        if kb_item_id:
            kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id, notebook=notebook)
        else:
            kb_item = KnowledgeBaseItem.objects.create(
                notebook=notebook,
                title=clean_title(url),
                content_type=ContentType.WEBPAGE,
                parsing_status=ParsingStatus.QUEUEING,
                notes=f"URL: {url}",
                tags=[],
                metadata={"url": url, "upload_url_id": upload_url_id},
            )

        # Update status to parsing
        kb_item.parsing_status = ParsingStatus.PARSING
        kb_item.save(update_fields=["parsing_status"])

        # Publish STARTED event via SSE
        publish_notebook_event(
            notebook_id=str(notebook.id),
            entity="source",
            entity_id=str(kb_item.id),
            status="STARTED",
            payload={
                "upload_url_id": upload_url_id,
                "url": url,
                "title": kb_item.title,
            },
        )

        # Process URL using new ingestion orchestrator
        orchestrator = _get_ingestion_orchestrator()

        # Execute URL processing
        result = async_to_sync(orchestrator.ingest_url)(
            url=url,
            user_pk=user.pk,
            notebook_id=str(notebook.id),
            mode="webpage",  # Default to webpage mode
            kb_item_id=str(kb_item.id),
        )

        # Handle completion
        result = _handle_task_completion(
            kb_item, batch_item_id, batch_job_id, upload_url_id=upload_url_id
        )

        logger.info(f"Successfully processed URL: {url}")
        return result

    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}")
        _handle_task_error(
            kb_item, e, batch_item_id, batch_job_id, upload_url_id=upload_url_id
        )
        raise URLProcessingError(f"Failed to process URL: {str(e)}")


@shared_task(bind=True)
def process_url_media_task(
    self,
    url: str,
    notebook_id: str,
    user_id: int,
    upload_url_id: str = None,
    batch_job_id: str = None,
    batch_item_id: str = None,
    kb_item_id: str = None,
):
    """Process a URL with media extraction."""
    kb_item = None

    try:
        _validate_task_inputs(url=url, notebook_id=notebook_id, user_id=user_id)
        notebook, user = _get_notebook_and_user(notebook_id, user_id)

        _update_batch_item_status(batch_job_id, upload_url_id, "processing")

        from ..utils.helpers import clean_title

        if kb_item_id:
            kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id, notebook=notebook)
        else:
            kb_item = KnowledgeBaseItem.objects.create(
                notebook=notebook,
                title=clean_title(url),
                content_type=ContentType.WEBPAGE,
                parsing_status=ParsingStatus.QUEUEING,
                notes=f"URL with media: {url}",
                tags=[],
                metadata={
                    "url": url,
                    "upload_url_id": upload_url_id,
                    "extract_media": True,
                },
            )

        kb_item.parsing_status = ParsingStatus.PARSING
        kb_item.save(update_fields=["parsing_status"])

        publish_notebook_event(
            notebook_id=str(notebook.id),
            entity="source",
            entity_id=str(kb_item.id),
            status="STARTED",
            payload={
                "upload_url_id": upload_url_id,
                "url": url,
                "title": kb_item.title,
            },
        )

        # Process URL with media using new ingestion orchestrator
        orchestrator = _get_ingestion_orchestrator()
        result = async_to_sync(orchestrator.ingest_url)(
            url=url,
            user_pk=user.pk,
            notebook_id=str(notebook.id),
            mode="media",  # Media mode for audio/video
            kb_item_id=str(kb_item.id),
        )

        result = _handle_task_completion(
            kb_item, batch_item_id, batch_job_id, upload_url_id=upload_url_id
        )

        logger.info(f"Successfully processed URL with media: {url}")
        return result

    except Exception as e:
        logger.error(f"Error processing URL with media {url}: {e}")
        _handle_task_error(
            kb_item, e, batch_item_id, batch_job_id, upload_url_id=upload_url_id
        )
        raise URLProcessingError(f"Failed to process URL with media: {str(e)}")


@shared_task(bind=True)
def process_url_document_task(
    self,
    url: str,
    notebook_id: str,
    user_id: int,
    upload_url_id: str = None,
    batch_job_id: str = None,
    batch_item_id: str = None,
    kb_item_id: str = None,
):
    """Process a document URL."""
    kb_item = None

    try:
        _validate_task_inputs(url=url, notebook_id=notebook_id, user_id=user_id)
        notebook, user = _get_notebook_and_user(notebook_id, user_id)

        _update_batch_item_status(batch_job_id, upload_url_id, "processing")

        from ..utils.helpers import clean_title

        if kb_item_id:
            kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id, notebook=notebook)
        else:
            kb_item = KnowledgeBaseItem.objects.create(
                notebook=notebook,
                title=clean_title(url),
                content_type=ContentType.DOCUMENT,
                parsing_status=ParsingStatus.QUEUEING,
                notes=f"Document URL: {url}",
                tags=[],
                metadata={
                    "url": url,
                    "upload_url_id": upload_url_id,
                    "document_only": True,
                },
            )

        kb_item.parsing_status = ParsingStatus.PARSING
        kb_item.save(update_fields=["parsing_status"])

        publish_notebook_event(
            notebook_id=str(notebook.id),
            entity="source",
            entity_id=str(kb_item.id),
            status="STARTED",
            payload={
                "upload_url_id": upload_url_id,
                "url": url,
                "title": kb_item.title,
            },
        )

        # Process document URL using new ingestion orchestrator
        orchestrator = _get_ingestion_orchestrator()
        result = async_to_sync(orchestrator.ingest_url)(
            url=url,
            user_pk=user.pk,
            notebook_id=str(notebook.id),
            mode="document",  # Document mode for PDF/PPTX
            kb_item_id=str(kb_item.id),
        )

        result = _handle_task_completion(
            kb_item, batch_item_id, batch_job_id, upload_url_id=upload_url_id
        )

        logger.info(f"Successfully processed document URL: {url}")
        return result

    except Exception as e:
        logger.error(f"Error processing document URL {url}: {e}")
        _handle_task_error(
            kb_item, e, batch_item_id, batch_job_id, upload_url_id=upload_url_id
        )
        raise URLProcessingError(f"Failed to process document URL: {str(e)}")


@shared_task(bind=True)
def process_file_upload_task(
    self,
    file_data: bytes,
    filename: str,
    notebook_id: str,
    user_id: int,
    upload_file_id: str = None,
    batch_job_id: str = None,
    batch_item_id: str = None,
    kb_item_id: str = None,
):
    """Process a single file upload asynchronously."""
    kb_item = None

    try:
        # Validate inputs
        _validate_task_inputs(
            file_data=file_data,
            filename=filename,
            notebook_id=notebook_id,
            user_id=user_id,
        )

        # Get required objects
        notebook, user = _get_notebook_and_user(notebook_id, user_id)

        # Update batch item status
        _update_batch_item_status(batch_job_id, upload_file_id, "processing")

        # Check file size limit
        file_size_mb = len(file_data) / 1024 / 1024
        logger.info(f"Processing file {filename}: {file_size_mb:.2f} MB")

        MAX_FILE_SIZE_MB = 500
        if file_size_mb > MAX_FILE_SIZE_MB:
            raise ValidationError(
                f"File too large: {file_size_mb:.2f}MB (max: {MAX_FILE_SIZE_MB}MB)"
            )

        # Get or create knowledge item
        if kb_item_id:
            kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id, notebook=notebook)
        else:
            kb_item = KnowledgeBaseItem.objects.create(
                notebook=notebook,
                title=filename,
                content_type=ContentType.DOCUMENT,
                parsing_status=ParsingStatus.QUEUEING,
                notes=f"File upload: {filename}",
                tags=[],
                metadata={"upload_file_id": upload_file_id, "filename": filename},
            )

        # Update status to parsing
        kb_item.parsing_status = ParsingStatus.PARSING
        if upload_file_id:
            kb_item.metadata = kb_item.metadata or {}
            kb_item.metadata["upload_file_id"] = upload_file_id
            kb_item.save(update_fields=["parsing_status", "metadata"])
        else:
            kb_item.save(update_fields=["parsing_status"])

        # Publish STARTED event via SSE
        publish_notebook_event(
            notebook_id=str(notebook.id),
            entity="source",
            entity_id=str(kb_item.id),
            status="STARTED",
            payload={
                "upload_file_id": upload_file_id,
                "filename": filename,
            },
        )

        # Process file using upload processor
        from ..processors.upload_processor import UploadProcessor

        upload_processor = UploadProcessor()
        temp_file = ContentFile(file_data, name=filename)

        result = async_to_sync(upload_processor.process_upload)(
            temp_file,
            upload_file_id or uuid4().hex,
            user_pk=user.pk,
            notebook_id=notebook.id,
            kb_item_id=str(kb_item.id),
        )

        # Handle completion
        result = _handle_task_completion(
            kb_item, batch_item_id, batch_job_id, upload_file_id=upload_file_id
        )
        result["file_id"] = kb_item.id  # Ensure correct file ID

        logger.info(f"Successfully processed file upload: {filename}")
        return result

    except Exception as e:
        logger.error(f"Error processing file upload {filename}: {e}")
        _handle_task_error(
            kb_item, e, batch_item_id, batch_job_id, upload_file_id=upload_file_id
        )
        raise FileProcessingError(f"Failed to process file upload: {str(e)}")


# ============================================================================
# IMAGE CAPTION GENERATION
# ============================================================================


@shared_task(bind=True)
def generate_image_captions_task(self, kb_item_id: str):
    """Generate captions for images in a knowledge base item asynchronously.

    State handling: Uses captioning_status field (independent of parsing_status)
    - Set captioning_status='in_progress' while running
    - On success, set captioning_status='completed'
    - On failure, set captioning_status='failed'
    - parsing_status remains unchanged (already 'done')
    """
    kb_item = None
    try:
        kb_item = get_object_or_404(KnowledgeBaseItem, id=kb_item_id)

        # Set to in_progress (don't touch parsing_status)
        kb_item.captioning_status = CaptioningStatus.IN_PROGRESS
        kb_item.save(update_fields=["captioning_status", "updated_at"])

        # Import caption generator utility lazily
        from ..utils.image_processing.caption_generator import (
            populate_image_captions_for_kb_item,
        )

        # Generate captions
        result = populate_image_captions_for_kb_item(kb_item)

        if result.get("success"):
            logger.info(f"Successfully generated captions for KB item {kb_item_id}")
            kb_item.captioning_status = CaptioningStatus.COMPLETED
            kb_item.save(update_fields=["captioning_status", "updated_at"])
            return {
                "success": True,
                "captions_generated": result.get("captions_count", 0),
            }
        else:
            logger.warning(
                f"Failed to generate captions for KB item {kb_item_id}: {result.get('error')}"
            )
            kb_item.captioning_status = CaptioningStatus.FAILED
            # Keep error in metadata for observability
            kb_item.metadata = kb_item.metadata or {}
            kb_item.metadata["caption_error"] = result.get("error")
            kb_item.save(update_fields=["captioning_status", "metadata", "updated_at"])
            return {"success": False, "error": result.get("error")}

    except Exception as e:
        logger.error(f"Error generating captions for KB item {kb_item_id}: {e}")
        if kb_item:
            kb_item.captioning_status = CaptioningStatus.FAILED
            kb_item.metadata = kb_item.metadata or {}
            kb_item.metadata["caption_error"] = str(e)
            kb_item.save(update_fields=["captioning_status", "metadata", "updated_at"])
        raise ValidationError(f"Failed to generate captions: {str(e)}")
