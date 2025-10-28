"""
RAGFlow integration tasks for notebooks app.

This module contains tasks for uploading documents to RAGFlow and monitoring
their processing status.
"""

import logging

from asgiref.sync import async_to_sync
from celery import shared_task
from celery.exceptions import Retry
from core.utils.sse import publish_notebook_event

from ..constants import RagflowDocStatus
from ..models import KnowledgeBaseItem

logger = logging.getLogger(__name__)


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
        kb_item = KnowledgeBaseItem.objects.select_related("notebook").get(
            id=kb_item_id
        )

        # Mark as uploading to RagFlow
        kb_item.mark_ragflow_uploading()

        # Check if we have a processed file in MinIO to upload
        if not kb_item.file_object_key:
            logger.warning(
                f"KB item {kb_item.id} has no processed file to upload to RagFlow"
            )
            kb_item.mark_ragflow_failed("No processed file available for upload")
            return {"success": False, "error": "No processed file available for upload"}

        from infrastructure.ragflow.client import get_ragflow_client
        from infrastructure.storage.adapters import get_storage_adapter

        ragflow_client = get_ragflow_client()
        storage_adapter = get_storage_adapter()

        # Upload to RagFlow - we need the notebook's RagFlow dataset ID
        if not kb_item.notebook.ragflow_dataset_id:
            logger.warning(
                f"No RagFlow dataset ID found for notebook {kb_item.notebook.id}"
            )
            kb_item.mark_ragflow_failed("No RagFlow dataset ID configured")
            return {"success": False, "error": "No RagFlow dataset ID configured"}

        # Get the processed markdown file content from MinIO using file_object_key
        try:
            file_content = storage_adapter.get_file_content(
                kb_item.file_object_key, str(kb_item.notebook.user_id)
            )

            # Extract filename from file_object_key path (e.g., "user_id/kb/kb_item_id/filename.md")
            # The file_object_key already contains the proper .md filename
            filename = kb_item.file_object_key.split("/")[-1]

            # Ensure it has .md extension (safety check)
            if not filename.endswith(".md"):
                filename = filename + ".md"

        except Exception as storage_error:
            error_msg = (
                f"Failed to retrieve processed file from storage: {storage_error}"
            )
            logger.error(error_msg)
            kb_item.mark_ragflow_failed(error_msg)
            return {"success": False, "error": error_msg}

        logger.info(
            f"Uploading file '{filename}' to RagFlow dataset {kb_item.notebook.ragflow_dataset_id}"
        )
        upload_result = ragflow_client.upload_document_file(
            dataset_id=kb_item.notebook.ragflow_dataset_id,
            file_content=file_content,
            filename=filename,
        )
        logger.info(f"RagFlow upload result: {upload_result}")

        if upload_result and upload_result.get("id"):
            document_id = upload_result.get("id")
            logger.info(
                f"Successfully uploaded processed file for KB item {kb_item.id} to RagFlow: {document_id}"
            )

            # Store the RagFlow document ID and mark as parsing atomically
            try:
                kb_item.ragflow_document_id = document_id
                kb_item.ragflow_processing_status = RagflowDocStatus.PARSING
                kb_item.save(
                    update_fields=[
                        "ragflow_document_id",
                        "ragflow_processing_status",
                        "updated_at",
                    ]
                )
                logger.info(
                    f"Saved RagFlow document ID {document_id} to KB item {kb_item.id} with status 'parsing'"
                )

                # Verify the save was successful by reloading from database
                kb_item.refresh_from_db()
                if kb_item.ragflow_document_id == document_id:
                    logger.info(
                        f"Verified: RagFlow document ID {document_id} successfully saved to database"
                    )
                else:
                    logger.warning(
                        f"Database verification failed: expected {document_id}, got {kb_item.ragflow_document_id}"
                    )

            except Exception as save_error:
                logger.error(
                    f"Failed to save RagFlow document ID {document_id} to KB item {kb_item.id}: {save_error}"
                )
                # Still continue with parsing trigger attempt
                kb_item.ragflow_processing_status = (
                    "parsing"  # At least update status in memory
                )

            # Trigger dataset update to refresh embeddings and settings
            try:
                ragflow_client.update_dataset(kb_item.notebook.ragflow_dataset_id)
                logger.info(
                    f"Successfully updated RagFlow dataset {kb_item.notebook.ragflow_dataset_id} after file upload"
                )
            except Exception as update_error:
                # Log error but don't fail the entire upload process
                logger.warning(
                    f"Failed to update dataset {kb_item.notebook.ragflow_dataset_id}: {update_error}"
                )

            # Trigger document parsing after successful upload
            try:
                parse_result = ragflow_client.parse_documents(
                    dataset_id=kb_item.notebook.ragflow_dataset_id,
                    document_ids=[document_id],
                )

                if parse_result:
                    logger.info(
                        f"Successfully triggered parsing for RagFlow document {document_id}"
                    )
                    # Mark as parsing in progress
                    kb_item.mark_ragflow_parsing()

                    # Schedule status checking task with unique task_id to prevent duplicates
                    try:
                        task_id = f"ragflow-status-{kb_item.id}"
                        check_ragflow_status_task.apply_async(
                            args=[str(kb_item.id)], task_id=task_id
                        )
                    except Exception as schedule_error:
                        logger.warning(
                            f"Failed to schedule status check for {document_id}: {schedule_error}"
                        )
                else:
                    logger.warning(
                        f"Failed to trigger parsing for RagFlow document {document_id}"
                    )
                    kb_item.mark_ragflow_failed("Failed to trigger parsing")

            except Exception as parse_error:
                logger.error(
                    f"Error triggering parsing for RagFlow document {document_id}: {parse_error}"
                )
                kb_item.mark_ragflow_failed(f"Parsing trigger error: {parse_error}")
                # Don't fail the main task if parsing trigger fails

            return {
                "success": True,
                "ragflow_document_id": document_id,
                "parsing_triggered": parse_result,
            }
        else:
            logger.warning(
                f"Failed to upload processed file for KB item {kb_item.id} to RagFlow"
            )
            kb_item.mark_ragflow_failed("Upload failed - no document ID returned")
            return {
                "success": False,
                "error": "Upload failed - no document ID returned",
            }

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


