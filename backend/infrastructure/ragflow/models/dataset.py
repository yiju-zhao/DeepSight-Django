from pydantic import BaseModel, Field


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
