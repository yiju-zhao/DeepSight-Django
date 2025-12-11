import logging
from typing import Any

from ..exceptions import (
    RagFlowDocumentError,
    RagFlowConfigurationError,
    RagFlowAPIError,
)
from ..models import (
    APIResponse,
    Chunk,
    ChunkListData,
    ChunkResponse,
    MetadataFilter,
    Paginated,
    RetrievalResponse,
    DocumentAggregation,
)

logger = logging.getLogger(__name__)

class RagflowChunkService:
    """
    Service for RAGFlow chunk and retrieval operations.
    """

    def __init__(self, http_client):
        self.http_client = http_client

    def list_chunks(
        self,
        dataset_id: str,
        document_id: str,
        keywords: str = None,
        page: int = 1,
        page_size: int = 1024,
        chunk_id: str = None,
    ) -> Paginated[Chunk]:
        """
        List chunks in a document.

        Args:
            dataset_id: Dataset ID
            document_id: Document ID
            keywords: Optional keywords to filter chunks
            page: Page number (1-indexed)
            page_size: Number of chunks per page (default: 1024)
            chunk_id: Optional specific chunk ID to retrieve

        Returns:
            Paginated[Chunk] object

        Raises:
            RagFlowDocumentError: If request fails
        """
        try:
            logger.info(
                f"Listing chunks for document {document_id} in dataset {dataset_id}"
            )

            path = f"/api/v1/datasets/{dataset_id}/documents/{document_id}/chunks"
            params = {
                "page": page,
                "page_size": page_size,
            }

            if keywords:
                params["keywords"] = keywords
            if chunk_id:
                params["id"] = chunk_id

            response = self.http_client.get(path, params=params)
            api_response = APIResponse[ChunkListData](**response.json())
            api_response.raise_for_status()

            data = api_response.data
            chunks = data.chunks if data else []
            total = data.total if data else 0

            logger.info(f"Found {len(chunks)} chunks (total: {total})")

            return Paginated[Chunk](
                items=chunks,
                total=total,
                page=page,
                page_size=page_size,
            )

        except Exception as e:
            logger.error(f"Failed to list chunks for document {document_id}: {e}")
            raise RagFlowDocumentError(
                f"Failed to list chunks: {e}",
                document_id=document_id,
                dataset_id=dataset_id,
                details={"error": str(e)},
            ) from e

    def retrieve_chunks(
        self,
        question: str,
        dataset_ids: list[str] | None = None,
        document_ids: list[str] | None = None,
        page: int = 1,
        page_size: int = 30,
        similarity_threshold: float = 0.2,
        vector_similarity_weight: float = 0.3,
        top_k: int = 1024,
        rerank_id: str | None = None,
        keyword: bool = False,
        highlight: bool = False,
        cross_languages: list[str] | None = None,
        metadata_condition: MetadataFilter | None = None,
    ) -> RetrievalResponse:
        """
        Retrieve chunks from specified datasets or documents using semantic search.

        This method performs semantic search across RAGFlow datasets/documents,
        combining vector similarity with term matching for optimal retrieval.

        Args:
            question: User query or search keywords
            dataset_ids: List of dataset IDs to search (requires this or document_ids)
            document_ids: List of document IDs to search (requires this or dataset_ids)
            page: Page number for pagination (default: 1)
            page_size: Number of results per page (default: 30)
            similarity_threshold: Minimum similarity score to include (default: 0.2)
            vector_similarity_weight: Weight for vector cosine similarity (default: 0.3)
                Term similarity weight = 1 - vector_similarity_weight
            top_k: Number of chunks for vector computation (default: 1024)
            rerank_id: Optional rerank model ID for re-ranking results
            keyword: Enable keyword-based matching (default: False)
            highlight: Enable highlighting of matched terms in results (default: False)
            cross_languages: Languages for query translation and cross-lingual retrieval
            metadata_condition: Optional metadata filters for chunk filtering

        Returns:
            RetrievalResponse with chunks, document aggregations, and total count

        Raises:
            RagFlowConfigurationError: If neither dataset_ids nor document_ids provided
            RagFlowAPIError: If the API request fails

        Example:
            >>> result = service.retrieve_chunks(
            ...     question="What is RAGFlow?",
            ...     dataset_ids=["dataset_123"],
            ...     page_size=10,
            ...     highlight=True
            ... )
            >>> for chunk in result.chunks:
            ...     print(f"Content: {chunk.content}")
            ...     print(f"Similarity: {chunk.similarity}")
        """
        # Validate required parameters
        if not dataset_ids and not document_ids:
            raise RagFlowConfigurationError(
                "Either dataset_ids or document_ids must be provided",
                details={"question": question}
            )

        try:
            # Build request payload
            payload: dict[str, Any] = {"question": question}

            # Add optional fields only if provided
            if dataset_ids:
                payload["dataset_ids"] = dataset_ids
            if document_ids:
                payload["document_ids"] = document_ids

            # Pagination
            payload["page"] = page
            payload["page_size"] = page_size

            # Search parameters
            payload["similarity_threshold"] = similarity_threshold
            payload["vector_similarity_weight"] = vector_similarity_weight
            payload["top_k"] = top_k

            # Optional features
            if rerank_id:
                payload["rerank_id"] = rerank_id
            payload["keyword"] = keyword
            payload["highlight"] = highlight

            if cross_languages:
                payload["cross_languages"] = cross_languages

            if metadata_condition:
                payload["metadata_condition"] = metadata_condition.model_dump(
                    exclude_none=True
                )

            # Log retrieval request
            logger.info(
                f"Retrieving chunks for question: '{question[:50]}...' "
                f"from {len(dataset_ids or [])} datasets, "
                f"{len(document_ids or [])} documents"
            )

            # Make API request
            response = self.http_client.post(
                "/api/v1/retrieval",
                json_data=payload
            )

            # Parse response
            api_response = APIResponse[dict](**response.json())
            api_response.raise_for_status()

            data = api_response.data

            # Parse chunks and aggregations
            chunks = [ChunkResponse(**chunk) for chunk in data.get("chunks", [])]
            doc_aggs = [
                {"doc_id": agg["doc_id"], "doc_name": agg["doc_name"], "count": agg["count"]}
                for agg in data.get("doc_aggs", [])
            ]
            total = data.get("total", 0)

            logger.info(
                f"Successfully retrieved {len(chunks)} chunks from {len(doc_aggs)} documents "
                f"(total: {total})"
            )

            return RetrievalResponse(
                chunks=chunks,
                doc_aggs=[DocumentAggregation(**agg) for agg in doc_aggs],
                total=total
            )

        except RagFlowConfigurationError:
            # Re-raise configuration errors as-is
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve chunks: {e}")
            raise RagFlowAPIError(
                f"Chunk retrieval failed: {str(e)}",
                details={
                    "question": question[:100],
                    "dataset_ids": dataset_ids,
                    "document_ids": document_ids,
                    "page": page
                }
            ) from e
