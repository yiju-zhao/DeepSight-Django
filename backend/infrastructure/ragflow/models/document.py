from typing import Any
from pydantic import BaseModel, Field


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
