"""
MinIO-based upload processor for immediate file processing.
Handles immediate processing of uploaded files with MinIO object storage only.
"""

import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from django.core.exceptions import ValidationError

# Django imports for file handling
from django.core.files.uploadedfile import UploadedFile as UploadFile

try:
    from ..utils.helpers import ContentIndexingService, clean_title
    from ..utils.helpers import config as settings
    from ..utils.storage import FileStorageService
    from ..utils.validators import FileValidator
except ImportError:
    # Fallback classes to prevent import errors
    FileStorageService = None
    ContentIndexingService = None
    FileValidator = None
    settings = None
    clean_title = None

# Import new ingestion module
from ..ingestion import IngestionOrchestrator


class UploadProcessor:
    """Handles immediate processing of uploaded files with MinIO storage only."""

    def __init__(self, mineru_base_url: str = None):
        self.service_name = "upload_processor"
        self.logger = logging.getLogger(f"{__name__}.upload_processor")

        # Initialize services with fallbacks
        self.file_storage = FileStorageService() if FileStorageService else None
        self.content_indexing = (
            ContentIndexingService() if ContentIndexingService else None
        )
        self.validator = FileValidator() if FileValidator else None

        # MinerU API configuration - use Django settings if available
        if mineru_base_url is None:
            try:
                from django.conf import settings as django_settings

                mineru_base_url = getattr(django_settings, "MINERU_BASE_URL", None)
            except ImportError:
                mineru_base_url = None

        # Fallback to default if still None
        if mineru_base_url is None:
            mineru_base_url = "http://localhost:8008"

        # Normalize: ensure URL has a scheme to avoid requests errors like 'no scheme supplied'
        if not str(mineru_base_url).lower().startswith(("http://", "https://")):
            mineru_base_url = f"http://{mineru_base_url}"

        self.mineru_base_url = mineru_base_url.rstrip("/")

        # Initialize new ingestion orchestrator with transcription configuration
        transcription_provider = os.getenv("TRANSCRIPTION_PROVIDER", "whisperx")

        # WhisperX configuration
        whisperx_model_name = os.getenv("WHISPERX_MODEL_NAME", "large-v2")
        whisperx_device = os.getenv("WHISPERX_DEVICE", "auto")
        whisperx_compute_type = os.getenv("WHISPERX_COMPUTE_TYPE")  # None means auto
        whisperx_batch_size = int(os.getenv("WHISPERX_BATCH_SIZE", "16"))
        whisperx_language = os.getenv("WHISPERX_LANGUAGE")  # None means auto-detect
        whisperx_use_vad = os.getenv("WHISPERX_VAD", "0") == "1"
        whisperx_cache_dir = os.getenv("WHISPERX_CACHE_DIR")  # None means default

        # Xinference configuration (fallback)
        xinference_url = os.getenv("XINFERENCE_URL", "http://localhost:9997")
        xinference_model_uid = os.getenv(
            "XINFERENCE_WHISPER_MODEL_UID", "Bella-whisper-large-v3-zh"
        )

        self.ingestion_orchestrator = IngestionOrchestrator(
            mineru_base_url=self.mineru_base_url,
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
            logger=self.logger,
        )

        # Track upload statuses in memory (in production, use Redis or database)
        self._upload_statuses = {}

    def log_operation(self, operation: str, details: str = "", level: str = "info"):
        """Log service operations with consistent formatting."""
        message = f"[{self.service_name}] {operation}"
        if details:
            message += f": {details}"

        getattr(self.logger, level)(message)

    def get_upload_status(
        self, upload_file_id: str, user_pk: int = None
    ) -> dict[str, Any] | None:
        """Get the current status of an upload by upload_file_id."""
        try:
            # Check in-memory status first
            if upload_file_id in self._upload_statuses:
                return self._upload_statuses[upload_file_id]

            # Check if file is already processed and stored
            if self.file_storage:
                file_metadata = self.file_storage.get_file_by_upload_id(
                    upload_file_id, user_pk
                )
                if file_metadata:
                    status = {
                        "upload_file_id": upload_file_id,
                        "file_id": file_metadata.get("file_id"),
                        "status": "completed",
                        "parsing_status": "completed",
                        "filename": file_metadata.get("original_filename"),
                        "metadata": file_metadata,
                    }
                    # Cache for future requests
                    self._upload_statuses[upload_file_id] = status
                    return status

            return None
        except Exception as e:
            self.log_operation("get_upload_status_error", str(e), "error")
            return None

    def delete_upload(self, upload_file_id: str, user_pk: int) -> bool:
        """Delete an upload and its associated files."""
        try:
            # Remove from in-memory tracking
            if upload_file_id in self._upload_statuses:
                del self._upload_statuses[upload_file_id]

            # Delete from storage
            if self.file_storage:
                return self.file_storage.delete_file_by_upload_id(
                    upload_file_id, user_pk
                )
            return False
        except Exception as e:
            self.log_operation("delete_upload_error", str(e), "error")
            return False

    def _update_upload_status(self, upload_file_id: str, status: str, **kwargs):
        """Update the status of an upload."""
        if upload_file_id:
            current_status = self._upload_statuses.get(upload_file_id, {})

            # Convert UUID objects to strings for JSON serialization
            json_safe_kwargs = {}
            for key, value in kwargs.items():
                if hasattr(value, "__str__") and hasattr(value, "hex"):  # UUID check
                    json_safe_kwargs[key] = str(value)
                else:
                    json_safe_kwargs[key] = value

            current_status.update(
                {
                    "upload_file_id": upload_file_id,
                    "status": status,
                    "parsing_status": status,
                    "updated_at": datetime.now(UTC).isoformat(),
                    **json_safe_kwargs,
                }
            )
            self._upload_statuses[upload_file_id] = current_status

    async def process_upload(
        self,
        file: UploadFile,
        upload_file_id: str | None = None,
        user_pk: int | None = None,
        notebook_id: int | None = None,
        kb_item_id: str | None = None,
        upload_to_ragflow: bool = False,
    ) -> dict[str, Any]:
        """Main entry point for immediate file processing with MinIO storage."""
        temp_path = None
        try:
            # Initialize status tracking
            if upload_file_id:
                self._update_upload_status(
                    upload_file_id, "pending", filename=file.name
                )

            # Validate file
            validation = self.validator.validate_file(file)
            if not validation["valid"]:
                if upload_file_id:
                    self._update_upload_status(
                        upload_file_id,
                        "error",
                        error=f"File validation failed: {'; '.join(validation['errors'])}",
                    )
                raise ValidationError(
                    f"File validation failed: {'; '.join(validation['errors'])}"
                )

            # Update status to processing
            if upload_file_id:
                self._update_upload_status(
                    upload_file_id, "processing", filename=file.name
                )

            # Save file temporarily
            temp_path = self._save_uploaded_file(file)

            # Additional content validation
            content_validation = self.validator.validate_file_content(temp_path)
            if not content_validation["valid"]:
                if upload_file_id:
                    self._update_upload_status(
                        upload_file_id,
                        "error",
                        error=f"File content validation failed: {'; '.join(content_validation['errors'])}",
                    )
                raise ValidationError(
                    f"File content validation failed: {'; '.join(content_validation['errors'])}"
                )

            # Get file size
            file_size = os.path.getsize(temp_path)

            # Clean the original filename using clean_title function
            file_path = Path(file.name)
            base_name = file_path.stem
            extension = file_path.suffix
            clean_base_name = clean_title(base_name)
            clean_filename = f"{clean_base_name}{extension}"

            # Prepare file metadata with cleaned file information
            file_metadata = {
                "filename": clean_filename,
                "original_filename": clean_filename,  # Store cleaned filename
                "file_extension": validation["file_extension"],
                "content_type": validation["content_type"],
                "file_size": file_size,
                "upload_file_id": upload_file_id,
                "upload_timestamp": datetime.now(UTC).isoformat(),
                "parsing_status": "processing",
                "storage_backend": "minio",  # Mark as MinIO storage
            }

            # Add source URL to metadata if available (for duplicate detection)
            if hasattr(file, "_source_url") and file._source_url:
                file_metadata["source_url"] = file._source_url

            # Store result with user isolation using MinIO storage
            if user_pk is None:
                raise ValueError("user_pk is required for file storage")
            if notebook_id is None:
                raise ValueError("notebook_id is required for file storage")

            # Use new ingestion orchestrator for processing
            ingestion_result = await self.ingestion_orchestrator.ingest_file(
                file_path=temp_path,
                user_pk=user_pk,
                notebook_id=notebook_id,
                metadata=file_metadata,
                kb_item_id=kb_item_id,
            )

            file_id = ingestion_result.file_id

            # Run synchronous content indexing in executor
            if self.content_indexing:
                from asgiref.sync import sync_to_async

                index_content_sync = sync_to_async(
                    self.content_indexing.index_content, thread_sensitive=False
                )
                await index_content_sync(
                    file_id=file_id,
                    content=ingestion_result.content_preview,
                    metadata=file_metadata,
                    processing_stage="immediate",
                )

            # Handle RagFlow upload if requested
            if upload_to_ragflow:
                await self._handle_ragflow_upload_async(
                    file_id, file_metadata, notebook_id
                )

            # Update final status
            if upload_file_id:
                self._update_upload_status(
                    upload_file_id,
                    "completed",
                    file_id=file_id,
                    filename=file.name,
                    file_size=file_size,
                    metadata=file_metadata,
                    storage_backend="minio",
                )

            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

            return {
                "file_id": file_id,
                "status": ingestion_result.status,
                "parsing_status": ingestion_result.parsing_status,
                "content_preview": ingestion_result.content_preview,
                "processing_type": "immediate",
                "features_available": ingestion_result.features_available,
                "metadata": ingestion_result.metadata,
                "filename": file.name,
                "file_size": file_size,
                "upload_file_id": upload_file_id,
                "storage_backend": "minio",
            }

        except ValidationError:
            # Clean up and re-raise validation errors
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
        except Exception as e:
            # Handle unexpected errors
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

            if upload_file_id:
                self._update_upload_status(upload_file_id, "error", error=str(e))

            self.log_operation("process_upload_error", str(e), "error")
            raise Exception(f"Processing failed: {str(e)}")

    def _save_uploaded_file(self, file: UploadFile) -> str:
        """Save uploaded file to temporary directory."""
        try:
            suffix = Path(file.name).suffix.lower()
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix, prefix="deepsight_minio_"
            ) as tmp_file:
                content = file.read()

                # Reset file pointer for potential future reads
                file.seek(0)

                # Additional size check
                if len(content) > self.validator.max_file_size:
                    os.unlink(tmp_file.name)
                    raise ValueError(
                        f"File size {len(content) / (1024 * 1024):.1f}MB exceeds maximum allowed size"
                    )

                tmp_file.write(content)
                tmp_file.flush()

                self.log_operation("save_file", f"Saved {file.name} to {tmp_file.name}")
                return tmp_file.name

        except Exception as e:
            self.log_operation(
                "save_file_error", f"File: {file.name}, error: {str(e)}", "error"
            )
            raise

    async def _handle_ragflow_upload_async(
        self,
        file_id: str,
        file_metadata: dict[str, Any],
        notebook_id: int | None = None,
    ) -> None:
        """Handle RagFlow upload for immediate processing."""
        try:
            # Import models inside method to avoid circular imports
            from asgiref.sync import sync_to_async

            from ..models import KnowledgeBaseItem

            # Get the KB item to access content and dataset ID
            get_kb_item_sync = sync_to_async(
                KnowledgeBaseItem.objects.get, thread_sensitive=False
            )
            kb_item = await get_kb_item_sync(id=file_id)

            # Check if notebook has RagFlow dataset ID
            dataset_id = kb_item.notebook.ragflow_dataset_id
            if not dataset_id:
                self.log_operation(
                    "ragflow_upload_skipped",
                    f"No RagFlow dataset ID for notebook {kb_item.notebook.id}",
                    "warning",
                )
                return

            # Check if content is available
            if not kb_item.content:
                self.log_operation(
                    "ragflow_upload_skipped",
                    f"No content available for KB item {file_id}",
                    "warning",
                )
                return

            # Upload to RagFlow
            from infrastructure.ragflow.service import get_ragflow_service

            ragflow_service_sync = sync_to_async(
                get_ragflow_service, thread_sensitive=False
            )
            ragflow_service = await ragflow_service_sync()

            # Prepare display name from metadata
            display_name = (
                file_metadata.get("original_filename") or kb_item.title or "document.md"
            )

            # Use upload_document_text for text content
            upload_document_sync = sync_to_async(
                ragflow_service.upload_document_text, thread_sensitive=False
            )
            documents = await upload_document_sync(
                dataset_id=dataset_id,
                content=kb_item.content,
                display_name=display_name,
            )

            if documents and len(documents) > 0:
                # Store RagFlow document ID in KB item model field
                kb_item.ragflow_document_id = documents[0].id

                save_kb_item_sync = sync_to_async(kb_item.save, thread_sensitive=False)
                await save_kb_item_sync(update_fields=["ragflow_document_id"])

                self.log_operation(
                    "ragflow_upload_success",
                    f"Uploaded KB item {file_id} to RagFlow: {documents[0].id}",
                )

                # Trigger dataset update to refresh embeddings and settings
                try:
                    update_dataset_sync = sync_to_async(
                        ragflow_service.update_dataset, thread_sensitive=False
                    )
                    await update_dataset_sync(dataset_id)
                    self.log_operation(
                        "ragflow_dataset_update_success",
                        f"Updated RagFlow dataset {dataset_id} after file upload",
                    )
                except Exception as update_e:
                    # Log error but don't fail the entire upload process
                    self.log_operation(
                        "ragflow_dataset_update_error",
                        f"Failed to update dataset {dataset_id}: {update_e}",
                        "warning",
                    )
            else:
                self.log_operation(
                    "ragflow_upload_failed",
                    f"Failed to upload KB item {file_id} to RagFlow - no document ID returned",
                    "error",
                )

        except Exception as e:
            self.log_operation(
                "ragflow_upload_error",
                f"Error uploading KB item {file_id} to RagFlow: {e}",
                "error",
            )


# Global singleton instance
upload_processor = UploadProcessor()
