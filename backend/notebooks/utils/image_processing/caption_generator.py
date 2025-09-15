"""
Caption generation for images using OpenAI's vision models.
Includes utilities for knowledge base image caption processing.
"""

import os
import base64
import mimetypes
import json
import re
import logging
import tempfile
from typing import List, Dict, Any, Optional
from tqdm import tqdm

try:
    from reports.image_utils import extract_figure_data_from_markdown
except ImportError:
    extract_figure_data_from_markdown = None

logger = logging.getLogger(__name__)

def to_data_url(path: str) -> str:
    """Read an image file and return data-URL string suitable for OpenAI vision models."""
    mime, _ = mimetypes.guess_type(path)
    mime = mime or "application/octet-stream"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}"

def generate_caption_for_image(
    image_path: str, 
    prompt: str = "Look at the image and do the following in one sentences: Focus more on important numbers or text shown in the image (such as signs, titles, or numbers), and briefly summarize the key points from the text. Give your answer in one clear sentences. Add a tag at the end if you find <chart> or <table> in the image.",
    api_key: Optional[str] = None
) -> str:
    """
    Generate a caption for a single image using OpenAI's vision model.
    
    Args:
        image_path: Path to the image file
        prompt: Prompt for caption generation
        api_key: OpenAI API key (will try to get from environment if not provided)
        
    Returns:
        Generated caption text
    """
    try:
        from openai import OpenAI
        
        # Get API key
        if not api_key:
            api_key = load_api_key_from_settings()

        if not api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable or provide api_key parameter.")
        
        client = OpenAI(api_key=api_key)
        data_url = to_data_url(image_path)
        
        chat = client.chat.completions.create(
            model="gpt-4.1-mini",  # Using the latest vision model
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }],
            max_tokens=100,
        )
        
        return chat.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Caption generation failed for {image_path}: {e}")
        return f"Caption generation failed: {str(e)}"

