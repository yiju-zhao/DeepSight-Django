"""
Caption Service - Handle image caption generation and extraction.
"""
import os
import tempfile
import logging
from typing import List, Optional, Dict, Any

try:
    from reports.image_utils import extract_figure_data_from_markdown
    from notebooks.utils.image_processing.caption_generator import generate_caption_for_image
except ImportError:
    extract_figure_data_from_markdown = None
    generate_caption_for_image = None


class CaptionService:
    """Handle image caption generation and extraction."""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def log_operation(self, operation: str, details: str = "", level: str = "info"):
        """Log operations with consistent formatting."""
        message = f"[caption_service] {operation}"
        if details:
            message += f": {details}"
        getattr(self.logger, level)(message)

    def populate_image_captions_for_kb_item(self, kb_item, markdown_content=None):
        """
        Populate image captions for all images in a knowledge base item.
        Uses markdown extraction first, then AI generation as fallback.
        """
        try:
            # Get markdown content if not provided
            if not markdown_content:
                markdown_content = self._get_markdown_content_for_captions(kb_item)
            
            if not markdown_content:
                self.log_operation("caption_population_warning", 
                    f"No markdown content found for KB item {kb_item.id}, using AI-only captions", "warning")
            
            # Get all images for this knowledge base item that need captions
            from ..models import KnowledgeBaseImage
            images_needing_captions = KnowledgeBaseImage.objects.filter(
                knowledge_base_item=kb_item,
                image_caption__in=['', None]
            ).order_by('created_at')
            
            if not images_needing_captions.exists():
                return
                
            # Extract figure data from markdown if available
            figure_data = []
            if markdown_content and extract_figure_data_from_markdown:
                figure_data = self._extract_figure_data_from_content_for_captions(markdown_content)
            
            # Process each image
            updated_count = 0
            ai_generated_count = 0
            
            for image in images_needing_captions:
                try:
                    caption = None
                    caption_source = None
                    
                    # Try to find caption from markdown first
                    if figure_data:
                        caption = self._find_caption_for_image_in_upload(image, figure_data, images_needing_captions)
                        if caption:
                            caption_source = "markdown"
                    
                    # Use AI generation as fallback if no caption found from markdown
                    if not caption and generate_caption_for_image:
                        caption = self._generate_ai_caption_for_upload(image)
                        if caption and not caption.startswith("Caption generation failed"):
                            caption_source = "AI"
                            ai_generated_count += 1
                    
                    # Update the image with the caption
                    if caption:
                        image.image_caption = caption
                        image.save(update_fields=['image_caption', 'updated_at'])
                        updated_count += 1
                        self.log_operation("caption_updated", 
                            f"Updated image {image.id} with {caption_source} caption: {caption[:50]}...")
                    else:
                        self.log_operation("caption_not_found", 
                            f"No caption found for image {image.id}", "warning")
                
                except Exception as e:
                    self.log_operation("caption_image_error", 
                        f"Error processing image {image.id}: {e}", "error")
                        
            # Log summary
            self.log_operation("caption_population_summary", 
                f"Updated {updated_count} images with captions ({ai_generated_count} AI-generated)")
                
        except Exception as e:
            self.log_operation("caption_population_error", 
                f"Error populating captions for KB item {kb_item.id}: {e}", "error")

    def _get_markdown_content_for_captions(self, kb_item):
        """Get markdown content from knowledge base item using model manager."""
        try:
            from ..models import KnowledgeBaseItem
            
            # Use the model manager to get content
            content = KnowledgeBaseItem.objects.get_content(str(kb_item.id), kb_item.notebook.user.pk)
            return content
            
        except Exception as e:
            self.log_operation("get_markdown_content_error", 
                f"Error getting markdown content for KB item {kb_item.id}: {e}", "error")
            return None

    def _extract_figure_data_from_content_for_captions(self, content):
        """Extract figure data from markdown content using a temporary file."""
        try:
            # Create a temporary markdown file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Extract figure data using the image_utils function
                figure_data = extract_figure_data_from_markdown(temp_file_path)
                return figure_data or []
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            self.log_operation("extract_figure_data_error", 
                f"Error extracting figure data from content: {e}", "error")
            return []

    def _find_caption_for_image_in_upload(self, image, figure_data, all_images):
        """Find matching caption for an image from figure data."""
        try:
            # Try to match by image name from object key first
            if image.minio_object_key:
                image_basename = os.path.basename(image.minio_object_key).lower()
                for figure in figure_data:
                    figure_image_path = figure.get('image_path', '')
                    if figure_image_path:
                        figure_basename = figure_image_path.split('/')[-1].lower()
                        if figure_basename == image_basename:
                            return figure.get('caption', '')
            
            # Fallback: match by index in the figure data list
            # Use the creation order as an approximation
            if figure_data:
                try:
                    image_index = list(all_images).index(image)
                    if image_index < len(figure_data):
                        return figure_data[image_index].get('caption', '')
                except (ValueError, IndexError):
                    pass
            
            return None
            
        except Exception as e:
            self.log_operation("find_caption_error", 
                f"Error finding caption for image {image.id}: {e}", "error")
            return None
    
    def _generate_ai_caption_for_upload(self, image, api_key=None):
        """Generate AI caption for an image using OpenAI vision model."""
        try:
            # Download image from MinIO to a temporary file
            temp_image_path = self._download_image_to_temp_for_caption(image)
            
            if not temp_image_path:
                self.log_operation("ai_caption_download_error", 
                    f"Could not download image {image.id} from MinIO for AI captioning", "error")
                return None
            
            try:
                # Generate caption using AI
                caption = generate_caption_for_image(temp_image_path, api_key=api_key)
                return caption
            
            finally:
                # Clean up temporary file
                if os.path.exists(temp_image_path):
                    os.unlink(temp_image_path)
            
        except Exception as e:
            self.log_operation("ai_caption_generation_error", 
                f"Error generating AI caption for image {image.id}: {e}", "error")
            return None
    
    def _download_image_to_temp_for_caption(self, image):
        """Download image from MinIO to a temporary file for caption generation."""
        try:
            # Get image content from MinIO
            image_content = image.get_image_content()
            
            if not image_content:
                return None
            
            # Determine file extension from content type or object key
            file_extension = '.png'  # default
            if image.content_type:
                if 'jpeg' in image.content_type or 'jpg' in image.content_type:
                    file_extension = '.jpg'
                elif 'png' in image.content_type:
                    file_extension = '.png'
                elif 'gif' in image.content_type:
                    file_extension = '.gif'
                elif 'webp' in image.content_type:
                    file_extension = '.webp'
            elif image.minio_object_key:
                # Try to get extension from object key
                object_key_lower = image.minio_object_key.lower()
                if object_key_lower.endswith('.jpg') or object_key_lower.endswith('.jpeg'):
                    file_extension = '.jpg'
                elif object_key_lower.endswith('.png'):
                    file_extension = '.png'
                elif object_key_lower.endswith('.gif'):
                    file_extension = '.gif'
                elif object_key_lower.endswith('.webp'):
                    file_extension = '.webp'
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(
                suffix=file_extension, 
                delete=False
            ) as temp_file:
                temp_file.write(image_content)
                temp_file_path = temp_file.name
            
            return temp_file_path
            
        except Exception as e:
            self.log_operation("download_image_temp_error", 
                f"Error downloading image {image.id} to temp file: {e}", "error")
            return None