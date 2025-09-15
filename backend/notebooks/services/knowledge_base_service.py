"""
Knowledge Base Service - Handle knowledge base operations following Django patterns.
Includes integrated image management functionality.
"""
import json
import logging
import os
import tempfile
from typing import Dict, List, Optional, Any
import re
from urllib.parse import urlparse
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from rest_framework import status

from ..models import KnowledgeBaseItem, BatchJob, KnowledgeBaseImage
from ..utils.storage import get_storage_adapter, get_minio_backend
from core.services import NotebookBaseService

logger = logging.getLogger(__name__)


class KnowledgeBaseService(NotebookBaseService):
    """
    Handle knowledge base operations business logic following Django patterns.
    Includes integrated image management functionality.
    """
    
    def __init__(self):
        super().__init__()
        self.storage_adapter = get_storage_adapter()
        self.minio_backend = get_minio_backend()
    
    def perform_action(self, **kwargs):
        """
        Implementation of abstract method from BaseService.
        This service uses direct method calls rather than the template pattern.
        """
        pass
    
    def get_processed_content(self, kb_item: KnowledgeBaseItem, expires: int = 3600) -> str:
        """
        Get processed markdown content from a knowledge base item.
        Uses only the database content field for simplified access.

        Args:
            kb_item: KnowledgeBaseItem instance

        Returns:
            Processed content as string
        """
        try:
            # Get content directly from the database content field
            if kb_item.content and kb_item.content.strip():
                logger.debug(f"Returning content from database field for KB item {kb_item.id}")
                # Replace local image paths with presigned URLs for preview rendering
                return self._replace_local_image_paths(kb_item.content, kb_item, expires=expires)

            # Return empty string if no content found
            logger.info(f"No content found in database field for KB item {kb_item.id}")
            return ""

        except Exception as e:
            logger.error(f"Error getting processed content for KB item {kb_item.id}: {e}")
            return ""

    def _replace_local_image_paths(self, markdown: str, kb_item: KnowledgeBaseItem, expires: int = 3600) -> str:
        """
        Replace local image references in markdown with presigned MinIO URLs.

        Supports both markdown image syntax and HTML <img> tags.
        Only replaces relative/local paths (no scheme, not data:, not absolute URLs).
        """
        try:
            # Quick exit if no obvious image tokens
            if not markdown or ('![' not in markdown and '<img' not in markdown):
                return markdown

            # Build mapping from original paths and basenames to presigned URLs
            from ..models import KnowledgeBaseImage
            images = KnowledgeBaseImage.objects.filter(knowledge_base_item=kb_item).only(
                'id', 'minio_object_key', 'image_metadata'
            )

            path_to_url: Dict[str, str] = {}
            basename_to_url: Dict[str, str] = {}

            for img in images:
                # Best practice: serve via backend API proxy to avoid client MinIO dependency
                url = f"/api/v1/notebooks/{kb_item.notebook.id}/files/{kb_item.id}/image/{img.id}/inline/"
                original_file = None
                original_filename = None
                if isinstance(img.image_metadata, dict):
                    original_file = img.image_metadata.get('original_file')
                    original_filename = img.image_metadata.get('original_filename')
                # Prefer full relative path match
                if original_file:
                    # Normalize to use forward slashes
                    norm = original_file.replace('\\', '/')
                    path_to_url[norm] = url
                    # Also map basename
                    basename_to_url[os.path.basename(norm)] = url
                if original_filename:
                    basename_to_url[original_filename] = url

            if not path_to_url and not basename_to_url:
                return markdown

            # Helper to decide if url is local/relative
            def is_local_path(p: str) -> bool:
                parsed = urlparse(p)
                if parsed.scheme or parsed.netloc:
                    return False
                # data URIs or anchors should be left alone
                if p.startswith('data:') or p.startswith('#'):
                    return False
                return True

            # Replace in markdown image syntax: ![alt](url)
            md_img_pattern = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+['\"][^)]+['\"])??\)")

            def md_repl(match: re.Match) -> str:
                orig_url = match.group(1)
                if not is_local_path(orig_url):
                    return match.group(0)
                norm = orig_url.replace('\\', '/')
                new_url = path_to_url.get(norm)
                if not new_url:
                    new_url = basename_to_url.get(os.path.basename(norm))
                if not new_url:
                    return match.group(0)
                return match.group(0).replace(orig_url, new_url)

            markdown = md_img_pattern.sub(md_repl, markdown)

            # Replace in HTML <img src="...">
            html_img_pattern = re.compile(r"<img([^>]*?)src=[\"\']([^\"\']+)[\"\']([^>]*)>")

            def html_repl(match: re.Match) -> str:
                pre, src, post = match.groups()
                if not is_local_path(src):
                    return match.group(0)
                norm = src.replace('\\', '/')
                new_url = path_to_url.get(norm)
                if not new_url:
                    new_url = basename_to_url.get(os.path.basename(norm))
                if not new_url:
                    return match.group(0)
                return f"<img{pre}src=\"{new_url}\"{post}>"

            markdown = html_img_pattern.sub(html_repl, markdown)

            return markdown
        except Exception as e:
            logger.exception(f"Error replacing image URLs for KB item {kb_item.id}: {e}")
            return markdown

    def get_user_knowledge_base(self, user_id: int, notebook, content_type: str = None, limit: int = None, offset: int = None) -> Dict:
        """
        Get knowledge base items for this specific notebook.
        
        Args:
            user_id: User ID
            notebook: Notebook instance
            content_type: Optional content type filter
            limit: Optional limit for pagination
            offset: Optional offset for pagination
            
        Returns:
            Dict with knowledge base items and metadata
        """
        # Validate notebook access
        self.validate_notebook_access(notebook, notebook.user)
        try:
            # Since knowledge base items are now notebook-specific, just get items for this notebook
            queryset = KnowledgeBaseItem.objects.filter(notebook=notebook)
            
            # Apply content type filter if specified
            if content_type:
                queryset = queryset.filter(content_type=content_type)
                
            # Apply pagination
            if offset:
                queryset = queryset[offset:]
            if limit:
                queryset = queryset[:limit]
                
            # Convert to dictionary format for API compatibility
            knowledge_base = []
            for kb_item in queryset.order_by('-created_at'):
                item_data = {
                    "id": str(kb_item.id),
                    "title": kb_item.title,
                    "content_type": kb_item.content_type,
                    "parsing_status": kb_item.parsing_status,
                    "metadata": kb_item.metadata or {},
                    "file_metadata": kb_item.file_metadata or {},
                    "created_at": kb_item.created_at.isoformat(),
                    "updated_at": kb_item.updated_at.isoformat(),
                    "linked_to_notebook": True,  # All items are now linked to the notebook
                    "notes": kb_item.notes,
                    "tags": kb_item.tags,
                }
                knowledge_base.append(item_data)

            return {
                "success": True,
                "items": knowledge_base,
                "notebook_id": notebook.id,
                "pagination": {"limit": limit, "offset": offset},
            }

        except Exception as e:
            self.logger.exception(f"Failed to retrieve knowledge base for user {user_id}: {e}")
            return {
                "error": "Failed to retrieve knowledge base",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    @transaction.atomic
    def link_knowledge_item_to_notebook(self, kb_item_id: str, notebook, user_id: int, notes: str = "") -> Dict:
        """
        Link a knowledge base item to a notebook.
        
        Args:
            kb_item_id: Knowledge base item ID
            notebook: Notebook instance
            user_id: User ID
            notes: Optional notes
            
        Returns:
            Dict with operation result
        """
        # Validate notebook access
        self.validate_notebook_access(notebook, notebook.user)
        try:
            # Link the item using storage adapter
            success = self.storage_adapter.link_knowledge_item_to_notebook(
                kb_item_id=kb_item_id,
                notebook_id=notebook.id,
                user_id=user_id,
                notes=notes,
            )

            if success:
                return {
                    "success": True,
                    "linked": True
                }
            else:
                return {
                    "error": "Failed to link knowledge item",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
                }

        except Exception as e:
            self.logger.exception(f"Failed to link KB item {kb_item_id} to notebook {notebook.id}: {e}")
            return {
                "error": "Link operation failed",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    @transaction.atomic
    def delete_knowledge_base_item(self, kb_item_id, user_id):
        """Delete a knowledge base item entirely from user's knowledge base"""
        try:
            # Delete the knowledge base item entirely
            success = self.storage_adapter.delete_knowledge_base_item(
                kb_item_id, user_id
            )

            if success:
                return {
                    "success": True,
                    "status_code": status.HTTP_204_NO_CONTENT
                }
            else:
                return {
                    "error": "Knowledge base item not found or access denied",
                    "status_code": status.HTTP_404_NOT_FOUND,
                }

        except Exception as e:
            logger.exception(f"Failed to delete KB item {kb_item_id} for user {user_id}: {e}")
            return {
                "error": "Delete operation failed",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    def get_knowledge_base_images(self, file_id, notebook):
        """Get all images for a knowledge base item"""
        try:
            # Get the knowledge base item from the notebook
            kb_item = get_object_or_404(KnowledgeBaseItem, id=file_id, notebook=notebook)
            
            # Get all images for this knowledge base item
            images = KnowledgeBaseImage.objects.filter(
                knowledge_base_item=kb_item
            ).order_by('created_at')
            
            # Serialize image data
            image_data = []
            for image in images:
                image_url = image.get_image_url(expires=3600)  # 1 hour
                if image_url:
                    # Get the original filename from metadata for display
                    original_filename = "unknown"
                    if image.image_metadata and 'original_filename' in image.image_metadata:
                        original_filename = image.image_metadata['original_filename']
                    
                    image_data.append({
                        'id': str(image.id),
                        'figure_id': str(image.figure_id),
                        'name': str(image.figure_id),  # Use figure_id as name for API compatibility
                        'image_caption': image.image_caption,
                        'image_url': image_url,
                        'imageUrl': image_url,  # Also include imageUrl for frontend compatibility
                        'content_type': image.content_type,
                        'file_size': image.file_size,
                        'created_at': image.created_at.isoformat(),
                        'original_filename': original_filename,
                    })
            
            return {
                "success": True,
                'images': image_data,
                'count': len(image_data),
                'knowledge_base_item_id': file_id,
            }

        except Exception as e:
            logger.exception(f"Failed to retrieve images for KB item {file_id}: {e}")
            return {
                "error": "Failed to retrieve images",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    def get_images(self, kb_item: KnowledgeBaseItem) -> List[Dict[str, Any]]:
        """Compatibility helper for views: return list of images for a KB item.

        Mirrors get_knowledge_base_images but returns just the images list, as
        expected by FileViewSet.images view.
        """
        try:
            images = KnowledgeBaseImage.objects.filter(
                knowledge_base_item=kb_item
            ).order_by('created_at')

            image_data: List[Dict[str, Any]] = []
            for image in images:
                image_url = image.get_image_url(expires=3600)
                if not image_url:
                    continue
                original_filename = "unknown"
                if image.image_metadata and 'original_filename' in image.image_metadata:
                    original_filename = image.image_metadata['original_filename']

                image_data.append({
                    'id': str(image.id),
                    'figure_id': str(image.figure_id),
                    'name': str(image.figure_id),
                    'image_caption': image.image_caption,
                    'image_url': image_url,
                    'imageUrl': image_url,
                    'content_type': image.content_type,
                    'file_size': image.file_size,
                    'created_at': image.created_at.isoformat(),
                    'original_filename': original_filename,
                })

            return image_data
        except Exception as e:
            logger.exception(f"Failed to retrieve images list for KB item {kb_item.id}: {e}")
            return []

    def get_batch_job_status(self, batch_job_id, notebook):
        """Get status of a batch job"""
        try:
            # Get the batch job
            batch_job = get_object_or_404(BatchJob, id=batch_job_id, notebook=notebook)

            # Get batch job items
            from ..models import BatchJobItem
            items = BatchJobItem.objects.filter(batch_job=batch_job).order_by('created_at')

            # Serialize data
            items_data = []
            for item in items:
                items_data.append({
                    'id': str(item.id),
                    'item_data': item.item_data,
                    'upload_id': item.upload_id,
                    'status': item.status,
                    'result_data': item.result_data,
                    'error_message': item.error_message,
                    'created_at': item.created_at.isoformat(),
                    'updated_at': item.updated_at.isoformat(),
                })

            return {
                "success": True,
                'batch_job': {
                    'id': str(batch_job.id),
                    'job_type': batch_job.job_type,
                    'status': batch_job.status,
                    'total_items': batch_job.total_items,
                    'completed_items': batch_job.completed_items,
                    'failed_items': batch_job.failed_items,
                    'created_at': batch_job.created_at.isoformat(),
                    'updated_at': batch_job.updated_at.isoformat(),
                },
                'items': items_data,
            }

        except Exception as e:
            logger.exception(f"Failed to get batch job {batch_job_id} status: {e}")
            return {
                "error": "Failed to get batch job status",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    # Image Management Methods
    
    def get_images_for_knowledge_base_item(self, kb_item_id: int, user_id: int = None) -> List[Dict[str, Any]]:
        """
        Get all images for a knowledge base item in figure_data.json compatible format.
        
        Args:
            kb_item_id: Knowledge base item ID
            user_id: User ID for additional security check (optional)
            
        Returns:
            List of image dictionaries in figure_data.json compatible format
        """
        try:
            # Validate access to knowledge base item
            kb_item_query = KnowledgeBaseItem.objects.filter(id=kb_item_id)
            if user_id:
                # Knowledge base items are now notebook-specific, filter by notebook owner
                kb_item_query = kb_item_query.filter(notebook__user=user_id)
            
            kb_item = kb_item_query.first()
            if not kb_item:
                logger.warning(f"Knowledge base item {kb_item_id} not found or access denied")
                return []
            
            # Get all images for this knowledge base item
            images = KnowledgeBaseImage.objects.filter(
                knowledge_base_item=kb_item
            ).order_by('id')
            
            # Convert to figure_data.json compatible format
            figure_data = [image.to_figure_data_dict() for image in images]
            
            logger.info(f"Retrieved {len(figure_data)} images for knowledge base item {kb_item_id}")
            return figure_data
            
        except Exception as e:
            logger.error(f"Error retrieving images for kb_item {kb_item_id}: {e}")
            return []
    
    def get_combined_figure_data_for_files(self, file_ids: List[str], user_id: int = None) -> List[Dict[str, Any]]:
        """
        Get combined figure data for multiple knowledge base items.
        This replaces the functionality of creating combined figure_data.json files.
        
        Args:
            file_ids: List of knowledge base item IDs
            user_id: User ID for security checks
            
        Returns:
            Combined list of figure data dictionaries with renumbered figures
        """
        combined_figure_data = []
        
        try:
            for file_id in file_ids:
                # Remove 'f_' prefix if present
                clean_file_id = file_id.replace('f_', '') if file_id.startswith('f_') else file_id
                
                # Get images for this file
                file_images = self.get_images_for_knowledge_base_item(clean_file_id, user_id)
                combined_figure_data.extend(file_images)
            
            # No need to renumber figures since we're using UUIDs
                
            logger.info(f"Combined figure data from {len(file_ids)} files: {len(combined_figure_data)} total images")
            return combined_figure_data
            
        except Exception as e:
            logger.error(f"Error creating combined figure data: {e}")
            return []
    
    def update_image_caption(self, figure_id: str, caption: str, user_id: int = None) -> bool:
        """
        Update the caption for a specific image.
        
        Args:
            figure_id: KnowledgeBaseImage figure_id
            caption: New caption text
            user_id: User ID for security check
            
        Returns:
            True if successful, False otherwise
        """
        try:
            image_query = KnowledgeBaseImage.objects.filter(figure_id=figure_id)
            if user_id:
                # Knowledge base items are now notebook-specific, filter by notebook owner
                image_query = image_query.filter(knowledge_base_item__notebook__user=user_id)
            
            image = image_query.first()
            if not image:
                logger.warning(f"Image {figure_id} not found or access denied")
                return False
            
            image.image_caption = caption
            image.save(update_fields=['image_caption', 'updated_at'])
            
            logger.info(f"Updated caption for image {figure_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating caption for image {figure_id}: {e}")
            return False
    
    def update_images_from_figure_data(self, kb_item_id: int, figure_data: List[Dict[str, Any]], user_id: int = None) -> bool:
        """
        Update image captions and metadata from figure_data format.
        This helps migrate or update data from existing figure_data.json files.
        
        Args:
            kb_item_id: Knowledge base item ID
            figure_data: List of figure data dictionaries
            user_id: User ID for security check
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate access to knowledge base item
            kb_item_query = KnowledgeBaseItem.objects.filter(id=kb_item_id)
            if user_id:
                # Knowledge base items are now notebook-specific, filter by notebook owner
                kb_item_query = kb_item_query.filter(notebook__user=user_id)
            
            kb_item = kb_item_query.first()
            if not kb_item:
                logger.warning(f"Knowledge base item {kb_item_id} not found or access denied")
                return False
            
            updated_count = 0
            
            with transaction.atomic():
                for figure in figure_data:
                    # Try to match by image file name
                    image_file = figure.get('image_file', '')
                    caption = figure.get('caption', '')
                    
                    if not image_file and 'image_path' in figure:
                        image_file = os.path.basename(figure['image_path'])
                    
                    # Find matching image in database
                    matching_image = None
                    if image_file:
                        # Try to match by filename in object key
                        matching_image = KnowledgeBaseImage.objects.filter(
                            knowledge_base_item=kb_item,
                            minio_object_key__icontains=image_file
                        ).first()
                    
                    if matching_image:
                        # Update existing image
                        matching_image.image_caption = caption
                        
                        # Update metadata
                        matching_image.image_metadata.update({
                            'updated_from_figure_data': True,
                            'original_figure_data': figure
                        })
                        
                        matching_image.save()
                        updated_count += 1
                        
                        logger.debug(f"Updated image {matching_image.id} with caption from figure_data")
            
            logger.info(f"Updated {updated_count} images from figure_data for kb_item {kb_item_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating images from figure_data for kb_item {kb_item_id}: {e}")
            return False
    
    def migrate_figure_data_json_to_database(self, kb_item_id: int, figure_data_path: str, user_id: int = None) -> bool:
        """
        Migrate from figure_data.json file to database records.
        This method helps transition from the old file-based system.
        
        Args:
            kb_item_id: Knowledge base item ID
            figure_data_path: Path to existing figure_data.json file
            user_id: User ID for security check
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(figure_data_path):
                logger.info(f"Figure data file doesn't exist: {figure_data_path}")
                return False
            
            # Load figure data from JSON file
            with open(figure_data_path, 'r', encoding='utf-8') as f:
                figure_data = json.load(f)
            
            if not figure_data:
                logger.info(f"No figure data found in {figure_data_path}")
                return False
            
            # Update images using the figure data
            success = self.update_images_from_figure_data(kb_item_id, figure_data, user_id)
            
            if success:
                logger.info(f"Successfully migrated figure_data.json to database for kb_item {kb_item_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error migrating figure_data.json to database: {e}")
            return False
    
    def delete_image(self, figure_id: str, user_id: int = None, delete_from_minio: bool = True) -> bool:
        """
        Delete an image record and optionally its file from MinIO.
        
        Args:
            figure_id: KnowledgeBaseImage figure_id
            user_id: User ID for security check
            delete_from_minio: Whether to also delete the file from MinIO
            
        Returns:
            True if successful, False otherwise
        """
        try:
            image_query = KnowledgeBaseImage.objects.filter(figure_id=figure_id)
            if user_id:
                # Knowledge base items are now notebook-specific, filter by notebook owner
                image_query = image_query.filter(knowledge_base_item__notebook__user=user_id)
            
            image = image_query.first()
            if not image:
                logger.warning(f"Image {figure_id} not found or access denied")
                return False
            
            object_key = image.minio_object_key
            
            # Delete from database
            image.delete()
            
            # Delete from MinIO if requested
            if delete_from_minio and object_key:
                try:
                    self.minio_backend.delete_file(object_key)
                    logger.info(f"Deleted image file from MinIO: {object_key}")
                except Exception as e:
                    logger.warning(f"Failed to delete image file from MinIO {object_key}: {e}")
            
            logger.info(f"Deleted image record {figure_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting image {figure_id}: {e}")
            return False
    
    def get_image_url(self, figure_id: str, user_id: int = None, expires: int = 3600) -> Optional[str]:
        """
        Get pre-signed URL for image access.
        
        Args:
            figure_id: KnowledgeBaseImage figure_id
            user_id: User ID for security check
            expires: URL expiration time in seconds
            
        Returns:
            Pre-signed URL or None if not found
        """
        try:
            image_query = KnowledgeBaseImage.objects.filter(figure_id=figure_id)
            if user_id:
                # Knowledge base items are now notebook-specific, filter by notebook owner
                image_query = image_query.filter(knowledge_base_item__notebook__user=user_id)
            
            image = image_query.first()
            if not image:
                return None
            
            return image.get_image_url(expires)
            
        except Exception as e:
            logger.error(f"Error getting image URL for {figure_id}: {e}")
            return None
    
    def get_image_stats_for_knowledge_base_item(self, kb_item_id: int, user_id: int = None) -> Dict[str, Any]:
        """
        Get statistics about images for a knowledge base item.
        
        Args:
            kb_item_id: Knowledge base item ID
            user_id: User ID for security check
            
        Returns:
            Dictionary with image statistics
        """
        try:
            # Validate access to knowledge base item
            kb_item_query = KnowledgeBaseItem.objects.filter(id=kb_item_id)
            if user_id:
                # Knowledge base items are now notebook-specific, filter by notebook owner
                kb_item_query = kb_item_query.filter(notebook__user=user_id)
            
            kb_item = kb_item_query.first()
            if not kb_item:
                return {}
            
            images = KnowledgeBaseImage.objects.filter(knowledge_base_item=kb_item)
            
            stats = {
                'total_images': images.count(),
                'images_with_captions': images.exclude(image_caption='').count(),
                'total_file_size': sum(img.file_size for img in images),
                'content_types': list(images.values_list('content_type', flat=True).distinct()),
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats for kb_item {kb_item_id}: {e}")
            return {}
    
    def auto_populate_captions_from_content(self, kb_item_id: int, user_id: int = None) -> bool:
        """
        Automatically populate image captions by extracting figure data from the knowledge base item's content.
        This method uses the extract_figure_data function from paper_processing.py.
        
        Args:
            kb_item_id: Knowledge base item ID
            user_id: User ID for security check
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate access to knowledge base item
            kb_item_query = KnowledgeBaseItem.objects.filter(id=kb_item_id)
            if user_id:
                # Knowledge base items are now notebook-specific, filter by notebook owner
                kb_item_query = kb_item_query.filter(notebook__user=user_id)
            
            kb_item = kb_item_query.first()
            if not kb_item:
                logger.warning(f"Knowledge base item {kb_item_id} not found or access denied")
                return False
            
            # Get markdown content from the knowledge base item
            markdown_content = self._get_markdown_content(kb_item)
            if not markdown_content:
                logger.info(f"No markdown content found for KB item {kb_item_id}")
                return False
            
            # Extract figure data from markdown content
            figure_data = self._extract_figure_data_from_content(markdown_content)
            if not figure_data:
                logger.info(f"No figure data extracted from KB item {kb_item_id}")
                return False
            
            # Update images with extracted captions
            success = self.update_images_from_figure_data(kb_item_id, figure_data, user_id)
            
            if success:
                logger.info(f"Auto-populated captions for KB item {kb_item_id} from content")
            
            return success
            
        except Exception as e:
            logger.error(f"Error auto-populating captions for KB item {kb_item_id}: {e}")
            return False
    
    def _get_markdown_content(self, kb_item):
        """Get markdown content from knowledge base item using database field."""
        try:
            # Get content directly from database field
            if kb_item.content and kb_item.content.strip():
                return kb_item.content
            return None

        except Exception as e:
            logger.error(f"Error getting markdown content for KB item {kb_item.id}: {e}")
            return None

    def _extract_figure_data_from_content(self, content):
        """Extract figure data from markdown content using a temporary file."""
        try:
            # Import here to avoid circular imports
            from reports.image_utils import extract_figure_data_from_markdown
            
            # Create a temporary markdown file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Extract figure data using the paper processing function
                figure_data = extract_figure_data_from_markdown(temp_file_path)
                return figure_data or []
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Error extracting figure data from content: {e}")
            return [] 
