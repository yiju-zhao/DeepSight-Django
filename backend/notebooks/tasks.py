"""
Refactored Celery tasks for async processing of notebook content.

This module follows Python best practices with modular design,
DRY principle, and proper error handling.
"""

import logging
from typing import Optional, Dict, Any, Tuple
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from uuid import uuid4

from .models import KnowledgeBaseItem, Notebook, BatchJob, BatchJobItem
from .exceptions import (
    FileProcessingError,
    URLProcessingError,
    ValidationError
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS - Shared functionality extracted for reuse
# ============================================================================

def _validate_task_inputs(url: str = None, notebook_id: str = None, user_id: int = None, 
                         file_data: bytes = None, filename: str = None) -> None:
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


def _get_notebook_and_user(notebook_id: str, user_id: int) -> Tuple[Notebook, Any]:
    """Get notebook and user objects with validation."""
    try:
        user = User.objects.get(id=user_id)
        notebook = get_object_or_404(Notebook, id=notebook_id, user=user)
        return notebook, user
    except User.DoesNotExist:
        raise ValidationError(f"User {user_id} not found")


def _get_or_create_knowledge_item(kb_item_id: str = None, notebook: Notebook = None, 
                                 title: str = None) -> KnowledgeBaseItem:
    """Get existing knowledge item or create new one if needed."""
    if kb_item_id:
        try:
            return KnowledgeBaseItem.objects.get(id=kb_item_id, notebook=notebook)
        except KnowledgeBaseItem.DoesNotExist:
            logger.error(f"KnowledgeBaseItem {kb_item_id} not found in notebook {notebook.id}")
            raise ValidationError(f"Knowledge item {kb_item_id} not found")
    
    # Create new knowledge item if no ID provided
    if not title:
        raise ValidationError("Title is required for new knowledge items")
    
    return KnowledgeBaseItem(
        notebook=notebook,
        title=title,
        content_type="document",
        parsing_status="queueing",
        notes=f"Processing {title}",
        tags=[],
        file_metadata={}
    )


@shared_task(bind=True)
def upload_to_ragflow_task(self, kb_item_id: str):
    """
    Separate task to handle RagFlow upload.

    This task is chained after file processing to ensure the KB item content
    is fully saved to the database before attempting the upload.

    Args:
        kb_item_id: ID of the KnowledgeBaseItem to upload to RagFlow

    Returns:
        dict: Upload result with success status
    """
    try:
        # Fetch the KB item from database to ensure we have the latest content
        kb_item = KnowledgeBaseItem.objects.select_related('notebook').get(id=kb_item_id)

        # Check if we have a processed file in MinIO to upload
        if not kb_item.file_object_key:
            logger.warning(f"KB item {kb_item.id} has no processed file to upload to RagFlow")
            return {"success": False, "error": "No processed file available for upload"}

        from infrastructure.ragflow.client import get_ragflow_client
        from infrastructure.storage.adapters import get_storage_adapter

        ragflow_client = get_ragflow_client()
        storage_adapter = get_storage_adapter()

        # Upload to RagFlow - we need the notebook's RagFlow dataset ID
        if not kb_item.notebook.ragflow_dataset_id:
            logger.warning(f"No RagFlow dataset ID found for notebook {kb_item.notebook.id}")
            return {"success": False, "error": "No RagFlow dataset ID configured"}

        # Get the processed markdown file content from MinIO
        try:
            file_content = storage_adapter.get_file_content(
                kb_item.file_object_key,
                str(kb_item.notebook.user_id)
            )

            # Determine filename - prefer original filename with .md extension
            filename = kb_item.title
            if kb_item.file_metadata and isinstance(kb_item.file_metadata, dict):
                original_filename = kb_item.file_metadata.get('original_filename', kb_item.title)
                # Convert to .md extension for RagFlow
                if '.' in original_filename:
                    filename = original_filename.rsplit('.', 1)[0] + '.md'
                else:
                    filename = original_filename + '.md'
            elif not filename.endswith('.md'):
                filename = filename + '.md'

        except Exception as storage_error:
            error_msg = f"Failed to retrieve processed file from storage: {storage_error}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        upload_result = ragflow_client.upload_document_file(
            dataset_id=kb_item.notebook.ragflow_dataset_id,
            file_content=file_content,
            filename=filename
        )

        if upload_result and upload_result.get('id'):
            document_id = upload_result.get('id')
            logger.info(f"Successfully uploaded processed file for KB item {kb_item.id} to RagFlow: {document_id}")

            # Store the RagFlow document ID in the knowledge base item metadata
            kb_item.metadata = kb_item.metadata or {}
            kb_item.metadata['ragflow_document_id'] = document_id
            kb_item.save(update_fields=['metadata'])

            # Trigger document parsing after successful upload
            try:
                parse_result = ragflow_client.parse_documents(
                    dataset_id=kb_item.notebook.ragflow_dataset_id,
                    document_ids=[document_id]
                )

                if parse_result:
                    logger.info(f"Successfully triggered parsing for RagFlow document {document_id}")
                    kb_item.metadata['ragflow_parsing_triggered'] = True
                    kb_item.save(update_fields=['metadata'])
                else:
                    logger.warning(f"Failed to trigger parsing for RagFlow document {document_id}")
                    kb_item.metadata['ragflow_parsing_error'] = "Failed to trigger parsing"
                    kb_item.save(update_fields=['metadata'])

            except Exception as parse_error:
                logger.error(f"Error triggering parsing for RagFlow document {document_id}: {parse_error}")
                kb_item.metadata['ragflow_parsing_error'] = str(parse_error)
                kb_item.save(update_fields=['metadata'])
                # Don't fail the main task if parsing trigger fails

            return {"success": True, "ragflow_document_id": document_id, "parsing_triggered": parse_result}
        else:
            logger.warning(f"Failed to upload processed file for KB item {kb_item.id} to RagFlow")
            return {"success": False, "error": "Upload failed - no document ID returned"}

    except KnowledgeBaseItem.DoesNotExist:
        error_msg = f"KB item {kb_item_id} not found"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    except Exception as ragflow_error:
        error_msg = f"RagFlow upload error for KB item {kb_item_id}: {ragflow_error}"
        logger.error(error_msg)
        return {"success": False, "error": str(ragflow_error)}




