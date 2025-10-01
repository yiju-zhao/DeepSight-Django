"""
MinIO-based upload processor for immediate file processing.
Handles immediate processing of uploaded files with MinIO object storage only.
"""

import os
import sys
import tempfile
import subprocess
import asyncio
import logging
import time
import re
import requests
import json
import base64
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone

# Django imports for file handling
from django.core.files.uploadedfile import UploadedFile as UploadFile
from django.http import Http404
from django.core.exceptions import ValidationError

try:
    from ..utils.storage import FileStorageService
    from ..utils.helpers import ContentIndexingService, config as settings, clean_title
    from ..utils.validators import FileValidator
except ImportError:
    # Fallback classes to prevent import errors
    FileStorageService = None
    ContentIndexingService = None
    FileValidator = None
    settings = None
    clean_title = None

# Import refactored services
from .device_manager import DeviceManager
from .file_type_processors import FileTypeProcessors
from .minio_post_processor import MinIOPostProcessor



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
        
        # Initialize service components
        self.device_manager = DeviceManager(self.logger)
        self.file_type_processors = None  # Lazy initialization
        self.minio_post_processor = None  # Lazy initialization

        # Initialize Xinference settings
        self.xinference_url = os.getenv('XINFERENCE_URL', 'http://localhost:9997')
        self.model_uid = os.getenv('XINFERENCE_WHISPER_MODEL_UID', 'whisper-large-v3-turbo')
        self._xinference_client = None
        self._xinference_model = None
        
        # MinerU API configuration - use Django settings if available
        if mineru_base_url is None:
            try:
                from django.conf import settings as django_settings
                mineru_base_url = getattr(django_settings, 'MINERU_BASE_URL', None)
            except ImportError:
                mineru_base_url = None
        
        # Fallback to default if still None
        if mineru_base_url is None:
            mineru_base_url = "http://localhost:8008"

        # Normalize: ensure URL has a scheme to avoid requests errors like 'no scheme supplied'
        if not str(mineru_base_url).lower().startswith(("http://", "https://")):
            mineru_base_url = f"http://{mineru_base_url}"
            
        self.mineru_base_url = mineru_base_url.rstrip('/')
        self.mineru_parse_endpoint = f"{self.mineru_base_url}/file_parse"
        
        # Track upload statuses in memory (in production, use Redis or database)
        self._upload_statuses = {}
        
    def _init_file_type_processors(self):
        """Lazy initialization of file type processors."""
        if self.file_type_processors is None:
            self.file_type_processors = FileTypeProcessors(
                mineru_base_url=self.mineru_base_url,
                xinference_url=self.xinference_url,
                model_uid=self.model_uid,
                logger=self.logger
            )
        return self.file_type_processors
    
    def _init_minio_post_processor(self):
        """Lazy initialization of MinIO post processor."""
        if self.minio_post_processor is None:
            self.minio_post_processor = MinIOPostProcessor(
                file_storage_service=self.file_storage,
                logger=self.logger
            )
        return self.minio_post_processor

    def log_operation(self, operation: str, details: str = "", level: str = "info"):
        """Log service operations with consistent formatting."""
        message = f"[{self.service_name}] {operation}"
        if details:
            message += f": {details}"

        getattr(self.logger, level)(message)
    
    def check_mineru_health(self) -> bool:
        """Check if MinerU API is available."""
        processor = self._init_file_type_processors()
        return processor.check_mineru_health()

    
    def _get_xinference_client(self):
        """Get or create Xinference client."""
        if not self._xinference_client:
            try:
                from xinference.client import Client
                self._xinference_client = Client(self.xinference_url)
                self.log_operation("xinference_client_connected", f"Connected to Xinference at {self.xinference_url}")
            except Exception as e:
                self.log_operation("xinference_client_error", f"Failed to connect to Xinference: {e}", "error")
                self._xinference_client = False
        return self._xinference_client
    
    def _get_xinference_model(self):
        """Get or create Xinference model."""
        if not self._xinference_model:
            try:
                client = self._get_xinference_client()
                if client:
                    self._xinference_model = client.get_model(self.model_uid)
                    self.log_operation("xinference_model_loaded", f"Loaded Xinference model {self.model_uid}")
                else:
                    self._xinference_model = False
            except Exception as e:
                self.log_operation("xinference_model_error", f"Failed to load Xinference model: {e}", "error")
                self._xinference_model = False
        return self._xinference_model

    def get_upload_status(
        self, upload_file_id: str, user_pk: int = None
    ) -> Optional[Dict[str, Any]]:
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
                return self.file_storage.delete_file_by_upload_id(upload_file_id, user_pk)
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
                if hasattr(value, '__str__') and hasattr(value, 'hex'):  # UUID check
                    json_safe_kwargs[key] = str(value)
                else:
                    json_safe_kwargs[key] = value
            
            current_status.update(
                {
                    "upload_file_id": upload_file_id,
                    "status": status,
                    "parsing_status": status,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    **json_safe_kwargs,
                }
            )
            self._upload_statuses[upload_file_id] = current_status

    async def process_upload(
        self,
        file: UploadFile,
        upload_file_id: Optional[str] = None,
        user_pk: Optional[int] = None,
        notebook_id: Optional[int] = None,
        kb_item_id: Optional[str] = None,
        upload_to_ragflow: bool = False,
    ) -> Dict[str, Any]:
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
                "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                "parsing_status": "processing",
                "storage_backend": "minio",  # Mark as MinIO storage
            }
            
            # Add source URL to metadata if available (for duplicate detection)
            if hasattr(file, '_source_url') and file._source_url:
                file_metadata["source_url"] = file._source_url

            # Process based on file type
            processor = self._init_file_type_processors()
            processing_result = await processor.process_file_by_type(temp_path, file_metadata)

            # Update file metadata with parsing status
            file_metadata["parsing_status"] = "completed"

            # Store result with user isolation using MinIO storage
            if user_pk is None:
                raise ValueError("user_pk is required for file storage")
            if notebook_id is None:
                raise ValueError("notebook_id is required for file storage")

            # For media files, use transcript filename instead of default extracted_content.md
            processing_result_for_storage = processing_result.copy()
            if processing_result.get('transcript_filename'):
                processing_result_for_storage['content_filename'] = processing_result['transcript_filename']

            # Run synchronous file storage in executor
            # Use thread_sensitive=False to run in thread pool where sync ORM calls are allowed
            from asgiref.sync import sync_to_async
            
            if not self.file_storage:
                raise Exception("MinIO file storage service not available")
                
            # Use source URL as identifier for duplicate detection if available, otherwise use filename
            source_identifier = getattr(file, '_source_url', None) or file.name
            
            store_file_sync = sync_to_async(self.file_storage.store_processed_file, thread_sensitive=False)
            file_id = await store_file_sync(
                content=processing_result["content"],
                metadata=file_metadata,
                processing_result=processing_result_for_storage,
                user_id=user_pk,
                notebook_id=notebook_id,
                original_file_path=temp_path,
                source_identifier=source_identifier,  # Use URL for duplicate detection if available
                kb_item_id=kb_item_id,  # Pass the pre-created KB item ID
            )

            # Run synchronous content indexing in executor
            if self.content_indexing:
                index_content_sync = sync_to_async(self.content_indexing.index_content, thread_sensitive=False)
                await index_content_sync(
                    file_id=file_id,
                    content=processing_result["content"],
                    metadata=file_metadata,
                    processing_stage="immediate",
                )
            
            # Handle mineru extraction post-processing if needed
            if 'marker_extraction_result' in processing_result:
                post_processor = self._init_minio_post_processor()
                post_process_sync = sync_to_async(post_processor.post_process_mineru_extraction, thread_sensitive=False)
                await post_process_sync(file_id, processing_result['marker_extraction_result'])

            # Handle RagFlow upload if requested
            if upload_to_ragflow:
                await self._handle_ragflow_upload_async(file_id, file_metadata, notebook_id)

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
                "status": "completed",
                "parsing_status": "completed",
                "content_preview": processing_result["content"][:500] + "..."
                if len(processing_result["content"]) > 500
                else processing_result["content"],
                "processing_type": "immediate",
                "features_available": processing_result.get("features_available", []),
                "metadata": processing_result.get("metadata", {}),
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

    async def _handle_ragflow_upload_async(self, file_id: str, file_metadata: Dict[str, Any], notebook_id: Optional[int] = None) -> None:
        """Handle RagFlow upload for immediate processing."""
        try:
            # Import models inside method to avoid circular imports
            from ..models import KnowledgeBaseItem
            from asgiref.sync import sync_to_async

            # Get the KB item to access content and dataset ID
            get_kb_item_sync = sync_to_async(KnowledgeBaseItem.objects.get, thread_sensitive=False)
            kb_item = await get_kb_item_sync(id=file_id)

            # Check if notebook has RagFlow dataset ID
            dataset_id = kb_item.notebook.ragflow_dataset_id
            if not dataset_id:
                self.log_operation("ragflow_upload_skipped", f"No RagFlow dataset ID for notebook {kb_item.notebook.id}", "warning")
                return

            # Check if content is available
            if not kb_item.content:
                self.log_operation("ragflow_upload_skipped", f"No content available for KB item {file_id}", "warning")
                return

            # Upload to RagFlow
            from infrastructure.ragflow.client import get_ragflow_client
            ragflow_client_sync = sync_to_async(get_ragflow_client, thread_sensitive=False)
            ragflow_client = await ragflow_client_sync()

            # Prepare display name from metadata
            display_name = file_metadata.get("original_filename") or kb_item.title or "document.md"

            upload_document_sync = sync_to_async(ragflow_client.upload_document, thread_sensitive=False)
            upload_result = await upload_document_sync(
                dataset_id=dataset_id,
                content=kb_item.content,
                display_name=display_name
            )

            if upload_result and upload_result.get('id'):
                # Store RagFlow document ID in KB item model field
                kb_item.ragflow_document_id = upload_result.get('id')

                save_kb_item_sync = sync_to_async(kb_item.save, thread_sensitive=False)
                await save_kb_item_sync(update_fields=['ragflow_document_id'])

                self.log_operation("ragflow_upload_success", f"Uploaded KB item {file_id} to RagFlow: {upload_result.get('id')}")

                # Trigger dataset update to refresh embeddings and settings
                try:
                    update_dataset_sync = sync_to_async(ragflow_client.update_dataset, thread_sensitive=False)
                    await update_dataset_sync(dataset_id)
                    self.log_operation("ragflow_dataset_update_success", f"Updated RagFlow dataset {dataset_id} after file upload")
                except Exception as update_e:
                    # Log error but don't fail the entire upload process
                    self.log_operation("ragflow_dataset_update_error", f"Failed to update dataset {dataset_id}: {update_e}", "warning")
            else:
                self.log_operation("ragflow_upload_failed", f"Failed to upload KB item {file_id} to RagFlow - no document ID returned", "error")

        except Exception as e:
            self.log_operation("ragflow_upload_error", f"Error uploading KB item {file_id} to RagFlow: {e}", "error")


# Global singleton instance
upload_processor = UploadProcessor()
