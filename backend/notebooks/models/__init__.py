"""
Notebooks models package.

This package organizes notebook-related models following Django best practices.
Each model is in its own focused module for better maintainability.
"""

from .batch_processing import BatchJob, BatchJobItem
from .chat_session import ChatSession, SessionChatMessage
from .knowledge_item import KnowledgeBaseImage, KnowledgeBaseItem
from .notebook import Notebook

# Maintain backward compatibility
__all__ = [
    "Notebook",
    "KnowledgeBaseItem",
    "KnowledgeBaseImage",
    "BatchJob",
    "BatchJobItem",
    "ChatSession",
    "SessionChatMessage",
]