def _update_batch_item_status(batch_item_id: Optional[str], status: str, 
                            result_data: Dict = None, error_message: str = None) -> None:
    """Update batch item status if batch processing is enabled."""
    if not batch_item_id:
        return
        
    try:
        batch_item = BatchJobItem.objects.get(id=batch_item_id)
        batch_item.status = status
        
        if result_data:
            batch_item.result_data = result_data
        if error_message:
            batch_item.error_message = error_message
            
        batch_item.save()
        
    except ObjectDoesNotExist:
        logger.warning(f"Batch item {batch_item_id} not found")


def _check_batch_completion(batch_job_id: Optional[str]) -> None:
    """Check if batch job is complete and update its status."""
    if not batch_job_id:
        return
        
    try:
        batch_job = BatchJob.objects.get(id=batch_job_id)
        items = batch_job.items.all()
        
        # Check if any items are still pending or processing
        if items.filter(status__in=['pending', 'processing']).exists():
            return  # Still has items in progress
        
        # All items are either completed or failed
        completed_count = items.filter(status='completed').count()
        failed_count = items.filter(status='failed').count()
        
        # Update batch job status
        if failed_count == 0:
            batch_job.status = 'completed'
        elif completed_count == 0:
            batch_job.status = 'failed'
        else:
            batch_job.status = 'partially_completed'
        
        batch_job.completed_items = completed_count
        batch_job.failed_items = failed_count
        batch_job.save()
        
        logger.info(f"Batch job {batch_job_id} completed: {completed_count} successful, {failed_count} failed")
        
    except ObjectDoesNotExist:
        logger.warning(f"Batch job {batch_job_id} not found")


