"""
Notebooks utilities package.

This package provides organized utilities for the DeepSight notebooks application:
- validators.py: Input validation for files and URLs
- storage.py: Storage operations using MinIO backend
- helpers.py: Common utilities and configuration
"""

# Core configuration
# Helper utilities and services
from .helpers import (
    AsyncResponseMixin,
    ContentIndexingService,
    ErrorHandlingMixin,
    NotebookPermissionMixin,
    NotebooksConfig,
    RAGChatbot,
    calculate_content_hash,
    calculate_source_hash,
    calculate_user_content_hash,
    check_content_duplicate,
    check_source_duplicate,
    clean_title,
    cleanup_temp_file,
    create_temp_file,
    extract_domain,
    format_file_size,
    generate_unique_filename,
    get_notebooks_config,
    get_file_extension,
    get_mime_type_from_extension,
    is_safe_filename,
    sanitize_path,
    truncate_text,
)

# Storage operations
from .storage import (
    FileStorageService,
    MinIOBackend,
    StorageAdapter,
    get_minio_backend,
    get_storage_adapter,
)

# Validators
from .validators import (
    ALLOWED_FILE_EXTENSIONS,
    MAX_FILE_SIZE,
    FileValidator,
    URLValidator,
    get_content_type_for_extension,
    sanitize_filename,
    validate_file_type,
)

# Legacy imports with fallbacks for backward compatibility
try:
    from ..processors.upload_processor import UploadProcessor, get_upload_processor
except ImportError:
    UploadProcessor = None
    get_upload_processor = None

__all__ = [
    # Configuration
    "get_notebooks_config",
    "NotebooksConfig",
    # Validators
    "FileValidator",
    "URLValidator",
    "validate_file_type",
    "get_content_type_for_extension",
    "sanitize_filename",
    "ALLOWED_FILE_EXTENSIONS",
    "MAX_FILE_SIZE",
    # Storage
    "FileStorageService",
    "StorageAdapter",
    "MinIOBackend",
    "get_storage_adapter",
    "get_minio_backend",
    # Helpers
    "clean_title",
    "calculate_content_hash",
    "calculate_user_content_hash",
    "check_content_duplicate",
    "calculate_source_hash",
    "check_source_duplicate",
    "extract_domain",
    "sanitize_path",
    "get_file_extension",
    "get_mime_type_from_extension",
    "is_safe_filename",
    "generate_unique_filename",
    "create_temp_file",
    "cleanup_temp_file",
    "format_file_size",
    "truncate_text",
    "ContentIndexingService",
    "RAGChatbot",
    "NotebookPermissionMixin",
    "ErrorHandlingMixin",
    "AsyncResponseMixin",
    # Legacy processors (may be None if not available)
    "UploadProcessor",
    "get_upload_processor",
]
