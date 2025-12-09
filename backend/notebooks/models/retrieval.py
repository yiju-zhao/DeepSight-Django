"""
Pydantic models for RAGFlow retrieval API.

Defines data contracts for retrieval requests and responses, ensuring
type-safe interactions with RAGFlow's /api/v1/retrieval endpoint.
"""

from typing import Optional
from pydantic import BaseModel, Field


class RetrievalChunk(BaseModel):
    """
    Single chunk from RAGFlow retrieval API.

    Represents a piece of retrieved content with associated metadata
    including similarity scores and source information.
    """

    id: str
    content: str
    document_id: str
    document_name: str = Field(alias="document_keyword")
    dataset_id: str = Field(alias="kb_id")
    similarity: float
    vector_similarity: Optional[float] = None
    term_similarity: Optional[float] = None
    positions: list[str] = Field(default_factory=list)
    important_keywords: list[str] = Field(default_factory=list)
    image_id: str = ""
    content_ltks: Optional[str] = None
    highlight: Optional[str] = None

    class Config:
        populate_by_name = True  # Allow both alias and field name


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