def _handle_task_completion(kb_item: KnowledgeBaseItem, 
                          batch_item_id: str = None, batch_job_id: str = None) -> Dict[str, Any]:
    """Handle common task completion logic."""
    # Determine if captioning is required based on available image info
    image_count = 0
    try:
        if isinstance(kb_item.file_metadata, dict):
            image_count = int(kb_item.file_metadata.get("image_count", 0) or 0)
    except Exception:
        image_count = 0

    if image_count > 0:
        # Move to captioning and schedule caption generation
        kb_item.parsing_status = "captioning"
        kb_item.save(update_fields=["parsing_status", "updated_at"])

        try:
            from .tasks import generate_image_captions_task
            generate_image_captions_task.delay(str(kb_item.id))
        except Exception as e:
            # If scheduling fails, mark as failed and record error
            logger.error(f"Failed to schedule caption generation for KB item {kb_item.id}: {e}")
            kb_item.parsing_status = "failed"
            kb_item.metadata = kb_item.metadata or {}
            kb_item.metadata["caption_schedule_error"] = str(e)
            kb_item.save(update_fields=["parsing_status", "metadata", "updated_at"])
    else:
        # No images; complete immediately
        kb_item.parsing_status = "done"
        kb_item.save(update_fields=["parsing_status", "updated_at"])
    
    # Chain RagFlow upload task to ensure content is fully saved
    try:
        upload_to_ragflow_task.delay(str(kb_item.id))
        logger.info(f"Chained RagFlow upload task for KB item {kb_item.id}")
    except Exception as e:
        logger.error(f"Failed to chain RagFlow upload task for KB item {kb_item.id}: {e}")
        # Don't fail the main task if chaining fails
    
    # Update batch status
    _update_batch_item_status(batch_item_id, 'completed', result_data={"file_id": str(kb_item.id)})
    _check_batch_completion(batch_job_id)
    
    return {"file_id": str(kb_item.id), "status": "completed"}


def _handle_task_error(kb_item: KnowledgeBaseItem, error: Exception, 
                      batch_item_id: str = None, batch_job_id: str = None) -> None:
    """Handle common task error logic."""
    # Update KB item status
    if kb_item:
        kb_item.parsing_status = "done"
        kb_item.metadata = kb_item.metadata or {}
        kb_item.metadata["error_message"] = str(error)
        kb_item.save(update_fields=["parsing_status", "metadata"])
    
    # Update batch status
    _update_batch_item_status(batch_item_id, 'failed', error_message=str(error))
    _check_batch_completion(batch_job_id)


# ============================================================================
# TASK IMPLEMENTATIONS - Clean, focused task functions
# ============================================================================

@shared_task(bind=True)
def process_url_task(self, url: str, notebook_id: str, user_id: int, 
                    upload_url_id: str = None, batch_job_id: str = None, 
                    batch_item_id: str = None, kb_item_id: str = None):
    """Process a single URL asynchronously."""
    kb_item = None
    
    try:
        # Validate inputs
        _validate_task_inputs(url=url, notebook_id=notebook_id, user_id=user_id)
        
        # Get required objects
        notebook, user = _get_notebook_and_user(notebook_id, user_id)
        
        # Update batch item status
        _update_batch_item_status(batch_item_id, 'processing')
        
        # Get or create knowledge item
        from .utils.helpers import clean_title
        kb_item = _get_or_create_knowledge_item(
            kb_item_id=kb_item_id,
            notebook=notebook,
            title=clean_title(url)
        )
        
        if not kb_item_id:  # New item, save it
            kb_item.save()
        
        # Update status to parsing
        kb_item.parsing_status = "parsing"
        kb_item.save(update_fields=["parsing_status"])
        
        # Process URL using URL extractor
        from .processors.url_extractor import URLExtractor
        url_extractor = URLExtractor()
        
        async def process_url_async():
            if kb_item_id:
                return await url_extractor.process_url_update_existing(
                    url=url,
                    kb_item_id=str(kb_item.id),
                    upload_url_id=upload_url_id or uuid4().hex,
                    user_id=user.pk,
                    notebook_id=str(notebook.id)
                )
            else:
                return await url_extractor.process_url(
                    url=url,
                    upload_url_id=upload_url_id or uuid4().hex,
                    user_id=user.pk,
                    notebook_id=str(notebook.id)
                )
        
        # Execute URL processing
        result = async_to_sync(process_url_async)()
        
        # Handle completion
        result = _handle_task_completion(kb_item, batch_item_id, batch_job_id)
        
        logger.info(f"Successfully processed URL: {url}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}")
        _handle_task_error(kb_item, e, batch_item_id, batch_job_id)
        raise URLProcessingError(f"Failed to process URL: {str(e)}")


