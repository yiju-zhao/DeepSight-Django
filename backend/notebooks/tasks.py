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

        # Mark as uploading to RagFlow
        kb_item.mark_ragflow_uploading()

        # Check if we have a processed file in MinIO to upload
        if not kb_item.file_object_key:
            logger.warning(f"KB item {kb_item.id} has no processed file to upload to RagFlow")
            kb_item.mark_ragflow_failed("No processed file available for upload")
            return {"success": False, "error": "No processed file available for upload"}

        from infrastructure.ragflow.client import get_ragflow_client
        from infrastructure.storage.adapters import get_storage_adapter

        ragflow_client = get_ragflow_client()
        storage_adapter = get_storage_adapter()

        # Upload to RagFlow - we need the notebook's RagFlow dataset ID
        if not kb_item.notebook.ragflow_dataset_id:
            logger.warning(f"No RagFlow dataset ID found for notebook {kb_item.notebook.id}")
            kb_item.mark_ragflow_failed("No RagFlow dataset ID configured")
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
            kb_item.mark_ragflow_failed(error_msg)
            return {"success": False, "error": error_msg}

        logger.info(f"Uploading file '{filename}' to RagFlow dataset {kb_item.notebook.ragflow_dataset_id}")
        upload_result = ragflow_client.upload_document_file(
            dataset_id=kb_item.notebook.ragflow_dataset_id,
            file_content=file_content,
            filename=filename
        )
        logger.info(f"RagFlow upload result: {upload_result}")

        if upload_result and upload_result.get('id'):
            document_id = upload_result.get('id')
            logger.info(f"Successfully uploaded processed file for KB item {kb_item.id} to RagFlow: {document_id}")

            # Store the RagFlow document ID and mark as parsing atomically
            try:
                kb_item.ragflow_document_id = document_id
                kb_item.ragflow_processing_status = 'parsing'
                kb_item.save(update_fields=['ragflow_document_id', 'ragflow_processing_status', 'updated_at'])
                logger.info(f"Saved RagFlow document ID {document_id} to KB item {kb_item.id} with status 'parsing'")

                # Verify the save was successful by reloading from database
                kb_item.refresh_from_db()
                if kb_item.ragflow_document_id == document_id:
                    logger.info(f"Verified: RagFlow document ID {document_id} successfully saved to database")
                else:
                    logger.warning(f"Database verification failed: expected {document_id}, got {kb_item.ragflow_document_id}")

            except Exception as save_error:
                logger.error(f"Failed to save RagFlow document ID {document_id} to KB item {kb_item.id}: {save_error}")
                # Still continue with parsing trigger attempt
                kb_item.ragflow_processing_status = 'parsing'  # At least update status in memory

            # Trigger dataset update to refresh embeddings and settings
            try:
                ragflow_client.update_dataset(kb_item.notebook.ragflow_dataset_id)
                logger.info(f"Successfully updated RagFlow dataset {kb_item.notebook.ragflow_dataset_id} after file upload")
            except Exception as update_error:
                # Log error but don't fail the entire upload process
                logger.warning(f"Failed to update dataset {kb_item.notebook.ragflow_dataset_id}: {update_error}")

            # Trigger document parsing after successful upload
            try:
                parse_result = ragflow_client.parse_documents(
                    dataset_id=kb_item.notebook.ragflow_dataset_id,
                    document_ids=[document_id]
                )

                if parse_result:
                    logger.info(f"Successfully triggered parsing for RagFlow document {document_id}")
                    # Mark as parsing in progress
                    kb_item.mark_ragflow_parsing()

                    # Schedule status checking task
                    try:
                        check_ragflow_status_task.apply_async(
                            args=[str(kb_item.id)],
                            countdown=30  # Check status after 30 seconds
                        )
                    except Exception as schedule_error:
                        logger.warning(f"Failed to schedule status check for {document_id}: {schedule_error}")
                else:
                    logger.warning(f"Failed to trigger parsing for RagFlow document {document_id}")
                    kb_item.mark_ragflow_failed("Failed to trigger parsing")

            except Exception as parse_error:
                logger.error(f"Error triggering parsing for RagFlow document {document_id}: {parse_error}")
                kb_item.mark_ragflow_failed(f"Parsing trigger error: {parse_error}")
                # Don't fail the main task if parsing trigger fails

            return {"success": True, "ragflow_document_id": document_id, "parsing_triggered": parse_result}
        else:
            logger.warning(f"Failed to upload processed file for KB item {kb_item.id} to RagFlow")
            kb_item.mark_ragflow_failed("Upload failed - no document ID returned")
            return {"success": False, "error": "Upload failed - no document ID returned"}

    except KnowledgeBaseItem.DoesNotExist:
        error_msg = f"KB item {kb_item_id} not found"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    except Exception as ragflow_error:
        error_msg = f"RagFlow upload error for KB item {kb_item_id}: {ragflow_error}"
        logger.error(error_msg)

        # Mark as failed if KB item exists
        try:
            kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id)
            kb_item.mark_ragflow_failed(str(ragflow_error))
        except KnowledgeBaseItem.DoesNotExist:
            pass

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