@shared_task(bind=True, acks_late=False, reject_on_worker_lost=False)
def check_ragflow_status_task(self, kb_item_id: str):
    """
    Poll RagFlow document processing status using linear polling with a finite timeout.

    Args:
        kb_item_id: ID of the KnowledgeBaseItem to check

    Returns:
        dict: Status check result
    """
    # Define linear polling policy
    POLLING_INTERVAL = 15  # seconds
    MAX_POLLING_RETRIES = 120  # Results in a 30-minute timeout (120 * 15s)

    try:
        kb_item = KnowledgeBaseItem.objects.select_related("notebook").get(
            id=kb_item_id
        )

        if not kb_item.ragflow_document_id or not kb_item.notebook.ragflow_dataset_id:
            logger.warning(
                f"KB item {kb_item_id} is missing RagFlow document/dataset ID. Aborting task."
            )
            return {"success": False, "error": "Missing RagFlow document or dataset ID"}

        from infrastructure.ragflow.client import get_ragflow_client

        ragflow_client = get_ragflow_client()

        doc_status = ragflow_client.get_document_status(
            dataset_id=kb_item.notebook.ragflow_dataset_id,
            document_id=kb_item.ragflow_document_id,
        )

        ragflow_status = (
            doc_status.get("status", "unknown").upper() if doc_status else "UNKNOWN"
        )
        logger.info(
            f"RagFlow document {kb_item.ragflow_document_id} status: {ragflow_status}"
        )

        if ragflow_status == "DONE":
            kb_item.mark_ragflow_completed(kb_item.ragflow_document_id)
            logger.info(
                f"KB item {kb_item_id} RagFlow processing completed successfully."
            )
            try:
                # Publish final SUCCESS for 'source' on RagFlow completion
                async_to_sync(publish_notebook_event)(
                    notebook_id=str(kb_item.notebook.id),
                    entity="source",
                    entity_id=str(kb_item.id),
                    status="SUCCESS",
                    payload={
                        "file_id": str(kb_item.id),
                        "title": kb_item.title,
                    },
                )
            except Exception:
                logger.warning("Failed to publish SSE event on RagFlow completion", exc_info=True)
            return {"success": True, "status": "completed"}

        if ragflow_status in ["FAIL", "CANCEL"]:
            error_message = f"RagFlow processing ended with status: {ragflow_status}"
            kb_item.mark_ragflow_failed(error_message)
            logger.error(f"KB item {kb_item_id}: {error_message}")
            try:
                async_to_sync(publish_notebook_event)(
                    notebook_id=str(kb_item.notebook.id),
                    entity="source",
                    entity_id=str(kb_item.id),
                    status="FAILURE",
                    payload={"error": error_message},
                )
            except Exception:
                logger.warning("Failed to publish SSE event on RagFlow failure", exc_info=True)
            return {"success": False, "status": ragflow_status.lower()}

        # Still processing, retry with a fixed interval.
        logger.info(
            f"RagFlow still processing (status: {ragflow_status}). "
            f"Retrying in {POLLING_INTERVAL}s... "
            f"(Attempt {self.request.retries + 1}/{MAX_POLLING_RETRIES})"
        )
        self.retry(countdown=POLLING_INTERVAL, max_retries=MAX_POLLING_RETRIES)

    except self.MaxRetriesExceededError:
        error_msg = f"Polling timed out after {MAX_POLLING_RETRIES} retries (30 minutes). RagFlow processing took too long."
        logger.error(f"KB item {kb_item_id}: {error_msg}")
        try:
            # Final attempt to get the item and mark it as failed.
            kb_item = KnowledgeBaseItem.objects.get(id=kb_item_id)
            kb_item.mark_ragflow_failed(error_msg)
            try:
                async_to_sync(publish_notebook_event)(
                    notebook_id=str(kb_item.notebook.id),
                    entity="source",
                    entity_id=str(kb_item.id),
                    status="FAILURE",
                    payload={"error": error_msg},
                )
            except Exception:
                logger.warning("Failed to publish SSE event on RagFlow timeout", exc_info=True)
        except KnowledgeBaseItem.DoesNotExist:
            logger.error(
                f"KB item {kb_item_id} not found when trying to mark as failed after max retries."
            )

    except KnowledgeBaseItem.DoesNotExist:
        logger.error(
            f"KB item {kb_item_id} not found during status check. Task will not be retried."
        )

    except Retry:
        # Re-raise the Retry exception for Celery to handle.
        raise

    except Exception as e:
        # For other errors (e.g., network), retry using the same linear policy.
        logger.warning(
            f"Unexpected error checking RagFlow status for KB item {kb_item_id}: {e}. "
            f"Retrying... (Attempt {self.request.retries + 1}/{MAX_POLLING_RETRIES})"
        )
        self.retry(countdown=POLLING_INTERVAL, max_retries=MAX_POLLING_RETRIES, exc=e)