@shared_task(bind=True)
def process_url_media_task(self, url: str, notebook_id: str, user_id: int, 
                          upload_url_id: str = None, batch_job_id: str = None, 
                          batch_item_id: str = None):
    """Process a single URL with media extraction asynchronously."""
    kb_item = None
    
    try:
        # Validate inputs
        _validate_task_inputs(url=url, notebook_id=notebook_id, user_id=user_id)
        
        # Get required objects
        notebook, user = _get_notebook_and_user(notebook_id, user_id)
        
        # Update batch item status
        _update_batch_item_status(batch_item_id, 'processing')
        
        # Create knowledge item
        from .utils.helpers import clean_title
        kb_item = KnowledgeBaseItem(
            notebook=notebook,
            title=clean_title(url),
            content_type="document",
            parsing_status="queueing",
            notes=f"Processing URL with media: {url}",
            tags=[],
            file_metadata={}
        )
        kb_item.save()
        
        # Update status to parsing
        kb_item.parsing_status = "parsing"
        kb_item.save(update_fields=["parsing_status"])
        
        # Process URL with media extraction
        from .processors.url_extractor import URLExtractor
        url_extractor = URLExtractor()
        
        result = async_to_sync(url_extractor.process_url_with_media)(
            url=url,
            upload_url_id=upload_url_id or uuid4().hex,
            user_id=user.pk,
            notebook_id=str(notebook.id)
        )
        
        # Handle completion
        result = _handle_task_completion(kb_item, batch_item_id, batch_job_id)
        
        logger.info(f"Successfully processed URL with media: {url}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing URL with media {url}: {e}")
        _handle_task_error(kb_item, e, batch_item_id, batch_job_id)
        raise URLProcessingError(f"Failed to process URL with media: {str(e)}")


@shared_task(bind=True)
def process_url_document_task(self, url: str, notebook_id: str, user_id: int, 
                             upload_url_id: str = None, batch_job_id: str = None, 
                             batch_item_id: str = None):
    """Process a single document URL asynchronously."""
    kb_item = None
    
    try:
        # Validate inputs
        _validate_task_inputs(url=url, notebook_id=notebook_id, user_id=user_id)
        
        # Get required objects
        notebook, user = _get_notebook_and_user(notebook_id, user_id)
        
        # Update batch item status
        _update_batch_item_status(batch_item_id, 'processing')
        
        # Create knowledge item
        from .utils.helpers import clean_title
        kb_item = KnowledgeBaseItem(
            notebook=notebook,
            title=clean_title(url),
            content_type="document",
            parsing_status="queueing",
            notes=f"Processing document URL: {url}",
            tags=[],
            file_metadata={}
        )
        kb_item.save()
        
        # Update status to parsing
        kb_item.parsing_status = "parsing"
        kb_item.save(update_fields=["parsing_status"])
        
        # Process document URL
        from .processors.url_extractor import URLExtractor
        url_extractor = URLExtractor()
        
        result = async_to_sync(url_extractor.process_document_url)(
            url=url,
            upload_url_id=upload_url_id or uuid4().hex,
            user_id=user.pk,
            notebook_id=str(notebook.id)
        )
        
        # Handle completion
        result = _handle_task_completion(kb_item, batch_item_id, batch_job_id)
        
        logger.info(f"Successfully processed document URL: {url}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing document URL {url}: {e}")
        _handle_task_error(kb_item, e, batch_item_id, batch_job_id)
        raise URLProcessingError(f"Failed to process document URL: {str(e)}")


