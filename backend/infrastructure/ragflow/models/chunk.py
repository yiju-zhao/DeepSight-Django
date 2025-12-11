from typing import Any
from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """Document chunk entity."""

    id: str = Field(..., description="Chunk ID")
    content: str = Field(..., description="Chunk content")
    document_id: str = Field(..., description="Document ID")
    docnm_kwd: str | None = Field(None, description="Document name keyword")
    dataset_id: str | None = Field(None, description="Dataset ID")
    image_id: str = Field(default="", description="Image ID if applicable")
    important_keywords: str = Field(
        default="", description="Important keywords extracted"
    )
    positions: list[Any] = Field(
        default_factory=list,
        description="Chunk positions - can be list of strings or list of int lists",
    )
    available: bool = Field(True, description="Whether chunk is available")

    # Optional fields that may be present in search results
    similarity: float | None = Field(
        None, description="Similarity score if from search"
    )
    vector_similarity: float | None = Field(
        None, description="Vector similarity if from search"
    )
    term_similarity: float | None = Field(
        None, description="Term similarity if from search"
    )


class ChunkResponse(Chunk):
    """
    Chunk model for retrieval and completion API responses.

    Extends base Chunk with API field aliases and retrieval-specific fields.
    Used for:
    - /api/v1/retrieval endpoint responses
    - Completion reference chunks
    """

    # Override with field aliases for RAGFlow API compatibility
    document_name: str = Field(
        ...,
        alias="document_keyword",
        description="Document name (API returns as 'document_keyword')"
    )
    dataset_id: str = Field(
        ...,
        alias="kb_id",
        description="Dataset ID (API returns as 'kb_id')"
    )

    # Override important_keywords to list type
    important_keywords: list[str] = Field(
        default_factory=list,
        description="Important keywords extracted"
    )

    # Additional fields for retrieval responses
    content_ltks: str | None = Field(
        None,
        description="Content with lowercase tokens"
    )
    highlight: str | None = Field(
        None,
        description="Highlighted content with matched terms"
    )

    # URL field from ReferenceChunk
    url: str | None = Field(
        None,
        description="URL if applicable"
    )

    # doc_type field from ReferenceChunk
    doc_type: str | list[str] = Field(
        default="",
        description="Document type(s) - can be string or list"
    )

    model_config = {"populate_by_name": True}


# Type alias for backward compatibility
# ReferenceChunk is now an alias to ChunkResponse
ReferenceChunk = ChunkResponse


class DocumentInfo(BaseModel):
    """Document metadata in chunk list response."""

    id: str = Field(..., description="Document ID")
    name: str = Field(..., description="Document name")
    location: str = Field(..., description="Document location")
    size: int = Field(..., description="Document size in bytes")
    chunk_count: int = Field(..., description="Number of chunks")
    chunk_method: str = Field(..., description="Chunking method used")
    dataset_id: str = Field(..., description="Associated dataset ID")
    status: str = Field(..., description="Processing status")
    progress: float = Field(..., description="Processing progress (0-1)")
    progress_msg: str = Field(..., description="Progress message")
    type: str = Field(..., description="Document type")
    source_type: str = Field(..., description="Source type (local, web, etc.)")
    parser_config: dict[str, Any] = Field(
        default_factory=dict, description="Parser configuration"
    )
    token_count: int = Field(0, description="Total token count")
    create_time: int | None = Field(None, description="Creation timestamp (ms)")
    create_date: str | None = Field(None, description="Creation date string")
    update_time: int | None = Field(None, description="Update timestamp (ms)")
    update_date: str | None = Field(None, description="Update date string")
    process_begin_at: str | None = Field(None, description="Processing start time")
    process_duration: float | None = Field(None, description="Processing duration (s)")
    thumbnail: str = Field(default="", description="Thumbnail URL if available")
    run: str | None = Field(None, description="Run number")
    created_by: str | None = Field(None, description="Creator user ID")


class ChunkListData(BaseModel):
    """Chunk list response data."""

    chunks: list[Chunk] = Field(default_factory=list, description="List of chunks")
    doc: DocumentInfo | None = Field(None, description="Document metadata")
    total: int = Field(0, description="Total number of chunks")
