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
        )
    )
    value: str = Field(..., description="Value to compare against")


class MetadataFilter(BaseModel):
    """
    Container for metadata filter conditions.

    Used to filter chunks based on metadata field values.
    All conditions in the list are applied (AND logic).
    """

    conditions: list[MetadataCondition] = Field(
        default_factory=list,
        description="List of metadata filter conditions"
    )


class RetrievalResponse(BaseModel):
    """
    Response model for chunk retrieval API.

    Contains retrieved chunks with similarity scores, document aggregations,
    and total result count.
    """

    chunks: list[ChunkResponse] = Field(
        default_factory=list,
        description="Retrieved chunks with similarity scores"
    )
    doc_aggs: list[DocumentAggregation] = Field(
        default_factory=list,
        description="Document aggregations showing chunk count per document"
    )
    total: int = Field(
        default=0,
        description="Total number of matching chunks"
    )
