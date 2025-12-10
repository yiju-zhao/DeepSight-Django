"""
RAGFlow Pydantic models for API responses and entities.

Provides type-safe models for all RAGFlow API interactions.
"""

from __future__ import annotations

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

# NOTE: ReferenceChunk is now a forward reference to ChunkResponse
# defined below. This maintains backward compatibility with existing code
# while using the unified chunk model.
# Will be defined as: ReferenceChunk = ChunkResponse (after ChunkResponse definition)


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

    @field_validator("data", mode="before")
    @classmethod
    def validate_data(cls, v):
        """Handle various data formats from the API."""
        # If it's already a bool, return it
        if isinstance(v, bool):
            return v
        # If it's a dict, try to parse as CompletionData
        if isinstance(v, dict):
            try:
                return CompletionData(**v)
            except Exception:
                # If parsing fails, check if this is meant to be a final signal
                # Some APIs might send the final complete data as a dict
                # In that case, we'll try to parse it anyway and let it through
                raise
        return v

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
    """Document entity."""

    id: str = Field(..., description="Document ID")
    name: str = Field(..., description="Document name")
    location: str = Field(..., description="Document location/path")
    size: int = Field(default=0, description="Document size in bytes")
    type: str = Field(default="", description="Document type")
    chunk_count: int = Field(
        default=0, alias="chunk_count", description="Number of chunks"
    )

    # Dataset references (API uses both dataset_id and knowledgebase_id)
    dataset_id: str | None = Field(None, alias="dataset_id", description="Dataset ID")
    knowledgebase_id: str | None = Field(
        None, alias="knowledgebase_id", description="Knowledge base ID (alias)"
    )

    # Processing status and progress
    run: str | None = Field(
        None, description="Processing status (UNSTART, RUNNING, DONE, etc.)"
    )
    status: str | None = Field(None, description="Processing status (alias for run)")
    progress: float = Field(default=0.0, description="Processing progress (0-1)")
    progress_msg: str = Field(
        default="", alias="progress_msg", description="Progress message"
    )

    # Configuration
    chunk_method: str | None = Field(
        None, alias="chunk_method", description="Chunking method"
    )
    parser_config: dict[str, Any] | None = Field(
        None, alias="parser_config", description="Parser configuration"
    )

    # Metadata
    source_type: str = Field(default="local", description="Source type")
    created_by: str | None = Field(
        None, alias="created_by", description="Creator user ID"
    )
    thumbnail: str | None = Field(None, description="Thumbnail URL")

    # Timestamps
    create_time: int | None = Field(
        None, alias="create_time", description="Creation timestamp (ms)"
    )
    create_date: str | None = Field(
        None, alias="create_date", description="Creation date string"
    )
    update_time: int | None = Field(
        None, alias="update_time", description="Update timestamp (ms)"
    )
    process_begin_at: str | None = Field(
        None, alias="process_begin_at", description="Processing start time (GMT string)"
    )
    process_duration: float | None = Field(
        None, alias="process_duration", description="Processing duration (seconds)"
    )

    model_config = {"populate_by_name": True}

    @property
    def processing_status(self) -> str:
        """Get processing status (prefers run field, falls back to status)."""
        return self.run or self.status or "UNKNOWN"

    @property
    def get_dataset_id(self) -> str | None:
        """Get dataset ID (handles both dataset_id and knowledgebase_id fields)."""
        return self.dataset_id or self.knowledgebase_id


class DocumentUploadResponse(BaseModel):
    """Response from document upload."""

    document_ids: list[str] = Field(
        default_factory=list, description="List of uploaded document IDs"
    )


# --- Chat Models ---


class LLMConfig(BaseModel):
    """LLM configuration for chat assistant."""

    model_name: str | None = Field(
        None, alias="model_name", description="LLM model name"
    )
    temperature: float = Field(default=0.1, description="Temperature for LLM")
    top_p: float = Field(default=0.3, alias="top_p", description="Top-p sampling")
    presence_penalty: float = Field(
        default=0.4, alias="presence_penalty", description="Presence penalty"
    )
    frequency_penalty: float = Field(
        default=0.7, alias="frequency_penalty", description="Frequency penalty"
    )
    max_tokens: int | None = Field(
        None, alias="max_tokens", description="Maximum tokens"
    )

    model_config = {"populate_by_name": True}


class PromptVariable(BaseModel):
    """Variable in prompt configuration."""

    key: str = Field(..., description="Variable key")
    optional: bool = Field(default=True, description="Whether variable is optional")


class PromptConfig(BaseModel):
    """Prompt configuration for chat assistant."""

    similarity_threshold: float = Field(
        default=0.2, alias="similarity_threshold", description="Similarity threshold"
    )
    keywords_similarity_weight: float = Field(
        default=0.7,
        alias="keywords_similarity_weight",
        description="Keywords similarity weight",
    )
    top_n: int = Field(default=6, alias="top_n", description="Number of top chunks")
    variables: list[PromptVariable] = Field(
        default_factory=lambda: [{"key": "knowledge", "optional": True}],
        description="Prompt variables",
    )
    rerank_model: str = Field(
        default="", alias="rerank_model", description="Rerank model name"
    )
    empty_response: str = Field(
        default="", alias="empty_response", description="Response when no results"
    )
    opener: str = Field(
        default="Hi! I am your assistant, can I help you?",
        description="Opening greeting",
    )
    show_quote: bool = Field(
        default=True, alias="show_quote", description="Show quote sources"
    )
    prompt: str = Field(default="", description="Prompt text content")
    top_k: int = Field(default=1024, alias="top_k", description="Top-k for reranking")

    model_config = {"populate_by_name": True}


class Chat(BaseModel):
    """Chat assistant entity."""

    id: str = Field(..., description="Chat ID")
    name: str = Field(..., description="Chat name")
    avatar: str = Field(default="", description="Avatar (base64 or URL)")
    description: str = Field(
        default="A helpful Assistant", description="Chat description"
    )
    language: str = Field(default="English", description="Chat language")

    # Dataset associations
    dataset_ids: list[str] = Field(
        default_factory=list, alias="dataset_ids", description="Associated dataset IDs"
    )
    knowledgebase_ids: list[str] | None = Field(
        None, alias="knowledgebase_ids", description="Knowledge base IDs (alias)"
    )

    # Configuration
    llm: LLMConfig | None = Field(None, description="LLM configuration")
    prompt: PromptConfig | None = Field(None, description="Prompt configuration")

    # Metadata
    do_refer: str = Field(default="1", alias="do_refer", description="Reference flag")
    prompt_type: str = Field(
        default="simple", alias="prompt_type", description="Prompt type"
    )
    status: str = Field(default="1", description="Chat status")
    top_k: int = Field(default=1024, alias="top_k", description="Top-k for retrieval")

    # User and tenant
    tenant_id: str | None = Field(None, alias="tenant_id", description="Tenant ID")
    created_by: str | None = Field(
        None, alias="created_by", description="Creator user ID"
    )

    # Timestamps
    create_time: int | None = Field(
        None, alias="create_time", description="Creation timestamp (ms)"
    )
    create_date: str | None = Field(
        None, alias="create_date", description="Creation date string"
    )
    update_time: int | None = Field(
        None, alias="update_time", description="Update timestamp (ms)"
    )
    update_date: str | None = Field(
        None, alias="update_date", description="Update date string"
    )

    model_config = {"populate_by_name": True}


# --- Related Questions ---
# Note: The related_questions API returns a list[str] directly in the 'data' field,
# not wrapped in a model object. Use APIResponse[list[str]] to parse responses.
