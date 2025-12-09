"""
Unit tests for RetrievalService.

Tests retrieval logic, parameter validation, deduplication, and error handling.
"""

import pytest
from unittest.mock import Mock, patch
from unittest import mock

from notebooks.services.retrieval_service import RetrievalService
from notebooks.models.retrieval import RetrievalChunk, RetrievalResponse, DocAgg
from infrastructure.ragflow.exceptions import RagFlowAPIError


@pytest.fixture
def mock_ragflow_service():
    """Create a mock RagflowService."""
    service = Mock()
    service.http_client = Mock()
    return service


@pytest.fixture
def sample_retrieval_response():
    """Sample retrieval API response."""
    return {
        "code": 0,
        "data": {
            "chunks": [
                {
                    "id": "chunk1",
                    "content": "This is test content about Python programming.",
                    "document_id": "doc1",
                    "document_keyword": "Python Guide.pdf",
                    "kb_id": "kb1",
                    "similarity": 0.95,
                    "vector_similarity": 0.92,
                    "term_similarity": 0.98,
                    "positions": ["page_1"],
                    "important_keywords": ["python", "programming"],
                    "image_id": "",
                },
                {
                    "id": "chunk2",
                    "content": "Advanced Python techniques for data analysis.",
                    "document_id": "doc2",
                    "document_keyword": "Data Analysis.pdf",
                    "kb_id": "kb1",
                    "similarity": 0.88,
                    "vector_similarity": 0.85,
                    "term_similarity": 0.91,
                    "positions": ["page_3"],
                    "important_keywords": ["python", "data", "analysis"],
                    "image_id": "",
                },
            ],
            "doc_aggs": [
                {"doc_id": "doc1", "doc_name": "Python Guide.pdf", "count": 1},
                {"doc_id": "doc2", "doc_name": "Data Analysis.pdf", "count": 1},
            ],
            "total": 2,
        },
    }


