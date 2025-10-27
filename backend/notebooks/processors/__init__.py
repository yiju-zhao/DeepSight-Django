"""
Processors package for the notebooks module.

This package contains all processing logic for different types of content:
- media_processors.py: Media processing utilities
- upload_processor.py: Main upload processor with comprehensive file handling
- url_extractor.py: URL extractor (moved from utils)
"""

# Media processors
from .media_processors import MediaProcessor

# Main upload processor (refactored and cleaned)
try:
    from .upload_processor import UploadProcessor
except ImportError:
    UploadProcessor = None

# Supporting service modules
try:
    from .caption_service import CaptionService
    from .device_manager import DeviceManager
    from .file_type_processors import FileTypeProcessors
    from .minio_post_processor import MinIOPostProcessor
    from .transcription_service import TranscriptionService
except ImportError:
    FileTypeProcessors = None
    DeviceManager = None
    TranscriptionService = None
    CaptionService = None
    MinIOPostProcessor = None

# Legacy processors (moved from utils)
try:
    from .url_extractor import URLExtractor
except ImportError:
    URLExtractor = None

__all__ = [
    "MediaProcessor",
    "UploadProcessor",
    "FileTypeProcessors",
    "DeviceManager",
    "TranscriptionService",
    "CaptionService",
    "MinIOPostProcessor",
    "URLExtractor",
]