@shared_task(bind=True)
def parse_url_task(self, url: str, upload_url_id: str, notebook_id: str, user_id: int, kb_item_id: str = None):
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
                content_type="webpage",
                parsing_status="queueing",
                notes=f"URL: {url}",
                tags=[],
                metadata={'url': url, 'upload_url_id': upload_url_id}
            )
            logger.info(f"Created KB item {kb_item.id} for URL: {url}")

        # Update status to parsing
        kb_item.parsing_status = "parsing"
        kb_item.save(update_fields=['parsing_status'])

        # Process the URL
        from notebooks.processors.url_extractor import URLExtractor
        url_extractor = URLExtractor()

        # Pass kb_item_id to update existing item instead of creating new one
        result = async_to_sync(url_extractor.process_url)(
            url=url,
            upload_url_id=upload_url_id,
            user_id=user_id,
            notebook_id=notebook_id,
            kb_item_id=str(kb_item.id)
        )

        # Get the file_id from result (should be same as kb_item.id)
        file_id = result.get("file_id")

        if not file_id:
            kb_item.parsing_status = "failed"
            kb_item.save(update_fields=['parsing_status'])
            raise URLProcessingError("URL processing did not return a file_id")

        # Refresh KB item from database to get updated content
        kb_item.refresh_from_db()

        # Mark as done if processing completed successfully
        kb_item.parsing_status = "done"
        kb_item.save(update_fields=['parsing_status'])

        logger.info(f"Successfully parsed URL to KB item {file_id}")

        # Chain RagFlow upload task
        upload_to_ragflow_task.apply_async(args=[str(file_id)])

        return {
            "success": True,
            "file_id": file_id,
            "upload_url_id": upload_url_id
        }

    except Exception as e:
        logger.exception(f"Failed to parse URL {url}: {e}")

        # Mark KB item as failed if it exists
        try:
            if 'kb_item' in locals():
                kb_item.parsing_status = "failed"
                kb_item.metadata = kb_item.metadata or {}
                kb_item.metadata['error'] = str(e)
                kb_item.save(update_fields=['parsing_status', 'metadata'])
        except Exception:
            pass

        return {
            "success": False,
            "error": str(e)
        }


