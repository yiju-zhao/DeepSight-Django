"""
MinIO Post-Processor - Handle post-processing of extracted files and storage in MinIO.
"""
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any

# Direct import of caption generator utility
try:
    from ..utils.image_processing.caption_generator import generate_caption_for_image
    from reports.utils import extract_figure_data_from_markdown
except ImportError:
    generate_caption_for_image = None
    extract_figure_data_from_markdown = None


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

    def post_process_mineru_extraction(self, file_id: str, marker_extraction_result: Dict[str, Any]):
        """
        Post-process MinerU PDF extraction results by storing them in MinIO.
        This replaces the file system organization with MinIO object storage.
        """
        try:
            if not marker_extraction_result.get("success"):
                return

            temp_marker_dir = marker_extraction_result.get("temp_marker_dir")

            if not temp_marker_dir or not os.path.exists(temp_marker_dir):
                return

            # Get the MinIO storage service
            if not self.file_storage:
                self.log_operation("mineru_extraction_warning", "MinIO file storage service not available", "warning")
                return

            try:
                # Import here to avoid circular imports
                from ..models import KnowledgeBaseItem
                
                # Get the knowledge base item
                kb_item = KnowledgeBaseItem.objects.filter(id=file_id).first()
                if not kb_item:
                    self.log_operation("mineru_extraction_warning", f"Could not find knowledge base item for file_id: {file_id}", "warning")
                    return
                
                # Get clean title for file organization
                clean_title = marker_extraction_result.get("clean_title", "document")
                
                # Process files from temp directory and store in MinIO
                content_files = []
                image_files = []
                markdown_content = None
                referenced_images = set()

                # First pass: extract markdown and find referenced images
                for root, _, files in os.walk(temp_marker_dir):
                    for file in files:
                        if file.endswith('.md'):
                            source_file = os.path.join(root, file)
                            with open(source_file, 'rb') as f:
                                file_content = f.read()
                                markdown_content = file_content.decode('utf-8', errors='ignore')
                                kb_item.content = markdown_content

                            # Extract referenced images from markdown
                            if extract_figure_data_from_markdown:
                                try:
                                    figure_data = extract_figure_data_from_markdown(source_file)
                                    for fig in figure_data:
                                        image_path = fig.get('image_path', '')
                                        if image_path:
                                            # Extract just the filename from the path
                                            referenced_images.add(os.path.basename(image_path))
                                except Exception as e:
                                    self.log_operation("extract_figures_error", f"Failed to extract figures from markdown: {e}", "warning")
                            break

                # Second pass: process files, filtering images by references
                for root, _, files in os.walk(temp_marker_dir):
                    for file in files:
                        source_file = os.path.join(root, file)

                        # Skip all JSON metadata files
                        if file.endswith('.json'):
                            continue

                        # Read file content
                        with open(source_file, 'rb') as f:
                            file_content = f.read()

                        # Determine file type and store in appropriate MinIO prefix
                        if file.endswith(('.md', '.json')):
                            content_files.append(self._process_content_file(
                                file, file_content, clean_title, kb_item
                            ))

                        elif file.endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg')):
                            # Only process images that are referenced in the markdown
                            if file in referenced_images:
                                image_files.append(self._process_image_file(
                                    file, file_content, kb_item
                                ))
                            else:
                                self.log_operation("skip_unreferenced_image", f"Skipping unreferenced image: {file}")

                        else:
                            content_files.append(self._process_other_file(
                                file, file_content, kb_item
                            ))
                
                # Update the knowledge base item's metadata with MinIO object keys
                self._update_kb_item_metadata(kb_item, content_files, image_files)

                # Log summary
                self._log_processing_summary(content_files, image_files)

                # Clean up the temp directory
                self._cleanup_temp_directory(temp_marker_dir)
                    
            except Exception as e:
                self.log_operation("mineru_extraction_minio_error", f"MinIO storage error while processing file_id {file_id}: {e}", "error")

        except Exception as e:
            self.log_operation("post_process_mineru_extraction_minio_error", f"Failed to store MinerU extraction results in MinIO: {e}", "error")
            # Clean up temp directory if it still exists
            temp_marker_dir = marker_extraction_result.get("temp_marker_dir")
            if temp_marker_dir and os.path.exists(temp_marker_dir):
                self._cleanup_temp_directory(temp_marker_dir)

    def _process_content_file(self, file: str, file_content: bytes, clean_title: str, kb_item) -> Dict[str, str]:
        """Process content files (markdown, json) and store in MinIO."""
        # For any markdown file from MinerU, use clean title
        if file.endswith('.md'):
            target_filename = f"{clean_title}.md"
        else:
            target_filename = file
        
        # Store in MinIO using file ID structure
        object_key = self.file_storage.minio_backend.save_file_with_auto_key(
            content=file_content,
            filename=target_filename,
            prefix="kb",
            content_type="text/markdown" if file.endswith('.md') else "application/json",
            metadata={
                'kb_item_id': str(kb_item.id),
                'user_id': str(kb_item.notebook.user.id),
                'file_type': 'mineru_content',
                'original_file': file,
            },
            user_id=str(kb_item.notebook.user.id),
            file_id=str(kb_item.id)
        )
        
        # Update the knowledge base item's file_object_key if this is a markdown file
        if file.endswith('.md'):
            kb_item.file_object_key = object_key
        
        return {
            'original_filename': file,
            'target_filename': target_filename,
            'object_key': object_key
        }

    def _process_image_file(self, file: str, file_content: bytes, kb_item) -> Dict[str, str]:
        """Process image files and store in MinIO with database records."""
        target_filename = file
        
        # Determine content type
        import mimetypes
        content_type, _ = mimetypes.guess_type(target_filename)
        content_type = content_type or 'application/octet-stream'
        
        # Create KnowledgeBaseImage record first to get ID
        from ..models import KnowledgeBaseImage
        
        # Create a temporary record to get the ID
        kb_image = KnowledgeBaseImage(
            knowledge_base_item=kb_item,
            image_caption="",  # Will be filled later if caption data is available
            content_type=content_type,
            file_size=len(file_content),
            image_metadata={
                'original_filename': target_filename,
                'file_size': len(file_content),
                'content_type': content_type,
                'kb_item_id': str(kb_item.id),
                'source': 'mineru_extraction',
                'original_file': file,
            }
        )
        
        # Store in MinIO using file ID structure with images subfolder and UUID
        object_key = self.file_storage.minio_backend.save_file_with_auto_key(
            content=file_content,
            filename=target_filename,
            prefix="kb",
            content_type=content_type,
            metadata={
                'kb_item_id': str(kb_item.id),
                'user_id': str(kb_item.notebook.user.id),
                'file_type': 'mineru_image',
                'original_file': file,
            },
            user_id=str(kb_item.notebook.user.id),
            file_id=str(kb_item.id),
            subfolder="images",
            subfolder_uuid=str(kb_image.id)
        )
        
        # Now set the object key and save the record
        try:
            kb_image.minio_object_key = object_key
            kb_image.save()
            
            self.log_operation(
                "mineru_image_db_created", 
                f"Created KnowledgeBaseImage record: id={kb_image.id}, object_key={object_key}"
            )
            
        except Exception as e:
            self.log_operation(
                "mineru_image_db_error", 
                f"Failed to create KnowledgeBaseImage record for {target_filename}: {str(e)}", 
                "error"
            )
        
        return {
            'original_filename': file,
            'target_filename': target_filename,
            'object_key': object_key
        }

    def _process_other_file(self, file: str, file_content: bytes, kb_item) -> Dict[str, str]:
        """Process other files and store in MinIO."""
        target_filename = file
        
        # Store in MinIO using file ID structure
        object_key = self.file_storage.minio_backend.save_file_with_auto_key(
            content=file_content,
            filename=target_filename,
            prefix="kb",
            metadata={
                'kb_item_id': str(kb_item.id),
                'user_id': str(kb_item.notebook.user.id),
                'file_type': 'mineru_other',
                'original_file': file,
            },
            user_id=str(kb_item.notebook.user.id),
            file_id=str(kb_item.id)
        )
        
        return {
            'original_filename': file,
            'target_filename': target_filename,
            'object_key': object_key
        }

    def _update_kb_item_metadata(self, kb_item, content_files: list, image_files: list):
        """Update knowledge base item metadata with extraction results."""
        if not kb_item.file_metadata:
            kb_item.file_metadata = {}

        kb_item.file_metadata['mineru_extraction'] = {
            'success': True,
            'content_files': content_files,
            'image_files': image_files,
            'total_files': len(content_files) + len(image_files),
            'extraction_timestamp': datetime.now(timezone.utc).isoformat(),
            'storage_backend': 'minio'
        }

        kb_item.save()

    def _log_processing_summary(self, content_files: list, image_files: list):
        """Log summary of processing results."""
        total_files = len(content_files) + len(image_files)
        self.log_operation("mineru_extraction_minio_summary", 
            f"Stored {total_files} MinerU files in MinIO: {len(content_files)} content files, {len(image_files)} image files")
        
        if content_files:
            content_file_names = [f['target_filename'] for f in content_files]
            self.log_operation("mineru_content_files_minio", f"Content files stored: {content_file_names}")
        if image_files:
            image_file_names = [f['target_filename'] for f in image_files]
            self.log_operation("mineru_image_files_minio", f"Image files stored: {image_file_names}")

    def _cleanup_temp_directory(self, temp_marker_dir: str):
        """Clean up temporary directory."""
        try:
            import shutil
            shutil.rmtree(temp_marker_dir)
            self.log_operation("mineru_cleanup", f"Cleaned up temporary directory: {temp_marker_dir}")
        except Exception as cleanup_error:
            self.log_operation("mineru_cleanup_warning", f"Could not clean up temp MinerU directory: {cleanup_error}", "warning")
