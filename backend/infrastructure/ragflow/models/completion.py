from pydantic import BaseModel, Field, field_validator
from .chunk import ReferenceChunk


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