@shared_task(bind=True)
def process_file_upload_task(self, file_data: bytes, filename: str, notebook_id: str, 
                           user_id: int, upload_file_id: str = None, batch_job_id: str = None, 
                           batch_item_id: str = None, kb_item_id: str = None):
    """Process a single file upload asynchronously."""
    kb_item = None
    
    try:
        # Validate inputs
        _validate_task_inputs(
            file_data=file_data, filename=filename, 
            notebook_id=notebook_id, user_id=user_id
        )
        
        # Get required objects
        notebook, user = _get_notebook_and_user(notebook_id, user_id)
        
        # Update batch item status
        _update_batch_item_status(batch_item_id, 'processing')
        
        # Check file size limit
        file_size_mb = len(file_data) / 1024 / 1024
        logger.info(f"Processing file {filename}: {file_size_mb:.2f} MB")
        
        MAX_FILE_SIZE_MB = 500
        if file_size_mb > MAX_FILE_SIZE_MB:
            raise ValidationError(f"File too large: {file_size_mb:.2f}MB (max: {MAX_FILE_SIZE_MB}MB)")
        
        # Get or create knowledge item
        kb_item = _get_or_create_knowledge_item(
            kb_item_id=kb_item_id,
            notebook=notebook,
            title=filename
        )
        
        if not kb_item_id:  # New item, save it
            kb_item.save()
        
        # Update status to parsing
        kb_item.parsing_status = "parsing"
        kb_item.save(update_fields=["parsing_status"])
        
        # Process file using upload processor
        from .processors.upload_processor import UploadProcessor
        from django.core.files.base import ContentFile
        
        upload_processor = UploadProcessor()
        temp_file = ContentFile(file_data, name=filename)
        
        result = async_to_sync(upload_processor.process_upload)(
            temp_file, 
            upload_file_id or uuid4().hex, 
            user_pk=user.pk, 
            notebook_id=notebook.id, 
            kb_item_id=str(kb_item.id)
        )
        
        # Handle completion
        result = _handle_task_completion(kb_item, batch_item_id, batch_job_id)
        result["file_id"] = kb_item.id  # Ensure correct file ID
        
        logger.info(f"Successfully processed file upload: {filename}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing file upload {filename}: {e}")
        _handle_task_error(kb_item, e, batch_item_id, batch_job_id)
        raise FileProcessingError(f"Failed to process file upload: {str(e)}")



@shared_task(bind=True)
def generate_image_captions_task(self, kb_item_id: str):
    """Generate captions for images in a knowledge base item asynchronously.

    State handling (single-field state machine):
    - Ensure parsing_status is 'captioning' while running
    - On success, set parsing_status='done'
    - On failure, set parsing_status='failed'
    """
    kb_item = None
    try:
        kb_item = get_object_or_404(KnowledgeBaseItem, id=kb_item_id)

        # Move to captioning if not already in a terminal state
        if kb_item.parsing_status not in ["captioning", "done", "failed"]:
            kb_item.parsing_status = "captioning"
            kb_item.save(update_fields=["parsing_status", "updated_at"])

        # Import caption generator utility lazily
        from .utils.image_processing.caption_generator import populate_image_captions_for_kb_item

        # Generate captions
        result = populate_image_captions_for_kb_item(kb_item)

        if result.get('success'):
            logger.info(f"Successfully generated captions for KB item {kb_item_id}")
            kb_item.parsing_status = "done"
            kb_item.save(update_fields=["parsing_status", "updated_at"])
            return {"success": True, "captions_generated": result.get('captions_count', 0)}
        else:
            logger.warning(f"Failed to generate captions for KB item {kb_item_id}: {result.get('error')}")
            kb_item.parsing_status = "failed"
            # Keep error in metadata for observability
            kb_item.metadata = kb_item.metadata or {}
            kb_item.metadata['caption_error'] = result.get('error')
            kb_item.save(update_fields=["parsing_status", "metadata", "updated_at"])
            return {"success": False, "error": result.get('error')}

    except Exception as e:
        logger.error(f"Error generating captions for KB item {kb_item_id}: {e}")
        if kb_item:
            kb_item.parsing_status = "failed"
            kb_item.metadata = kb_item.metadata or {}
            kb_item.metadata['caption_error'] = str(e)
            kb_item.save(update_fields=["parsing_status", "metadata", "updated_at"])
        raise ValidationError(f"Failed to generate captions: {str(e)}")



# ============================================================================
# UTILITY TASKS - Simple maintenance and monitoring tasks
# ============================================================================

@shared_task
def cleanup_old_batch_jobs():
    """Cleanup old completed batch jobs (older than 7 days)."""
    from datetime import timedelta
    from django.utils import timezone
    
    try:
        cutoff_date = timezone.now() - timedelta(days=7)
        old_jobs = BatchJob.objects.filter(
            status__in=['completed', 'failed', 'partially_completed'],
            updated_at__lt=cutoff_date
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
    """Simple health check task for monitoring Celery workers."""
    from datetime import datetime
    
    logger.info("Health check task executed successfully")
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "worker": "celery"
    }