class TestRetrievalService:
    """Tests for RetrievalService class."""

    def test_retrieve_chunks_success(self, mock_ragflow_service, sample_retrieval_response):
        """Test successful retrieval with valid response."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_retrieval_response
        mock_ragflow_service.http_client.post.return_value = mock_response

        # Create service and call
        service = RetrievalService(mock_ragflow_service)
        result = service.retrieve_chunks("What is Python?", ["kb1"])

        # Assertions
        assert isinstance(result, RetrievalResponse)
        assert len(result.chunks) == 2
        assert result.total == 2
        assert len(result.doc_aggs) == 2

        # Verify first chunk
        assert result.chunks[0].id == "chunk1"
        assert result.chunks[0].content == "This is test content about Python programming."
        assert result.chunks[0].document_name == "Python Guide.pdf"
        assert result.chunks[0].similarity == 0.95

        # Verify API call
        mock_ragflow_service.http_client.post.assert_called_once()
        call_args = mock_ragflow_service.http_client.post.call_args
        assert call_args[0][0] == "/api/v1/retrieval"
        assert "question" in call_args[1]["json_data"]
        assert call_args[1]["json_data"]["dataset_ids"] == ["kb1"]

    def test_retrieve_chunks_empty_result(self, mock_ragflow_service):
        """Test retrieval with no results."""
        # Setup mock response with empty chunks
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {"chunks": [], "doc_aggs": [], "total": 0},
        }
        mock_ragflow_service.http_client.post.return_value = mock_response

        # Create service and call
        service = RetrievalService(mock_ragflow_service)
        result = service.retrieve_chunks("Unknown topic", ["kb1"])

        # Assertions
        assert isinstance(result, RetrievalResponse)
        assert len(result.chunks) == 0
        assert result.total == 0

    def test_parameter_clamping(self, mock_ragflow_service, sample_retrieval_response):
        """Test that out-of-range parameters are clamped."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_retrieval_response
        mock_ragflow_service.http_client.post.return_value = mock_response

        # Create service
        service = RetrievalService(mock_ragflow_service)

        # Call with out-of-range parameters
        service.retrieve_chunks(
            "test question",
            ["kb1"],
            similarity_threshold=1.5,  # > 1.0
            top_k=2000,  # > 1024
            page_size=100,  # > 30
        )

        # Verify clamped values in API call
        call_args = mock_ragflow_service.http_client.post.call_args
        payload = call_args[1]["json_data"]

        assert payload["similarity_threshold"] == 1.0  # Clamped to 1.0
        assert payload["top_k"] == 1024  # Clamped to 1024
        assert payload["page_size"] == 30  # Clamped to 30

    def test_parameter_validation_empty_question(self, mock_ragflow_service):
        """Test that empty question raises ValueError."""
        service = RetrievalService(mock_ragflow_service)

        with pytest.raises(ValueError, match="Question cannot be empty"):
            service.retrieve_chunks("", ["kb1"])

        with pytest.raises(ValueError, match="Question cannot be empty"):
            service.retrieve_chunks("   ", ["kb1"])

    def test_parameter_validation_empty_datasets(self, mock_ragflow_service):
        """Test that empty dataset_ids raises ValueError."""
        service = RetrievalService(mock_ragflow_service)

        with pytest.raises(ValueError, match="At least one dataset_id is required"):
            service.retrieve_chunks("test question", [])

    def test_api_error_response(self, mock_ragflow_service):
        """Test handling of API error response."""
        # Setup mock response with error code
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 102, "message": "Dataset not found"}
        mock_ragflow_service.http_client.post.return_value = mock_response

        # Create service
        service = RetrievalService(mock_ragflow_service)

        # Should raise ValueError with error message
        with pytest.raises(ValueError, match="Dataset not found"):
            service.retrieve_chunks("test", ["invalid_kb"])

    def test_http_error_response(self, mock_ragflow_service):
        """Test handling of HTTP error status."""
        # Setup mock response with error status
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_ragflow_service.http_client.post.return_value = mock_response

        # Create service
        service = RetrievalService(mock_ragflow_service)

        # Should raise RagFlowAPIError
        with pytest.raises(RagFlowAPIError, match="Retrieval failed with status 500"):
            service.retrieve_chunks("test", ["kb1"])

    def test_deduplication(self, mock_ragflow_service):
        """Test chunk deduplication by ID."""
        # Setup mock response with duplicate chunk IDs
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "chunks": [
                    {
                        "id": "chunk1",
                        "content": "First version",
                        "document_id": "doc1",
                        "document_keyword": "Doc1.pdf",
                        "kb_id": "kb1",
                        "similarity": 0.8,
                        "vector_similarity": 0.75,
                        "term_similarity": 0.85,
                    },
                    {
                        "id": "chunk1",  # Duplicate ID
                        "content": "Second version (higher similarity)",
                        "document_id": "doc1",
                        "document_keyword": "Doc1.pdf",
                        "kb_id": "kb1",
                        "similarity": 0.9,  # Higher similarity
                        "vector_similarity": 0.88,
                        "term_similarity": 0.92,
                    },
                    {
                        "id": "chunk2",
                        "content": "Different chunk",
                        "document_id": "doc2",
                        "document_keyword": "Doc2.pdf",
                        "kb_id": "kb1",
                        "similarity": 0.85,
                        "vector_similarity": 0.82,
                        "term_similarity": 0.88,
                    },
                ],
                "doc_aggs": [],
                "total": 3,
            },
        }
        mock_ragflow_service.http_client.post.return_value = mock_response

        # Create service and call
        service = RetrievalService(mock_ragflow_service)
        result = service.retrieve_chunks("test", ["kb1"])

        # Should deduplicate to 2 chunks, keeping higher similarity
        assert len(result.chunks) == 2

        # Find chunk1 (should be the one with higher similarity)
        chunk1 = next(c for c in result.chunks if c.id == "chunk1")
        assert chunk1.similarity == 0.9
        assert chunk1.content == "Second version (higher similarity)"

    def test_format_chunks_for_agent(self, mock_ragflow_service):
        """Test formatting chunks as text for agent."""
        # Create chunks
        chunks = [
            RetrievalChunk(
                id="1",
                content="Short content",
                document_id="doc1",
                document_name="Doc1.pdf",
                dataset_id="kb1",
                similarity=0.95,
                vector_similarity=0.92,
                term_similarity=0.98,
            ),
            RetrievalChunk(
                id="2",
                content="A" * 1000,  # Long content
                document_id="doc2",
                document_name="Doc2.pdf",
                dataset_id="kb1",
                similarity=0.88,
                vector_similarity=0.85,
                term_similarity=0.91,
            ),
        ]

        service = RetrievalService(mock_ragflow_service)
        formatted = service.format_chunks_for_agent(chunks)

        # Check format
        assert "Found 2 relevant passages" in formatted
        assert "[1] Doc1.pdf" in formatted
        assert "[2] Doc2.pdf" in formatted
        assert "Short content" in formatted
        assert "Similarity: 0.95" in formatted

        # Check truncation (long content should be truncated)
        assert formatted.count("...") >= 1

    def test_format_chunks_empty(self, mock_ragflow_service):
        """Test formatting with no chunks."""
        service = RetrievalService(mock_ragflow_service)
        formatted = service.format_chunks_for_agent([])

        assert "No relevant information found" in formatted

    def test_format_chunks_with_limit(self, mock_ragflow_service):
        """Test formatting with max_chunks limit."""
        chunks = [
            RetrievalChunk(
                id=str(i),
                content=f"Content {i}",
                document_id=f"doc{i}",
                document_name=f"Doc{i}.pdf",
                dataset_id="kb1",
                similarity=0.9 - i * 0.1,
                vector_similarity=0.85,
                term_similarity=0.9,
            )
            for i in range(5)
        ]

        service = RetrievalService(mock_ragflow_service)
        formatted = service.format_chunks_for_agent(chunks, max_chunks=2)

        # Should only include first 2
        assert "Found 2 relevant passages" in formatted
        assert "[1]" in formatted
        assert "[2]" in formatted
        assert "[3]" not in formatted
