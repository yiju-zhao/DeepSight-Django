"""
RAGFlow Pydantic models for API responses and entities.

Provides type-safe models for all RAGFlow API interactions.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, field_validator


# Generic type variable for API responses
T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    Generic API response wrapper.

    Used for all RAGFlow API responses that follow the standard format:
    {"code": 0, "message": "", "data": {...}}
    """

    code: int = Field(..., description="Response code (0 for success)")
    message: str = Field(default="", description="Error message if code != 0")
    data: T | None = Field(None, description="Response data")

    @property
    def is_success(self) -> bool:
        """Check if the response indicates success."""
        return self.code == 0

    def raise_for_status(self):
        """Raise an exception if the response indicates an error."""
        from .exceptions import RagFlowAPIError

        if not self.is_success:
            raise RagFlowAPIError(
                message=self.message or f"API error (code {self.code})",
                error_code=str(self.code),
                response_data=self.model_dump(),
            )


class Paginated(BaseModel, Generic[T]):
    """
    Generic paginated response.

    Used for list endpoints that return paginated results.
    """

    items: list[T] = Field(default_factory=list, description="List of items")
    total: int = Field(0, description="Total number of items")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(20, description="Number of items per page")

    @property
    def has_next(self) -> bool:
        """Check if there are more pages."""
        return self.page * self.page_size < self.total

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


# --- Completion Models ---


class ReferenceChunk(BaseModel):
    """Reference chunk from knowledge base."""

    id: str = Field(..., description="Chunk ID")
    content: str = Field(..., description="Chunk content")
    document_id: str = Field(..., description="Document ID")
    document_name: str = Field(..., description="Document name")
    dataset_id: str = Field(..., description="Dataset ID")
    image_id: str = Field(default="", description="Image ID if applicable")
    url: str | None = Field(None, description="URL if applicable")
    similarity: float = Field(..., description="Overall similarity score")
    vector_similarity: float = Field(default=0.0, description="Vector similarity score")
    term_similarity: float = Field(default=0.0, description="Term similarity score")
    doc_type: list[str] = Field(default_factory=list, description="Document types")
    positions: list[str] = Field(default_factory=list, description="Chunk positions")


class DocumentAggregation(BaseModel):
    """Document aggregation in reference."""

    doc_name: str = Field(..., alias="doc_name", description="Document name")
    doc_id: str = Field(..., alias="doc_id", description="Document ID")
    count: int = Field(..., description="Number of chunks from this document")


class CompletionReference(BaseModel):
    """Reference information in completion response."""

    total: int = Field(0, description="Total number of reference chunks")
    chunks: list[ReferenceChunk] = Field(
        default_factory=list, description="List of reference chunks"
    )
    doc_aggs: list[DocumentAggregation] = Field(
        default_factory=list, description="Document aggregations"
    )


class CompletionData(BaseModel):
    """Completion response data."""

    answer: str = Field(..., description="Generated answer")
    reference: CompletionReference | dict = Field(
        default_factory=dict, description="Reference information"
    )
    audio_binary: str | None = Field(None, description="Audio binary data if available")
    id: str | None = Field(None, description="Message ID")
    session_id: str = Field(..., description="Session ID")
    prompt: str | None = Field(None, description="Full prompt sent to LLM")
    created_at: float | None = Field(None, description="Creation timestamp")

    @field_validator("reference", mode="before")
    @classmethod
    def validate_reference(cls, v):
        """Convert empty dict to CompletionReference."""
        if isinstance(v, dict) and not v:
            return CompletionReference()
        if isinstance(v, dict):
            return CompletionReference(**v)
        return v


class CompletionResponse(BaseModel):
    """Complete completion API response."""

    code: int = Field(..., description="Response code")
    message: str = Field(default="", description="Error message if any")
    data: CompletionData | bool = Field(..., description="Completion data or boolean")

    @property
    def is_success(self) -> bool:
        """Check if response indicates success."""
        return self.code == 0

    @property
    def is_final(self) -> bool:
        """Check if this is the final message in a stream."""
        return isinstance(self.data, bool) and self.data is True


class CompletionStreamEvent(BaseModel):
    """
    Streaming completion event.

    In streaming mode, each chunk is prefixed with "data:" and contains
    a JSON object. The last event has data=true to indicate completion.
    """

    code: int = Field(..., description="Response code")
    message: str = Field(default="", description="Error message if any")
    data: CompletionData | bool = Field(..., description="Partial or final data")

    @property
    def is_success(self) -> bool:
        """Check if event indicates success."""
        return self.code == 0

    @property
    def is_final(self) -> bool:
        """Check if this is the final event in the stream."""
        return isinstance(self.data, bool) and self.data is True

    @property
    def answer(self) -> str:
        """Get answer from event data."""
        if isinstance(self.data, CompletionData):
            return self.data.answer
        return ""


