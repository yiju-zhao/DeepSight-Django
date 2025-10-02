"""
Unified utilities for reports.
Includes image utilities and Xinference client utilities.
"""

import re
import logging
from typing import List, Dict, Set, Tuple, Optional, Any
from urllib.parse import urlparse
import uuid
from django.conf import settings

logger = logging.getLogger(__name__)

# =============================================================================
# PATTERNS AND CONSTANTS
# =============================================================================

# UUID Pattern for figure IDs (8-4-4-4-12 hexadecimal characters)
UUID_PATTERN = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'

# Compiled regex patterns for better performance
UUID_REGEX = re.compile(UUID_PATTERN)
UUID_BRACKET_PATTERN = rf'<({UUID_PATTERN})>'
UUID_BRACKET_REGEX = re.compile(UUID_BRACKET_PATTERN)

# Standalone placeholder pattern for figure replacements
PLACEHOLDER_PATTERN = rf"^\s*<({UUID_PATTERN})>\s*$"
PLACEHOLDER_REGEX = re.compile(PLACEHOLDER_PATTERN, re.MULTILINE)

# Pattern for checking existing img tags
EXISTING_IMG_PATTERN = r'<img\s+[^>]*src="[^"]*{figure_id}[^"]*"[^>]*>'

# Caption and figure patterns
FIGURE_LINE_PATTERN = r"^(?:<[^>]+>\s*)*\*{0,2}(?:Figure|Fig\.?|图)\s+(\d+)\.?[\s:|]+(.+?)(?:\*{0,2})?$"
FIGURE_LINE_REGEX = re.compile(FIGURE_LINE_PATTERN, re.IGNORECASE)

# Markdown image patterns
MD_IMAGE_PATTERN = r"^(?:<[^>]+>\s*)*!\[\]\((.*?)\)\s*(?:<[^>]+>)*$"
MD_IMAGE_REGEX = re.compile(MD_IMAGE_PATTERN, re.IGNORECASE)

# HTML image patterns
HTML_IMG_PATTERN = r'^<img\s+[^>]*?src=["\'](.*?)["\'][^>]*?>$'
HTML_IMG_REGEX = re.compile(HTML_IMG_PATTERN, re.IGNORECASE)

# Title cleaning patterns
TITLE_HTML_TAGS_PATTERN = r"<(strong|em|b|i)>(.*?)</\1>"
TITLE_HTML_TAGS_REGEX = re.compile(TITLE_HTML_TAGS_PATTERN)

TITLE_SPAN_PATTERN = r"<span[^>]*?>(.*?)</span>"
TITLE_SPAN_REGEX = re.compile(TITLE_SPAN_PATTERN)

TITLE_REMAINING_HTML_PATTERN = r"<[^>]*?>"
TITLE_REMAINING_HTML_REGEX = re.compile(TITLE_REMAINING_HTML_PATTERN)

TITLE_WHITESPACE_PATTERN = r"\s+"
TITLE_WHITESPACE_REGEX = re.compile(TITLE_WHITESPACE_PATTERN)

# =============================================================================
# FORMATTING FUNCTIONS
# =============================================================================

def create_image_placeholder(figure_id: str) -> str:
    """
    Create a placeholder for figure insertion.

    Args:
        figure_id: UUID string for the figure

    Returns:
        Placeholder string in format <figure_id>
    """
    return f"<{figure_id}>"


def clean_title_text(title: str) -> str:
    """
    Clean title text by removing HTML tags and normalizing whitespace.

    Args:
        title: Raw title text

    Returns:
        Cleaned title text
    """
    if not title:
        return ""

    # Remove HTML tags while preserving content
    title = TITLE_HTML_TAGS_REGEX.sub(r'\2', title)
    title = TITLE_SPAN_REGEX.sub(r'\1', title)
    title = TITLE_REMAINING_HTML_REGEX.sub('', title)

    # Normalize whitespace
    title = TITLE_WHITESPACE_REGEX.sub(' ', title).strip()

    return title