@shared_task(bind=True)
def parse_url_with_media_task(self, url: str, upload_url_id: str, notebook_id: str, user_id: int, kb_item_id: str = None):
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
            logger.info(f"Using existing KB item {kb_item.id} for URL with media: {url}")
        else:
            kb_item = KnowledgeBaseItem.objects.create(
                notebook=notebook,
                title=f"Processing with media: {url[:100]}",
                content_type="webpage",
                parsing_status="queueing",
                notes=f"URL with media: {url}",
                tags=[],
                metadata={'url': url, 'upload_url_id': upload_url_id, 'extract_media': True}
            )
            logger.info(f"Created KB item {kb_item.id} for URL with media: {url}")

        # Update status to parsing
        kb_item.parsing_status = "parsing"
        kb_item.save(update_fields=['parsing_status'])

        # Process the URL with media
        from notebooks.processors.url_extractor import URLExtractor
        url_extractor = URLExtractor()

        # Pass kb_item_id to update existing item instead of creating new one
        result = async_to_sync(url_extractor.process_url_with_media)(
            url=url,
            upload_url_id=upload_url_id,
            user_id=user_id,
            notebook_id=notebook_id,
            kb_item_id=str(kb_item.id)
        )

        # Get the file_id from result
        file_id = result.get("file_id")

        if not file_id:
            kb_item.parsing_status = "failed"
            kb_item.save(update_fields=['parsing_status'])
            raise URLProcessingError("URL processing did not return a file_id")

        # Refresh KB item from database
        kb_item.refresh_from_db()

        # Mark as done
        kb_item.parsing_status = "done"
        kb_item.save(update_fields=['parsing_status'])

        logger.info(f"Successfully parsed URL with media to KB item {file_id}")

        # Chain RagFlow upload task
        upload_to_ragflow_task.apply_async(args=[str(file_id)])

        return {
            "success": True,
            "file_id": file_id,
            "upload_url_id": upload_url_id
        }

    except Exception as e:
        logger.exception(f"Failed to parse URL with media {url}: {e}")

        # Mark KB item as failed if it exists
        try:
            if 'kb_item' in locals():
                kb_item.parsing_status = "failed"
                kb_item.metadata = kb_item.metadata or {}
                kb_item.metadata['error'] = str(e)
                kb_item.save(update_fields=['parsing_status', 'metadata'])
        except Exception:
            pass

        return {
            "success": False,
            "error": str(e)
        }


@shared_task(bind=True)
def parse_document_url_task(self, url: str, upload_url_id: str, notebook_id: str, user_id: int, kb_item_id: str = None):
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
                content_type="document",
                parsing_status="queueing",
                notes=f"Document URL: {url}",
                tags=[],
                metadata={'url': url, 'upload_url_id': upload_url_id, 'document_only': True}
            )
            logger.info(f"Created KB item {kb_item.id} for document URL: {url}")

        # Update status to parsing
        kb_item.parsing_status = "parsing"
        kb_item.save(update_fields=['parsing_status'])

        # Process the document URL
        from notebooks.processors.url_extractor import URLExtractor
        url_extractor = URLExtractor()

        # Pass kb_item_id to update existing item instead of creating new one
        result = async_to_sync(url_extractor.process_url_document_only)(
            url=url,
            upload_url_id=upload_url_id,
            user_id=user_id,
            notebook_id=notebook_id,
            kb_item_id=str(kb_item.id)
        )

        # Get the file_id from result
        file_id = result.get("file_id")

        if not file_id:
            kb_item.parsing_status = "failed"
            kb_item.save(update_fields=['parsing_status'])
            raise URLProcessingError("URL processing did not return a file_id")

        # Refresh KB item from database
        kb_item.refresh_from_db()

        # Mark as done
        kb_item.parsing_status = "done"
        kb_item.save(update_fields=['parsing_status'])

        logger.info(f"Successfully parsed document URL to KB item {file_id}")

        # Chain RagFlow upload task
        upload_to_ragflow_task.apply_async(args=[str(file_id)])

        return {
            "success": True,
            "file_id": file_id,
            "upload_url_id": upload_url_id
        }

    except Exception as e:
        logger.exception(f"Failed to parse document URL {url}: {e}")

        # Mark KB item as failed if it exists
        try:
            if 'kb_item' in locals():
                kb_item.parsing_status = "failed"
                kb_item.metadata = kb_item.metadata or {}
                kb_item.metadata['error'] = str(e)
                kb_item.save(update_fields=['parsing_status', 'metadata'])
        except Exception:
            pass

        return {
            "success": False,
            "error": str(e)
        }