# --- Session Models ---


class ChatSession(BaseModel):
    """Chat session entity."""

    id: str = Field(..., description="Session ID")
    name: str = Field(..., description="Session name")
    user_id: str | None = Field(None, description="User ID if provided")
    chat_id: str | None = Field(None, description="Associated chat ID")
    create_time: int | None = Field(None, description="Creation timestamp (ms)")
    create_date: str | None = Field(None, description="Creation date string")
    update_time: int | None = Field(None, description="Update timestamp (ms)")
    update_date: str | None = Field(None, description="Update date string")


class SessionListData(BaseModel):
    """Session list response data."""

    sessions: list[ChatSession] = Field(
        default_factory=list, description="List of sessions"
    )
    total: int = Field(0, description="Total number of sessions")


# --- Chunk Models ---


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
    positions: list[str] = Field(default_factory=list, description="Chunk positions")
    available: bool = Field(True, description="Whether chunk is available")

    # Optional fields that may be present in search results
    similarity: float | None = Field(None, description="Similarity score if from search")
    vector_similarity: float | None = Field(
        None, description="Vector similarity if from search"
    )
    term_similarity: float | None = Field(
        None, description="Term similarity if from search"
    )


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


# --- Dataset Models (Placeholders for Phase 3) ---


class Dataset(BaseModel):
    """Dataset entity (placeholder for SDK replacement)."""

    id: str = Field(..., description="Dataset ID")
    name: str = Field(..., description="Dataset name")
    description: str = Field(default="", description="Dataset description")
    language: str = Field(default="English", description="Dataset language")
    embedding_model: str | None = Field(None, description="Embedding model used")
    chunk_method: str = Field(default="naive", description="Chunking method")
    permission: str = Field(default="me", description="Permission level")
    document_count: int = Field(0, description="Number of documents")
    chunk_count: int = Field(0, description="Number of chunks")
    create_time: int | None = Field(None, description="Creation timestamp (ms)")
    update_time: int | None = Field(None, description="Update timestamp (ms)")
    created_by: str | None = Field(None, description="Creator user ID")
    tenant_id: str | None = Field(None, description="Tenant ID")


# --- Document Models (Placeholders for Phase 3) ---


class Document(BaseModel):
    """Document entity (placeholder for SDK replacement)."""

    id: str = Field(..., description="Document ID")
    name: str = Field(..., description="Document name")
    dataset_id: str = Field(..., description="Associated dataset ID")
    location: str = Field(..., description="Document location/path")
    size: int = Field(..., description="Document size in bytes")
    type: str = Field(..., description="Document type")
    source_type: str = Field(default="local", description="Source type")
    chunk_count: int = Field(0, description="Number of chunks")
    status: str = Field(..., description="Processing status")
    progress: float = Field(0.0, description="Processing progress (0-1)")
    progress_msg: str = Field(default="", description="Progress message")
    create_time: int | None = Field(None, description="Creation timestamp (ms)")
    update_time: int | None = Field(None, description="Update timestamp (ms)")


class DocumentUploadResponse(BaseModel):
    """Response from document upload."""

    document_ids: list[str] = Field(
        default_factory=list, description="List of uploaded document IDs"
    )


# --- Chat Models (Placeholders for Phase 3) ---


class Chat(BaseModel):
    """Chat assistant entity (placeholder for SDK replacement)."""

    id: str = Field(..., description="Chat ID")
    name: str = Field(..., description="Chat name")
    description: str = Field(default="", description="Chat description")
    language: str = Field(default="English", description="Chat language")
    dataset_ids: list[str] = Field(
        default_factory=list, description="Associated dataset IDs"
    )
    llm_id: str | None = Field(None, description="LLM model ID")
    prompt: str = Field(default="", description="System prompt")
    create_time: int | None = Field(None, description="Creation timestamp (ms)")
    update_time: int | None = Field(None, description="Update timestamp (ms)")
    created_by: str | None = Field(None, description="Creator user ID")


# --- Related Questions Models ---


class RelatedQuestionsData(BaseModel):
    """Related questions response data."""

    questions: list[str] = Field(
        default_factory=list, description="List of related questions"
    )
