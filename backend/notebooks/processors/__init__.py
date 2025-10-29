"""
Processors package for the notebooks module.

This package contains processing logic:
- upload_processor.py: Main upload processor with comprehensive file handling
- minio_post_processor.py: MinIO post-processing for MinerU extractions
"""

# Main upload processor
try:
    from .upload_processor import UploadProcessor
except ImportError:
    UploadProcessor = None

# Supporting service modules
try:
    from .minio_post_processor import MinIOPostProcessor
except ImportError:
    MinIOPostProcessor = None

__all__ = [
    "UploadProcessor",
    "MinIOPostProcessor",
]