def _handle_task_completion(kb_item: KnowledgeBaseItem,
                          batch_item_id: str = None, batch_job_id: str = None) -> Dict[str, Any]:
    """Handle common task completion logic.

    File parsing is now complete - mark as 'done' immediately so frontend can use it.
    Caption generation and other post-processing run independently.
    """
    # Mark parsing as done immediately - file is ready for use
    kb_item.parsing_status = "done"
    kb_item.save(update_fields=["parsing_status", "updated_at"])

    logger.info(f"KB item {kb_item.id} marked as 'done' - ready for frontend use")

    # Chain RagFlow upload task to ensure content is fully saved
    try:
        upload_to_ragflow_task.delay(str(kb_item.id))
        logger.info(f"Chained RagFlow upload task for KB item {kb_item.id}")
    except Exception as e:
        logger.error(f"Failed to chain RagFlow upload task for KB item {kb_item.id}: {e}")
        # Don't fail the main task if chaining fails

    # Schedule caption generation after all processing is complete
    try:
        from .models import KnowledgeBaseImage

        # Count images in database
        image_count = KnowledgeBaseImage.objects.filter(knowledge_base_item=kb_item).count()

        if image_count > 0:
            kb_item.captioning_status = "pending"
            kb_item.save(update_fields=["captioning_status", "updated_at"])

            generate_image_captions_task.delay(str(kb_item.id))
            logger.info(f"Scheduled caption generation for KB item {kb_item.id} with {image_count} images")
        else:
            kb_item.captioning_status = "not_required"
            kb_item.save(update_fields=["captioning_status", "updated_at"])
            logger.info(f"No images for KB item {kb_item.id} - captioning not required")
    except Exception as caption_error:
        logger.warning(f"Failed to schedule caption generation for KB item {kb_item.id}: {caption_error}")

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
        kb_item.captioning_status = "in_progress"
        kb_item.save(update_fields=["captioning_status", "updated_at"])

        # Import caption generator utility lazily
        from .utils.image_processing.caption_generator import populate_image_captions_for_kb_item

        # Generate captions
        result = populate_image_captions_for_kb_item(kb_item)

        if result.get('success'):
            logger.info(f"Successfully generated captions for KB item {kb_item_id}")
            kb_item.captioning_status = "completed"
            kb_item.save(update_fields=["captioning_status", "updated_at"])
            return {"success": True, "captions_generated": result.get('captions_count', 0)}
        else:
            logger.warning(f"Failed to generate captions for KB item {kb_item_id}: {result.get('error')}")
            kb_item.captioning_status = "failed"
            # Keep error in metadata for observability
            kb_item.metadata = kb_item.metadata or {}
            kb_item.metadata['caption_error'] = result.get('error')
            kb_item.save(update_fields=["captioning_status", "metadata", "updated_at"])
            return {"success": False, "error": result.get('error')}

    except Exception as e:
        logger.error(f"Error generating captions for KB item {kb_item_id}: {e}")
        if kb_item:
            kb_item.captioning_status = "failed"
            kb_item.metadata = kb_item.metadata or {}
            kb_item.metadata['caption_error'] = str(e)
            kb_item.save(update_fields=["captioning_status", "metadata", "updated_at"])
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