def generate_captions_for_directory(
    images_dir: str,
    output_file: str,
    prompt: str = "Look at the image and do the following in one sentences: Focus more on important numbers or text shown in the image (such as signs, titles, or numbers), and briefly summarize the key points from the text. Give your answer in one clear sentences. Add a tag at the end if you find <chart> or <table> in the image.",
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate captions for all PNG images in a directory.
    
    Args:
        images_dir: Directory containing PNG images to caption
        output_file: Path to save the captions JSON file
        prompt: Caption prompt to use for all images
        api_key: OpenAI API key
        
    Returns:
        List of caption results
    """
    try:
        if not os.path.exists(images_dir):
            raise FileNotFoundError(f"Images directory not found: {images_dir}")
        
        # Find all PNG images
        images = [
            f for f in os.listdir(images_dir)
            if f.lower().endswith(".png") and os.path.isfile(os.path.join(images_dir, f))
        ]
        
        if not images:
            logger.warning(f"No PNG images found in {images_dir}")
            return []
        
        results = []
        total_images = len(images)
        logger.info(f"Starting caption generation for {total_images} images...")
        
        # Use tqdm for progress bar
        for img in tqdm(images, desc="Generating captions", unit="image"):
            image_path = os.path.join(images_dir, img)
            caption_text = generate_caption_for_image(image_path, prompt, api_key)
            
            results.append({
                "image_path": image_path,
                "caption": caption_text
            })
        
        # Sort results by image number (extracted from filename)
        try:
            results.sort(key=lambda x: int(re.search(r'(\d+)', os.path.basename(x['image_path'])).group(0)))
        except (AttributeError, ValueError):
            # If sorting fails, keep original order
            logger.warning("Could not sort results by image number")
        
        # Save results to file
        with open(output_file, "w") as out_f:
            json.dump(results, out_f, indent=2)
        
        logger.info(f"Generated {len(results)} captions and saved to {output_file}")
        return results
        
    except Exception as e:
        logger.error(f"Caption generation for directory failed: {e}")
        raise

def load_api_key_from_settings() -> Optional[str]:
    """
    Try to load OpenAI API key from various sources.

    Returns:
        API key if found, None otherwise
    """
    # Try environment variable first
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        return api_key

    # Try to load from settings
    try:
        from app.core.config import get_settings
        settings = get_settings()
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            return settings.OPENAI_API_KEY
    except Exception:
        pass

    # Try to load from secrets.toml at project root
    try:
        import toml
        # Get the project root directory (4 levels up from this file)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
        secrets_path = os.path.join(project_root, "secrets.toml")

        if os.path.exists(secrets_path):
            with open(secrets_path, "r") as f:
                secrets = toml.load(f)
            api_key = secrets.get("OPENAI_API_KEY")
            if api_key:
                return api_key

        # Fallback to relative paths for compatibility
        possible_paths = [
            "secrets.toml",
            "../secrets.toml",
            "../../secrets.toml",
            "../../../secrets.toml",
            "../../../../secrets.toml"
        ]

        for path in possible_paths:
            if os.path.exists(path):
                with open(path, "r") as f:
                    secrets = toml.load(f)
                api_key = secrets.get("OPENAI_API_KEY")
                if api_key:
                    return api_key
    except Exception:
        pass

    return None


# Knowledge Base Image Caption Functions
# =====================================

def populate_image_captions_for_kb_item(kb_item, markdown_content=None):
    """
    Populate image captions for all images in a knowledge base item.
    Uses markdown extraction first, then AI generation as fallback.

    Args:
        kb_item: KnowledgeBaseItem instance
        markdown_content: Optional markdown content to extract captions from

    Returns:
        Dict with success status, counts, and any errors
    """
    try:
        logger.info(f"Starting caption population for KB item {kb_item.id}")

        # Get markdown content if not provided
        if not markdown_content:
            markdown_content = _get_markdown_content_for_captions(kb_item)

        if not markdown_content:
            logger.warning(f"No markdown content found for KB item {kb_item.id}, using AI-only captions")

        # Get all images for this knowledge base item that need captions
        from ...models import KnowledgeBaseImage
        images_needing_captions = KnowledgeBaseImage.objects.filter(
            knowledge_base_item=kb_item,
            image_caption__in=['', None]
        ).order_by('created_at')

        if not images_needing_captions.exists():
            logger.info(f"No images need captions for KB item {kb_item.id}")
            return {
                'success': True,
                'captions_count': 0,
                'total_images': 0
            }

        # Extract figure data from markdown if available
        figure_data = []
        if markdown_content and extract_figure_data_from_markdown:
            figure_data = _extract_figure_data_from_content(markdown_content)

        # Process each image
        updated_count = 0
        ai_generated_count = 0

        for image in images_needing_captions:
            try:
                caption = None
                caption_source = None

                # Try to find caption from markdown first
                if figure_data:
                    caption = _find_caption_for_kb_image(image, figure_data, list(images_needing_captions))
                    if caption:
                        caption_source = "markdown"

                # Use AI generation as fallback if no caption found from markdown
                if not caption:
                    caption = _generate_ai_caption_for_kb_image(image)
                    if caption and not caption.startswith("Caption generation failed"):
                        caption_source = "AI"
                        ai_generated_count += 1

                # Update the image with the caption
                if caption:
                    image.image_caption = caption
                    image.save(update_fields=['image_caption', 'updated_at'])
                    updated_count += 1
                    logger.info(f"Updated image {image.id} with {caption_source} caption: {caption[:50]}...")
                else:
                    logger.warning(f"No caption found for image {image.id}")

            except Exception as e:
                logger.error(f"Error processing image {image.id}: {e}")

        # Log summary
        logger.info(f"Caption population completed: Updated {updated_count} images with captions ({ai_generated_count} AI-generated)")

        return {
            'success': True,
            'captions_count': updated_count,
            'total_images': images_needing_captions.count(),
            'ai_generated_count': ai_generated_count
        }

    except Exception as e:
        logger.error(f"Error populating captions for KB item {kb_item.id}: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def _get_markdown_content_for_captions(kb_item):
    """Get markdown content from knowledge base item using database field."""
    try:
        # Get content directly from database field
        if kb_item.content and kb_item.content.strip():
            return kb_item.content
        return None
    except Exception as e:
        logger.error(f"Error getting markdown content for KB item {kb_item.id}: {e}")
        return None


def _extract_figure_data_from_content(content):
    """Extract figure data from markdown content using a temporary file."""
    if not extract_figure_data_from_markdown:
        return []

    try:
        import tempfile

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
        logger.error(f"Error extracting figure data from content: {e}")
        return []


def _find_caption_for_kb_image(image, figure_data, all_images):
    """Find matching caption for a knowledge base image from figure data."""
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
        if figure_data:
            try:
                image_index = all_images.index(image)
                if image_index < len(figure_data):
                    return figure_data[image_index].get('caption', '')
            except (ValueError, IndexError):
                pass

        return None

    except Exception as e:
        logger.error(f"Error finding caption for image {image.id}: {e}")
        return None


def _generate_ai_caption_for_kb_image(image):
    """Generate AI caption for a knowledge base image."""
    try:
        # Download image from MinIO to a temporary file
        temp_image_path = _download_kb_image_to_temp(image)

        if not temp_image_path:
            logger.error(f"Could not download image {image.id} from MinIO for AI captioning")
            return None

        try:
            # Generate caption using the main function
            caption = generate_caption_for_image(temp_image_path)
            return caption

        finally:
            # Clean up temporary file
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    except Exception as e:
        logger.error(f"Error generating AI caption for image {image.id}: {e}")
        return None


def _download_kb_image_to_temp(image):
    """Download knowledge base image from MinIO to a temporary file."""
    try:
        import tempfile

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
        logger.error(f"Error downloading image {image.id} to temp file: {e}")
        return None
