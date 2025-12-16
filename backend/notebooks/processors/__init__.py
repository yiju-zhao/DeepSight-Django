"""
Processors package for the notebooks module.

This package contains processing logic:
- upload_processor.py: Main upload processor with comprehensive file handling
- minio_post_processor.py: MinIO post-processing for MinerU extractions
"""

# Main upload processor
try:
    from .upload_processor import UploadProcessor, get_upload_processor
except ImportError:
    UploadProcessor = None
    get_upload_processor = None

# MinIOPostProcessor is imported lazily in orchestrator to avoid loading
# heavy dependencies (torch, transformers) at startup

__all__ = [
    "UploadProcessor",
    "get_upload_processor",
]