@shared_task(bind=True)
def check_ragflow_status_task(self, kb_item_id: str, max_retries: int = 10):
    """
    Check RagFlow document processing status and update accordingly.

    Args:
        kb_item_id: ID of the KnowledgeBaseItem to check
        max_retries: Maximum number of retry attempts

    Returns:
        dict: Status check result
    """
    try:
        # Get the KB item
        kb_item = KnowledgeBaseItem.objects.select_related('notebook').get(id=kb_item_id)

        if not kb_item.ragflow_document_id:
            logger.warning(f"KB item {kb_item_id} has no RagFlow document ID")
            return {"success": False, "error": "No RagFlow document ID"}

        if not kb_item.notebook.ragflow_dataset_id:
            logger.warning(f"KB item {kb_item_id} has no dataset ID")
            return {"success": False, "error": "No RagFlow dataset ID"}

        from infrastructure.ragflow.client import get_ragflow_client
        ragflow_client = get_ragflow_client()

        # Get document status from RagFlow
        doc_status = ragflow_client.get_document_status(
            dataset_id=kb_item.notebook.ragflow_dataset_id,
            document_id=kb_item.ragflow_document_id
        )

        if not doc_status:
            logger.warning(f"Could not get status for RagFlow document {kb_item.ragflow_document_id}")
            # Retry if we haven't exceeded max retries
            if self.request.retries < max_retries:
                logger.info(f"Retrying status check for KB item {kb_item_id} (attempt {self.request.retries + 1})")
                raise self.retry(countdown=30, max_retries=max_retries)
            else:
                kb_item.mark_ragflow_failed("Could not get status from RagFlow")
                return {"success": False, "error": "Could not get status from RagFlow"}

        # Parse the status from RagFlow
        ragflow_status = doc_status.get('status', 'unknown').upper()
        logger.info(f"RagFlow document {kb_item.ragflow_document_id} status: {ragflow_status}")

        # Update KB item based on RagFlow status
        if ragflow_status == 'DONE':
            kb_item.mark_ragflow_completed(kb_item.ragflow_document_id)
            logger.info(f"KB item {kb_item_id} RagFlow processing completed successfully")
            return {"success": True, "status": "completed"}

        elif ragflow_status == 'FAIL':
            kb_item.mark_ragflow_failed("RagFlow processing failed")
            logger.error(f"KB item {kb_item_id} RagFlow processing failed")
            return {"success": False, "status": "failed"}

        elif ragflow_status in ['RUNNING', 'UNSTART']:
            # Still processing, schedule another check
            if self.request.retries < max_retries:
                logger.info(f"RagFlow document still processing, scheduling next check for KB item {kb_item_id}")
                raise self.retry(countdown=30, max_retries=max_retries)
            else:
                # Max retries reached, mark as failed
                kb_item.mark_ragflow_failed("RagFlow processing timeout")
                logger.error(f"KB item {kb_item_id} RagFlow processing timeout after {max_retries} checks")
                return {"success": False, "error": "Processing timeout"}

        elif ragflow_status == 'CANCEL':
            kb_item.mark_ragflow_failed("RagFlow processing was cancelled")
            logger.warning(f"KB item {kb_item_id} RagFlow processing was cancelled")
            return {"success": False, "status": "cancelled"}

        else:
            # Unknown status, retry
            if self.request.retries < max_retries:
                logger.warning(f"Unknown RagFlow status '{ragflow_status}' for KB item {kb_item_id}, retrying")
                raise self.retry(countdown=30, max_retries=max_retries)
            else:
                kb_item.mark_ragflow_failed(f"Unknown RagFlow status: {ragflow_status}")
                return {"success": False, "error": f"Unknown status: {ragflow_status}"}

    except KnowledgeBaseItem.DoesNotExist:
        error_msg = f"KB item {kb_item_id} not found"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    except Exception as e:
        logger.error(f"Error checking RagFlow status for KB item {kb_item_id}: {e}")

        # Retry on unexpected errors
        if self.request.retries < max_retries:
            logger.info(f"Retrying status check due to error for KB item {kb_item_id}")
            raise self.retry(countdown=30, max_retries=max_retries)
        else:
            # Mark as failed after max retries
            try:
                kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id)
                kb_item.mark_ragflow_failed(f"Status check error: {e}")
            except:
                pass
            return {"success": False, "error": str(e)}


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
