from pydantic import BaseModel, Field
from .chunk import ChunkResponse
from .completion import DocumentAggregation


class MetadataCondition(BaseModel):
    """
    Metadata filter condition for chunk retrieval.

    Defines a single filtering condition for metadata fields.
    """

    name: str = Field(..., description="Metadata field name (e.g., 'author', 'url')")
    comparison_operator: str = Field(
        ...,
        description=(
            "Comparison operator. Valid values: 'contains', 'not contains', "
            "'start with', 'empty', 'not empty', '=', '≠', '>', '<', '≥', '≤'"
        ),
    )
    value: str = Field(..., description="Value to compare against")


class MetadataFilter(BaseModel):
    """
    Container for metadata filter conditions.

    Used to filter chunks based on metadata field values.
    All conditions in the list are applied (AND logic).
    """

    conditions: list[MetadataCondition] = Field(
        default_factory=list, description="List of metadata filter conditions"
    )


class RetrievalRequest(BaseModel):
    """
    Request model for chunk retrieval API.

    Defines parameters for semantic search across RAGFlow datasets/documents,
    combining vector similarity with term matching for optimal retrieval.
    """

    question: str = Field(..., description="User query or search keywords")
    dataset_ids: list[str] | None = Field(
        default=None,
        description="List of dataset IDs to search (requires this or document_ids)",
    )
    document_ids: list[str] | None = Field(
        default=None,
        description="List of document IDs to search (requires this or dataset_ids)",
    )
    page: int = Field(default=1, description="Page number for pagination")
    page_size: int = Field(default=30, description="Number of results per page")
    similarity_threshold: float = Field(
        default=0.2, description="Minimum similarity score to include"
    )
    vector_similarity_weight: float = Field(
        default=0.3,
        description="Weight for vector cosine similarity (term weight = 1 - this value)",
    )
    top_k: int = Field(
        default=1024, description="Number of chunks for vector computation"
    )
    rerank_id: str | None = Field(
        default=None, description="Optional rerank model ID for re-ranking results"
    )
    keyword: bool = Field(default=False, description="Enable keyword-based matching")
    highlight: bool = Field(
        default=False, description="Enable highlighting of matched terms in results"
    )
    cross_languages: list[str] | None = Field(
        default=None,
        description="Languages for query translation and cross-lingual retrieval",
    )
    metadata_condition: MetadataFilter | None = Field(
        default=None, description="Optional metadata filters for chunk filtering"
    )


class RetrievalResponse(BaseModel):
    """
    Response model for chunk retrieval API.

    Contains retrieved chunks with similarity scores, document aggregations,
    and total result count.
    """

    chunks: list[ChunkResponse] = Field(
        default_factory=list, description="Retrieved chunks with similarity scores"
    )
    doc_aggs: list[DocumentAggregation] = Field(
        default_factory=list,
        description="Document aggregations showing chunk count per document",
    )
    total: int = Field(default=0, description="Total number of matching chunks")