def preserve_figure_formatting(content: str) -> str:
    """
    Preserve proper spacing around figures and captions.

    Args:
        content: Content with figures

    Returns:
        Content with preserved formatting
    """
    if not content:
        return ""

    # Add proper spacing around captions
    lines = content.split('\n')
    formatted_lines = []

    for i, line in enumerate(lines):
        formatted_lines.append(line)

        # Add extra spacing after figure captions
        if FIGURE_LINE_REGEX.match(line.strip()):
            if i < len(lines) - 1 and lines[i + 1].strip():
                formatted_lines.append('')

    return '\n'.join(formatted_lines)


def normalize_content_spacing(content: str) -> str:
    """
    Normalize spacing in content while preserving intentional formatting.

    Args:
        content: Content to normalize

    Returns:
        Content with normalized spacing
    """
    if not content:
        return ""

    # Remove excessive blank lines but preserve intentional spacing
    content = re.sub(r'\n{3,}', '\n\n', content)

    # Normalize line endings
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    return content.strip()


# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================

def extract_figure_ids_from_content(content: str) -> List[str]:
    """
    Extract all figure IDs from content.
    Looks for UUID patterns that represent figure IDs.

    Args:
        content: Content with figure ID placeholders

    Returns:
        List of figure ID strings (UUIDs)
    """
    if not content:
        return []

    # Find all UUIDs in the content (these should be figure IDs)
    figure_ids = re.findall(UUID_PATTERN, content)

    # Remove duplicates while preserving order
    seen = set()
    unique_figure_ids = []
    for fig_id in figure_ids:
        if fig_id not in seen:
            seen.add(fig_id)
            unique_figure_ids.append(fig_id)

    logger.info(f"Extracted {len(unique_figure_ids)} unique figure IDs from content")
    return unique_figure_ids


def find_figure_placeholders(content: str, figure_dict: Dict[str, str]) -> Dict[str, int]:
    """
    Find first occurrences of figure placeholders in content.

    Args:
        content: Content to search
        figure_dict: Dictionary of figure IDs to URLs

    Returns:
        Dictionary mapping figure IDs to their first position in content
    """
    placeholder_positions = {}

    for figure_id in figure_dict.keys():
        placeholder = f"<{figure_id}>"
        position = content.find(placeholder)
        if position != -1:
            placeholder_positions[figure_id] = position

    return placeholder_positions


def find_already_inserted_figures(content: str, figure_ids: List[str]) -> Set[str]:
    """
    Find figures that are already inserted as img tags in content.

    Args:
        content: Content to search
        figure_ids: List of figure IDs to check

    Returns:
        Set of figure IDs that are already inserted
    """
    already_inserted = set()

    for figure_id in figure_ids:
        pattern = EXISTING_IMG_PATTERN.format(figure_id=figure_id)
        if re.search(pattern, content, re.IGNORECASE):
            already_inserted.add(figure_id)

    return already_inserted


def extract_figure_data_from_markdown(file_path: str) -> List[Dict[str, str]]:
    """
    Extract figure information (image path, caption) from a Markdown file.

    Args:
        file_path: Path to the Markdown file

    Returns:
        List of dictionaries with 'image_path' and 'caption' keys
    """
    if not file_path:
        return []

    figures = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        raise ValueError(f"Error reading file {file_path}: {e}")

    # First pass: collect all images
    image_locations = []
    for i, line in enumerate(lines):
        line_cleaned = line.strip()
        image_match = MD_IMAGE_REGEX.match(line_cleaned)
        html_img_match = None if image_match else HTML_IMG_REGEX.match(line_cleaned)

        if image_match or html_img_match:
            image_path = (
                image_match.group(1) if image_match else html_img_match.group(1)
            )
            image_locations.append((i, image_path))

    # Second pass: look for captions and associate with the nearest preceding image
    for i, line in enumerate(lines):
        caption_candidate_line = line.lstrip("\ufeff").strip()
        figure_match = FIGURE_LINE_REGEX.match(caption_candidate_line)

        if figure_match:
            figure_number = figure_match.group(1)
            caption = figure_match.group(2).strip()

            # Clean up markdown formatting in caption
            caption = re.sub(r'\*{2,}', '', caption)  # Remove ** markdown bold
            caption = caption.strip()

            # Find the nearest preceding image
            preceding_images = [
                (img_idx, img_path)
                for img_idx, img_path in image_locations
                if img_idx < i
            ]
            if preceding_images:
                # Get the closest image above this caption
                closest_img_idx, image_path = max(preceding_images, key=lambda x: x[0])

                # Check if the distance between image and caption is reasonable (within 10 lines)
                if i - closest_img_idx <= 10:
                    figures.append(
                        {
                            "image_path": image_path,
                            "caption": caption,
                        }
                    )

    # Remove duplicates while preserving order (based on image_path)
    unique_figures = []
    seen = set()
    for fig in figures:
        if fig["image_path"] not in seen:
            seen.add(fig["image_path"])
            unique_figures.append(fig)

    return unique_figures


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def is_valid_uuid(value: str) -> bool:
    """
    Check if a string is a valid UUID.

    Args:
        value: String to validate

    Returns:
        True if valid UUID, False otherwise
    """
    if not value:
        return False

    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError):
        return False


