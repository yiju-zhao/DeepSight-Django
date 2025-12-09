"""
Retrieval service for RAGFlow knowledge base access.

Provides high-level retrieval operations with retry logic, parameter validation,
and deduplication. Wraps RAGFlow's /api/v1/retrieval endpoint.
"""

import logging
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from backend.infrastructure.ragflow.service import RagflowService
from backend.infrastructure.ragflow.exceptions import (
    RagFlowAPIError,
    RagFlowTimeoutError,
    RagFlowRateLimitError,
)
from backend.notebooks.models.retrieval import RetrievalChunk, RetrievalResponse, DocAgg

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    Service for retrieving knowledge from RAGFlow datasets.

    Handles communication with RAGFlow's retrieval API including:
    - Parameter validation and clamping
    - Retry logic with exponential backoff
    - Response parsing and validation
    - Chunk deduplication
    """

    # Default parameters
    DEFAULT_SIMILARITY_THRESHOLD = 0.2
    DEFAULT_TOP_K = 6
    DEFAULT_PAGE_SIZE = 30

    # Parameter limits
    MAX_TOP_K = 1024
    MAX_PAGE_SIZE = 30

    def __init__(self, ragflow_service: RagflowService):
        """
        Initialize RetrievalService.

        Args:
            ragflow_service: RagflowService instance for API communication
        """
        self.ragflow_service = ragflow_service

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RagFlowTimeoutError, RagFlowRateLimitError)),
        reraise=True,
    )
    def retrieve_chunks(
        self,
        question: str,
        dataset_ids: list[str],
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        top_k: int = DEFAULT_TOP_K,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> RetrievalResponse:
        """
        Retrieve relevant chunks from RAGFlow datasets.

        Args:
            question: User query or search question
            dataset_ids: List of dataset IDs to search
            similarity_threshold: Minimum similarity score (0.0-1.0)
            top_k: Maximum chunks to consider for ranking
            page_size: Results per page

        Returns:
            RetrievalResponse with validated and deduplicated chunks

        Raises:
            ValueError: If parameters are invalid or API returns error
            RagFlowAPIError: If API request fails
            RagFlowTimeoutError: If request times out (will retry)
            RagFlowRateLimitError: If rate limited (will retry)
        """
        # Validate required parameters
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        if not dataset_ids:
            raise ValueError("At least one dataset_id is required")

        # Clamp parameters to safe ranges
        similarity_threshold = max(0.0, min(1.0, similarity_threshold))
        top_k = min(self.MAX_TOP_K, max(1, top_k))
        page_size = min(self.MAX_PAGE_SIZE, max(1, page_size))

        logger.info(
            f"Retrieving chunks: question='{question[:100]}...', "
            f"datasets={len(dataset_ids)}, top_k={top_k}, "
            f"threshold={similarity_threshold}"
        )

        # Build request payload
        payload = {
            "question": question.strip(),
            "dataset_ids": dataset_ids,
            "page": 1,
            "page_size": page_size,
            "similarity_threshold": similarity_threshold,
            "top_k": top_k,
            "keyword": False,
            "highlight": False,
        }

        # Call RAGFlow retrieval API
        try:
            response = self.ragflow_service.http_client.post(
                "/api/v1/retrieval", json_data=payload
            )
        except Exception as e:
            logger.error(f"Retrieval API request failed: {e}")
            raise

        # Validate HTTP response
        if response.status_code != 200:
            logger.error(
                f"Retrieval API returned status {response.status_code}: {response.text}"
            )
            raise RagFlowAPIError(
                f"Retrieval failed with status {response.status_code}",
                status_code=response.status_code,
                response_data=response.text,
            )

        # Parse JSON response
        try:
            data = response.json()
        except Exception as e:
            logger.error(f"Failed to parse retrieval response: {e}")
            raise ValueError(f"Invalid JSON response from retrieval API: {e}")

        # Validate API response code
        if data.get("code") != 0:
            error_message = data.get("message", "Unknown error")
            logger.error(f"Retrieval API error: {error_message}")
            raise ValueError(f"Retrieval API error: {error_message}")

        # Parse data section
        if "data" not in data:
            logger.error("Missing 'data' field in retrieval response")
            raise ValueError("Invalid retrieval response: missing 'data' field")

        # Create RetrievalResponse from data
        try:
            result = RetrievalResponse(**data["data"])
        except Exception as e:
            logger.error(f"Failed to parse retrieval data: {e}")
            raise ValueError(f"Failed to parse retrieval response: {e}")

        # Deduplicate chunks
        result.chunks = self._deduplicate_chunks(result.chunks)

        logger.info(
            f"Retrieved {len(result.chunks)} unique chunks "
            f"(total: {result.total}, docs: {len(result.doc_aggs)})"
        )

        return result

    def _deduplicate_chunks(self, chunks: list[RetrievalChunk]) -> list[RetrievalChunk]:
        """
        Deduplicate chunks by ID, keeping highest similarity.

        Args:
            chunks: List of chunks that may contain duplicates

        Returns:
            Deduplicated list of chunks
        """
        if not chunks:
            return []

        seen = {}
        for chunk in chunks:
            if chunk.id not in seen or chunk.similarity > seen[chunk.id].similarity:
                seen[chunk.id] = chunk

        deduplicated = list(seen.values())

        if len(deduplicated) < len(chunks):
            logger.debug(
                f"Deduplicated {len(chunks)} chunks to {len(deduplicated)} unique"
            )

        return deduplicated

    def _truncate_chunk_content(self, chunk: RetrievalChunk, max_length: int = 1000) -> str:
        """
        Truncate chunk content to maximum length.

        Args:
            chunk: Chunk to truncate
            max_length: Maximum content length

        Returns:
            Truncated content with ellipsis if needed
        """
        if len(chunk.content) <= max_length:
            return chunk.content

        return chunk.content[:max_length] + "..."

    def format_chunks_for_agent(
        self, chunks: list[RetrievalChunk], max_chunks: Optional[int] = None
    ) -> str:
        """
        Format chunks as structured text for agent consumption.

        Args:
            chunks: List of chunks to format
            max_chunks: Maximum number of chunks to include

        Returns:
            Formatted string with numbered chunks
        """
        if not chunks:
            return "No relevant information found in the knowledge base."

        chunks_to_format = chunks[:max_chunks] if max_chunks else chunks

        output = f"Found {len(chunks_to_format)} relevant passages:\n\n"

        for i, chunk in enumerate(chunks_to_format, 1):
            # Truncate content to 500 chars for agent readability
            content = self._truncate_chunk_content(chunk, max_length=500)

            output += f"[{i}] {chunk.document_name}\n"
            output += f"{content}\n"
            output += f"Similarity: {chunk.similarity:.2f}\n\n"

        return output
