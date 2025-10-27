"""
Services package for the notebooks module.

This package contains all business logic services:
- notebook_service.py: Notebook operations
- file_service.py: File processing business logic
- url_service.py: URL processing business logic
- chat_service.py: Chat and RAG business logic
- knowledge_base_service.py: Knowledge base operations
- base_service.py: Base service class (moved from utils)
- knowledge_base_image_service.py: Knowledge base image service (moved from utils)
"""

# Focused services for notebooks
from .chat_service import ChatService
from .file_service import FileService
from .knowledge_base_service import KnowledgeBaseService
from .notebook_service import NotebookService
from .url_service import URLService

# Optional services
try:
    from .knowledge_base_image_service import KnowledgeBaseImageService
except ImportError:
    KnowledgeBaseImageService = None

__all__ = [
    "NotebookService",
    "FileService",
    "URLService",
    "ChatService",
    "KnowledgeBaseService",
    "KnowledgeBaseImageService",
]
