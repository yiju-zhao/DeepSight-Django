"""
Pydantic models for RAGFlow retrieval API.

Defines data contracts for retrieval requests and responses, ensuring
type-safe interactions with RAGFlow's /api/v1/retrieval endpoint.
"""

from typing import Optional
from pydantic import BaseModel, Field

# Import ChunkResponse from infrastructure layer and alias as RetrievalChunk
# for backward compatibility
from infrastructure.ragflow.models import ChunkResponse as RetrievalChunk


class DocAgg(BaseModel):
    """Document aggregation from retrieval response."""

    doc_id: str
    doc_name: str
    count: int


class RetrievalResponse(BaseModel):
    """
    Full retrieval API response from RAGFlow.

    Contains retrieved chunks, document aggregations, and total count.
    """

    chunks: list[RetrievalChunk]
    doc_aggs: list[DocAgg]
    total: int


class Citation(BaseModel):
    """
    Citation for final answer.

    Used to track source attribution in agent responses.
    """

    document_name: str
    chunk_id: str
    content_preview: str  # First 200 chars
    similarity: float
    document_id: Optional[str] = None
    dataset_id: Optional[str] = None
