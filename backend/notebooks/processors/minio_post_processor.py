"""
MinIO Post-Processor - Handle post-processing of extracted files and storage in MinIO.
"""

import logging
import os
from datetime import UTC, datetime
from typing import Any

# Direct import of caption generator utility
try:
    from reports.utils import (
        extract_all_image_references,
        extract_figure_data_from_markdown,
    )

    from ..utils.image_processing.caption_generator import generate_caption_for_image
except ImportError:
    generate_caption_for_image = None
    extract_figure_data_from_markdown = None
    extract_all_image_references = None


class MinIOPostProcessor:
    """Handle post-processing of extracted files and storage in MinIO."""

    def __init__(self, file_storage_service, logger=None):
        self.file_storage = file_storage_service
        self.logger = logger or logging.getLogger(__name__)

    def log_operation(self, operation: str, details: str = "", level: str = "info"):
        """Log operations with consistent formatting."""
        message = f"[minio_post_processor] {operation}"
        if details:
            message += f": {details}"
        getattr(self.logger, level)(message)

    def _should_filter_images(self, kb_item) -> bool:
        """
        Determine if images should be filtered based on markdown references.

        Returns:
            True: Filter images (only save referenced ones) - for PDFs
            False: Save all images (no filtering) - for PowerPoint, Word
        """
        if not kb_item or not kb_item.metadata:
            return True  # Default to filtering for safety

        # Get file type from metadata
        file_type = kb_item.metadata.get("file_type", "").lower()
        file_extension = kb_item.metadata.get("file_extension", "").lower()

        # PowerPoint and Word: save all images (no filtering)
        if file_type in ["powerpoint", "word"]:
            return False
        if file_extension in [".ppt", ".pptx", ".doc", ".docx"]:
            return False

        # PDF: filter images (only save referenced ones)
        return True

    def post_process_mineru_extraction(
        self, file_id: str, mineru_extraction_result: dict[str, Any]
    ):
        """
        Post-process MinerU extraction results by storing them in MinIO.
        This replaces the file system organization with MinIO object storage.
        """
        try:
            if not mineru_extraction_result.get("success"):
                return

            temp_mineru_dir = mineru_extraction_result.get("temp_mineru_dir")

            if not temp_mineru_dir or not os.path.exists(temp_mineru_dir):
                return

            # Get the MinIO storage service
            if not self.file_storage:
                self.log_operation(
                    "mineru_extraction_warning",
                    "MinIO file storage service not available",
                    "warning",
                )
                return

            try:
                # Import here to avoid circular imports
                from ..models import KnowledgeBaseItem

                # Get the knowledge base item
                kb_item = KnowledgeBaseItem.objects.filter(id=file_id).first()
                if not kb_item:
                    self.log_operation(
                        "mineru_extraction_warning",
                        f"Could not find knowledge base item for file_id: {file_id}",
                        "warning",
                    )
                    return

                # Get clean title for file organization
                clean_title = mineru_extraction_result.get("clean_title", "document")

                # Determine image filtering strategy based on document type
                should_filter = self._should_filter_images(kb_item)
                file_type = (
                    kb_item.metadata.get("file_type", "unknown")
                    if kb_item.metadata
                    else "unknown"
                )

                self.log_operation(
                    "image_processing_strategy",
                    f"Document type: {file_type}, Image filtering: {'enabled (PDF)' if should_filter else 'disabled (PPT/Word - save all images)'}",
                )

                # Process files from temp directory and store in MinIO
                content_files = []
                image_files = []
                markdown_content = None
                referenced_images = set()

                # First pass: extract markdown and find referenced images (only if filtering is enabled)
                for root, _, files in os.walk(temp_mineru_dir):
                    for file in files:
                        if file.endswith(".md"):
                            source_file = os.path.join(root, file)
                            with open(source_file, "rb") as f:
                                file_content = f.read()
                                markdown_content = file_content.decode(
                                    "utf-8", errors="ignore"
                                )
                                kb_item.content = markdown_content

                            # Extract ALL image references from markdown (only for PDFs)
                            if should_filter and extract_all_image_references:
                                try:
                                    # Use new function to extract ALL images, not just captioned ones
                                    image_references = extract_all_image_references(
                                        source_file
                                    )
                                    for image_path in image_references:
                                        if image_path:
                                            # Extract filename and add variations for matching
                                            full_name = os.path.basename(image_path)
                                            base_name = os.path.splitext(full_name)[0]

                                            # Add both full filename and base name
                                            referenced_images.add(full_name)
                                            referenced_images.add(base_name)

                                    self.log_operation(
                                        "extract_images_success",
                                        f"Found {len(image_references)} image references in markdown (PDF filtering): {image_references}",
                                    )
                                except Exception as e:
                                    self.log_operation(
                                        "extract_images_error",
                                        f"Failed to extract image references from markdown: {e}",
                                        "warning",
                                    )
                            break

                # Second pass: process files, filtering images by references
                for root, _, files in os.walk(temp_mineru_dir):
                    for file in files:
                        source_file = os.path.join(root, file)

                        # Skip all JSON metadata files
                        if file.endswith(".json"):
                            continue

                        # Read file content
                        with open(source_file, "rb") as f:
                            file_content = f.read()

                        # Determine file type and store in appropriate MinIO prefix
                        if file.endswith((".md", ".json")):
                            content_files.append(
                                self._process_content_file(
                                    file, file_content, clean_title, kb_item
                                )
                            )

                        elif file.endswith((".jpg", ".jpeg", ".png", ".gif", ".svg")):
                            # Determine if image should be saved based on filtering strategy
                            should_save_image = False

                            if not should_filter:
                                # PPT/Word: Save all images
                                should_save_image = True
                            else:
                                # PDF: Only save referenced images
                                file_base = os.path.splitext(file)[0]
                                is_referenced = (
                                    file in referenced_images  # Exact match
                                    or file_base in referenced_images  # Base name match
                                    or any(
                                        ref in file or file in ref
                                        for ref in referenced_images
                                        if len(ref) > 3
                                    )  # Partial match (avoid short refs)
                                )
                                should_save_image = is_referenced

                            if should_save_image:
                                try:
                                    result = self._process_image_file(
                                        file, file_content, kb_item
                                    )
                                    image_files.append(result)
                                except Exception as e:
                                    self.log_operation(
                                        "image_processing_error",
                                        f"Failed to process image {file}: {str(e)}",
                                        "error",
                                    )
                            else:
                                self.log_operation(
                                    "skip_unreferenced_image",
                                    f"Skipping unreferenced image: {file} "
                                    f"(PDF filtering: not in {len(referenced_images)} referenced images)",
                                )

                        else:
                            content_files.append(
                                self._process_other_file(file, file_content, kb_item)
                            )

                # Update the knowledge base item's metadata with MinIO object keys
                self._update_kb_item_metadata(kb_item, content_files, image_files)

                # Log summary
                self._log_processing_summary(content_files, image_files)

                # Clean up the temp directory
                self._cleanup_temp_directory(temp_mineru_dir)

            except Exception as e:
                self.log_operation(
                    "mineru_extraction_minio_error",
                    f"MinIO storage error while processing file_id {file_id}: {e}",
                    "error",
                )

        except Exception as e:
            self.log_operation(
                "post_process_mineru_extraction_minio_error",
                f"Failed to store MinerU extraction results in MinIO: {e}",
                "error",
            )
            # Clean up temp directory if it still exists
            temp_mineru_dir = marker_extraction_result.get("temp_mineru_dir")
            if temp_mineru_dir and os.path.exists(temp_mineru_dir):
                self._cleanup_temp_directory(temp_mineru_dir)

    def _process_content_file(
        self, file: str, file_content: bytes, clean_title: str, kb_item
    ) -> dict[str, str]:
        """Process content files (markdown, json) and store in MinIO."""
        # For any markdown file from MinerU, use clean title
        if file.endswith(".md"):
            target_filename = f"{clean_title}.md"
        else:
            target_filename = file

        # Store in MinIO using file ID structure
        object_key = self.file_storage.minio_backend.save_file_with_auto_key(
            content=file_content,
            filename=target_filename,
            prefix="kb",
            content_type="text/markdown"
            if file.endswith(".md")
            else "application/json",
            metadata={
                "kb_item_id": str(kb_item.id),
                "user_id": str(kb_item.notebook.user.id),
                "file_type": "mineru_content",
                "original_file": file,
            },
            user_id=str(kb_item.notebook.user.id),
            file_id=str(kb_item.id),
        )

        # Update the knowledge base item's file_object_key if this is a markdown file
        if file.endswith(".md"):
            kb_item.file_object_key = object_key

        return {
            "original_filename": file,
            "target_filename": target_filename,
            "object_key": object_key,
        }

    def _process_image_file(
        self, file: str, file_content: bytes, kb_item
    ) -> dict[str, str]:
        """Process image files and store in MinIO with database records."""
        target_filename = file

        # Determine content type
        import mimetypes

        content_type, _ = mimetypes.guess_type(target_filename)
        content_type = content_type or "application/octet-stream"

        # Import KnowledgeBaseImage model
        from ..models import KnowledgeBaseImage

        # Step 1: Create and save KnowledgeBaseImage record FIRST to get an ID
        # Use a placeholder for minio_object_key temporarily
        kb_image = KnowledgeBaseImage(
            knowledge_base_item=kb_item,
            image_caption="",  # Will be filled later if caption data is available
            minio_object_key="placeholder",  # Temporary value to satisfy constraint
            content_type=content_type,
            file_size=len(file_content),
            image_metadata={
                "original_filename": target_filename,
                "file_size": len(file_content),
                "content_type": content_type,
                "kb_item_id": str(kb_item.id),
                "source": "mineru_extraction",
                "original_file": file,
            },
        )

        try:
            # Save first to generate the ID
            kb_image.save()

            # Step 2: Now use the generated ID for MinIO storage
            object_key = self.file_storage.minio_backend.save_file_with_auto_key(
                content=file_content,
                filename=target_filename,
                prefix="kb",
                content_type=content_type,
                metadata={
                    "kb_item_id": str(kb_item.id),
                    "kb_image_id": str(kb_image.id),  # Add the image ID for reference
                    "user_id": str(kb_item.notebook.user.id),
                    "file_type": "mineru_image",
                    "original_file": file,
                },
                user_id=str(kb_item.notebook.user.id),
                file_id=str(kb_item.id),
                subfolder="images",
                subfolder_uuid=str(kb_image.id),  # Now kb_image.id exists!
            )

            # Validate that we got a valid object key
            if not object_key:
                raise ValueError(
                    f"MinIO returned empty object key for {target_filename}"
                )

            # Step 3: Update the record with the actual MinIO object key
            kb_image.minio_object_key = object_key
            kb_image.save(update_fields=["minio_object_key"])

            self.log_operation(
                "mineru_image_db_created",
                f"Created KnowledgeBaseImage record: id={kb_image.id}, object_key={object_key}",
            )

        except Exception as e:
            self.log_operation(
                "mineru_image_db_error",
                f"Failed to create KnowledgeBaseImage record for {target_filename}: {str(e)}\n"
                f"  kb_item_id={kb_item.id}\n"
                f"  file_size={len(file_content)}\n"
                f"  content_type={content_type}",
                "error",
            )
            # Clean up the database record if MinIO save failed
            if kb_image.id:
                try:
                    kb_image.delete()
                    self.log_operation(
                        "mineru_image_cleanup",
                        f"Cleaned up failed KnowledgeBaseImage record: id={kb_image.id}",
                    )
                except Exception:
                    pass
            # Re-raise to prevent silent failures
            raise

        return {
            "original_filename": file,
            "target_filename": target_filename,
            "object_key": object_key,
        }

    def _process_other_file(
        self, file: str, file_content: bytes, kb_item
    ) -> dict[str, str]:
        """Process other files and store in MinIO."""
        target_filename = file

        # Store in MinIO using file ID structure
        object_key = self.file_storage.minio_backend.save_file_with_auto_key(
            content=file_content,
            filename=target_filename,
            prefix="kb",
            metadata={
                "kb_item_id": str(kb_item.id),
                "user_id": str(kb_item.notebook.user.id),
                "file_type": "mineru_other",
                "original_file": file,
            },
            user_id=str(kb_item.notebook.user.id),
            file_id=str(kb_item.id),
        )

        return {
            "original_filename": file,
            "target_filename": target_filename,
            "object_key": object_key,
        }

    def _update_kb_item_metadata(self, kb_item, content_files: list, image_files: list):
        """Update knowledge base item metadata with extraction results."""
        if not kb_item.metadata:
            kb_item.metadata = {}

        kb_item.metadata["mineru_extraction"] = {
            "success": True,
            "content_files": content_files,
            "image_files": image_files,
            "total_files": len(content_files) + len(image_files),
            "extraction_timestamp": datetime.now(UTC).isoformat(),
            "storage_backend": "minio",
        }

        kb_item.save()

    def _log_processing_summary(self, content_files: list, image_files: list):
        """Log summary of processing results."""
        total_files = len(content_files) + len(image_files)
        self.log_operation(
            "mineru_extraction_minio_summary",
            f"Stored {total_files} MinerU files in MinIO: {len(content_files)} content files, {len(image_files)} image files",
        )

        if content_files:
            content_file_names = [f["target_filename"] for f in content_files]
            self.log_operation(
                "mineru_content_files_minio",
                f"Content files stored: {content_file_names}",
            )
        if image_files:
            image_file_names = [f["target_filename"] for f in image_files]
            self.log_operation(
                "mineru_image_files_minio", f"Image files stored: {image_file_names}"
            )

    def _cleanup_temp_directory(self, temp_mineru_dir: str):
        """Clean up temporary directory."""
        try:
            import shutil

            shutil.rmtree(temp_mineru_dir)
            self.log_operation(
                "mineru_cleanup", f"Cleaned up temporary directory: {temp_mineru_dir}"
            )
        except Exception as cleanup_error:
            self.log_operation(
                "mineru_cleanup_warning",
                f"Could not clean up temp MinerU directory: {cleanup_error}",
                "warning",
            )
