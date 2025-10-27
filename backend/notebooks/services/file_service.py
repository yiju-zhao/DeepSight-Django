"""
File Service - Handle file processing business logic following Django patterns.
"""

import logging
from uuid import uuid4

from core.services import NotebookBaseService
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import status

from ..models import BatchJob, BatchJobItem, KnowledgeBaseItem

logger = logging.getLogger(__name__)


class FileService(NotebookBaseService):
    """Handle file processing business logic following Django patterns."""

    def __init__(self):
        super().__init__()

    @transaction.atomic
    def handle_single_file_upload(
        self, file_obj, upload_id: str, notebook, user
    ) -> dict:
        """
        Process single file upload with proper validation and error handling.

        Args:
            file_obj: Django file object
            upload_id: Unique upload identifier
            notebook: Notebook instance
            user: User instance

        Returns:
            Dict with upload result and status
        """
        # Validate notebook access
        self.validate_notebook_access(notebook, user)
        kb_item = None
        try:
            # Step 1: Create KnowledgeBaseItem immediately in separate transaction
            with transaction.atomic():
                # Create KnowledgeBaseItem with parsing_status="queueing" directly in notebook
                kb_item = KnowledgeBaseItem(
                    notebook=notebook,
                    title=file_obj.name,
                    content_type="document",
                    parsing_status="queueing",
                    notes=f"Processing {file_obj.name}",
                    tags=[],  # Explicitly set empty list
                    file_metadata={},  # Explicitly set empty dict
                )
                # Set defaults explicitly to avoid validation issues
                if not hasattr(kb_item, "tags") or kb_item.tags is None:
                    kb_item.tags = []
                if (
                    not hasattr(kb_item, "file_metadata")
                    or kb_item.file_metadata is None
                ):
                    kb_item.file_metadata = {}
                kb_item.save()

            # Step 2: Queue file processing to Celery (async)
            try:
                # Read file data for Celery task
                file_data = file_obj.read()
                file_obj.seek(0)  # Reset file pointer

                # Queue the processing task
                from ..tasks import process_file_upload_task

                process_file_upload_task.delay(
                    file_data=file_data,
                    filename=file_obj.name,
                    notebook_id=notebook.id,
                    user_id=user.pk,
                    upload_file_id=upload_id,
                    kb_item_id=str(kb_item.id),  # Pass our pre-created kb_item ID
                )

                self.log_notebook_operation(
                    "file_upload_queued",
                    str(notebook.id),
                    user.id,
                    kb_item_id=str(kb_item.id),
                    filename=file_obj.name,
                )

            except Exception as queue_error:
                # Update parsing status to done if queueing fails (parsing isn't the issue)
                kb_item.parsing_status = "done"
                kb_item.save(update_fields=["parsing_status"])
                self.logger.error(
                    f"Failed to queue processing for {file_obj.name}: {queue_error}"
                )
                # Don't re-raise - return success so frontend shows the item with error status

            return {
                "success": True,
                "file_id": kb_item.id,
                "knowledge_item_id": kb_item.id,
                "upload_id": upload_id,
                "status_code": status.HTTP_201_CREATED,
                "message": "File uploaded and processing started",
                "refresh_source_list": True,  # Trigger frontend refresh when processing complete
            }

        except Exception as e:
            self.logger.exception(f"Single file upload failed for {file_obj.name}: {e}")
            raise ValidationError(f"File upload failed: {str(e)}")

    @transaction.atomic
    def handle_batch_file_upload(self, files: list, notebook, user) -> dict:
        """
        Process batch file upload with proper transaction management.

        Args:
            files: List of Django file objects
            notebook: Notebook instance
            user: User instance

        Returns:
            Dict with batch job information
        """
        # Validate notebook access
        self.validate_notebook_access(notebook, user)
        try:
            # Create batch job
            batch_job = BatchJob.objects.create(
                notebook=notebook,
                job_type="file_upload",
                total_items=len(files),
                status="processing",
            )

            # Process each file and create source/knowledge base items immediately
            for file_obj in files:
                upload_id = uuid4().hex
                data = file_obj.read()
                file_obj.seek(0)

                # Create KnowledgeBaseItem with processing_status="processing" directly in notebook
                kb_item = KnowledgeBaseItem.objects.create(
                    notebook=notebook,
                    title=file_obj.name,
                    content_type="document",
                    parsing_status="parsing",
                    tags=[],  # Explicitly set empty list
                    file_metadata={},  # Explicitly set empty dict
                )

                batch_item = BatchJobItem.objects.create(
                    batch_job=batch_job,
                    item_data={
                        "filename": file_obj.name,
                        "size": len(data),
                        "kb_item_id": str(kb_item.id),
                    },
                    upload_id=upload_id,
                    status="pending",
                )

                # Enqueue Celery task for background processing
                from ..tasks import process_file_upload_task

                process_file_upload_task.delay(
                    file_data=data,
                    filename=file_obj.name,
                    notebook_id=notebook.id,
                    user_id=user.pk,
                    upload_file_id=upload_id,
                    batch_job_id=batch_job.id,
                    batch_item_id=batch_item.id,
                    kb_item_id=str(kb_item.id),  # Pass the kb_item_id to the task
                )

            self.log_notebook_operation(
                "batch_file_upload_started",
                str(notebook.id),
                user.id,
                batch_job_id=str(batch_job.id),
                total_files=len(files),
            )

            return {
                "success": True,
                "batch_job_id": batch_job.id,
                "total_items": len(files),
                "message": f"Batch upload started for {len(files)} files",
                "status_code": status.HTTP_202_ACCEPTED,
            }

        except Exception as e:
            self.logger.exception(f"Batch file upload failed: {e}")
            raise ValidationError(f"Batch file upload failed: {str(e)}")

    def validate_file_upload(self, serializer) -> tuple:
        """
        Validate file upload data from serializer.

        Args:
            serializer: DRF serializer instance

        Returns:
            Tuple of (file_obj, upload_id)
        """
        serializer.is_valid(raise_exception=True)
        file_obj = serializer.validated_data["file"]
        upload_id = serializer.validated_data.get("upload_file_id") or uuid4().hex
        return file_obj, upload_id

    def validate_batch_file_upload(self, serializer) -> list | None:
        """
        Validate batch file upload data from serializer.

        Args:
            serializer: DRF serializer instance

        Returns:
            List of file objects or None
        """
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        if "files" in validated_data:
            return validated_data["files"]
        return None