def is_valid_figure_id(figure_id: str) -> bool:
    """
    Check if a figure ID is valid (UUID format).

    Args:
        figure_id: Figure ID to validate

    Returns:
        True if valid, False otherwise
    """
    return is_valid_uuid(figure_id)


def validate_figure_ids(figure_ids: List[str]) -> List[str]:
    """
    Validate a list of figure IDs and return only valid ones.

    Args:
        figure_ids: List of figure IDs to validate

    Returns:
        List of valid figure IDs
    """
    valid_ids = []
    for figure_id in figure_ids:
        if is_valid_figure_id(figure_id):
            valid_ids.append(figure_id)
        else:
            logger.warning(f"Invalid figure ID: {figure_id}")

    return valid_ids


def convert_to_uuid_objects(figure_ids: List[str]) -> List[uuid.UUID]:
    """
    Convert string figure IDs to UUID objects.

    Args:
        figure_ids: List of figure ID strings

    Returns:
        List of UUID objects
    """
    uuid_objects = []
    for figure_id in figure_ids:
        try:
            uuid_obj = uuid.UUID(figure_id)
            uuid_objects.append(uuid_obj)
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not convert to UUID: {figure_id}, error: {e}")

    return uuid_objects


def validate_image_url(url: str) -> bool:
    """
    Validate an image URL.

    Args:
        url: URL to validate

    Returns:
        True if valid, False otherwise
    """
    if not url:
        return False

    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def validate_caption(caption: str) -> bool:
    """
    Validate a figure caption.

    Args:
        caption: Caption to validate

    Returns:
        True if valid, False otherwise
    """
    if not caption:
        return False

    # Basic validation - not empty and reasonable length
    return len(caption.strip()) > 0 and len(caption) < 1000


# =============================================================================
# URL PROVIDER CLASSES
# =============================================================================

class ImageUrlProvider:
    """Base class for image URL providers."""

    def get_image_relative_path(self, figure_id: str) -> Optional[str]:
        """Get relative path for a figure ID (used for Markdown embedding)."""
        raise NotImplementedError("Subclasses must implement get_image_relative_path")


class DatabaseUrlProvider(ImageUrlProvider):
    """URL provider that fetches relative paths from database."""

    def get_image_relative_path(self, figure_id: str) -> Optional[str]:
        """
        Get relative path for image from database.

        Args:
            figure_id: Figure ID to lookup

        Returns:
            Relative path in format 'images/{filename}' if found, None otherwise
        """
        try:
            from reports.models import ReportImage
            from pathlib import Path

            # Query ReportImage by figure_id
            report_image = ReportImage.objects.filter(figure_id=figure_id).first()
            if report_image and report_image.report_figure_minio_object_key:
                # Extract filename from MinIO object key
                filename = Path(report_image.report_figure_minio_object_key).name
                return f"images/{filename}"
        except Exception as e:
            logger.error(f"Error fetching image relative path for {figure_id}: {e}")

        return None


# =============================================================================
# IMAGE INSERTION SERVICE
# =============================================================================

