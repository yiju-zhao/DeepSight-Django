"""
Serializers package for the notebooks module.

This package contains focused serializers for different aspects:
- notebook_serializers.py: Notebook-related serializers
- file_serializers.py: File upload and processing serializers
- url_serializers.py: URL processing serializers
"""

# Notebook serializers
# Batch processing serializers
from .batch_serializers import BatchJobItemSerializer, BatchJobSerializer

# File serializers
from .file_serializers import (
    BatchFileUploadSerializer,
    FileUploadSerializer,
    KnowledgeBaseImageSerializer,
    KnowledgeBaseItemSerializer,
    VideoImageExtractionSerializer,
)
from .notebook_serializers import (
    NotebookCreateSerializer,
    NotebookListSerializer,
    NotebookSerializer,
    NotebookUpdateSerializer,
)

# URL serializers
from .url_serializers import (
    BatchURLParseSerializer,
    BatchURLParseWithMediaSerializer,
    URLParseDocumentSerializer,
    URLParseSerializer,
    URLParseWithMediaSerializer,
)

__all__ = [
    # Notebook
    "NotebookSerializer",
    "NotebookListSerializer",
    "NotebookCreateSerializer",
    "NotebookUpdateSerializer",
    # File processing
    "FileUploadSerializer",
    "VideoImageExtractionSerializer",
    "BatchFileUploadSerializer",
    "KnowledgeBaseItemSerializer",
    "KnowledgeBaseImageSerializer",
    # URL processing
    "URLParseSerializer",
    "URLParseWithMediaSerializer",
    "URLParseDocumentSerializer",
    "BatchURLParseSerializer",
    "BatchURLParseWithMediaSerializer",
    # Batch processing
    "BatchJobSerializer",
    "BatchJobItemSerializer",
]