class ImageInsertionService:
    """
    Service for inserting images into report content.
    Consolidated from the original insertion_service.py.
    """

    def __init__(self, url_provider: Optional[ImageUrlProvider] = None):
        """
        Initialize the service.

        Args:
            url_provider: Provider for image URLs, defaults to DatabaseUrlProvider
        """
        self.url_provider = url_provider or DatabaseUrlProvider()

    def insert_images_into_content(self, content: str, figure_ids: List[str]) -> str:
        """
        Insert images into content by replacing figure ID placeholders with Markdown images.

        Args:
            content: Content with figure placeholders
            figure_ids: List of figure IDs to insert

        Returns:
            Content with images inserted as Markdown with relative paths
        """
        if not content or not figure_ids:
            return content

        # Validate figure IDs
        valid_figure_ids = validate_figure_ids(figure_ids)
        if not valid_figure_ids:
            logger.warning("No valid figure IDs provided")
            return content

        # Get relative paths for all figures
        figure_paths = {}
        for figure_id in valid_figure_ids:
            relative_path = self.url_provider.get_image_relative_path(figure_id)
            if relative_path:
                figure_paths[figure_id] = relative_path

        if not figure_paths:
            logger.warning("No valid image paths found for figures")
            return content

        # Replace placeholders with Markdown image tags
        modified_content = content
        for figure_id, relative_path in figure_paths.items():
            placeholder = create_image_placeholder(figure_id)
            # Create Markdown image tag: ![Figure ID](images/filename.png)
            markdown_img = f"![{figure_id}]({relative_path})"
            modified_content = modified_content.replace(placeholder, markdown_img)
            logger.info(f"Replaced {placeholder} with {markdown_img}")

        # Apply formatting improvements
        modified_content = preserve_figure_formatting(modified_content)
        modified_content = normalize_content_spacing(modified_content)

        return modified_content

    def extract_and_insert_images(self, content: str) -> str:
        """
        Extract figure IDs from content and insert corresponding images.

        Args:
            content: Content to process

        Returns:
            Content with images inserted
        """
        figure_ids = extract_figure_ids_from_content(content)
        return self.insert_images_into_content(content, figure_ids)


# =============================================================================
# XINFERENCE CLIENT UTILITIES
# =============================================================================

def get_available_xinference_models() -> List[Dict[str, str]]:
    """
    Get list of available LLM models from Xinference.

    Returns:
        List of dicts with 'uid', 'name', and 'display_name' keys
    """
    try:
        from xinference.client import Client

        api_base = getattr(settings, 'XINFERENCE_API_BASE', None)
        if not api_base:
            logger.warning("XINFERENCE_API_BASE not configured")
            return []

        # Extract host and port from api_base (remove /v1 suffix if present)
        base_url = api_base.replace('/v1', '')

        client = Client(base_url)

        # List all running models
        running_models = client.list_models()

        models = []
        for model_uid, model_info in running_models.items():
            # Extract model information
            model_name = model_info.get('model_name', model_uid)
            model_type = model_info.get('model_type', 'LLM')

            # Only include LLM models
            if model_type.lower() == 'llm':
                display_name = f"{model_name} - Xinference"
                models.append({
                    'uid': model_uid,
                    'name': model_name,
                    'display_name': display_name,
                    'provider': 'xinference'
                })

        return models

    except ImportError:
        logger.error("xinference package not installed")
        return []
    except Exception as e:
        logger.error(f"Error listing Xinference models: {e}")
        return []


def get_xinference_model_info(model_uid: str) -> Optional[Dict]:
    """
    Get information about a specific Xinference model.

    Args:
        model_uid: The UID of the model

    Returns:
        Dict with model information or None if not found
    """
    try:
        from xinference.client import Client

        api_base = getattr(settings, 'XINFERENCE_API_BASE', None)
        if not api_base:
            return None

        base_url = api_base.replace('/v1', '')
        client = Client(base_url)

        running_models = client.list_models()
        return running_models.get(model_uid)

    except Exception as e:
        logger.error(f"Error getting Xinference model info: {e}")
        return None