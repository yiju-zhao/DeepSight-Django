"""
Tests for RAGFlow Pydantic models.
"""

import pytest
from pydantic import ValidationError

from infrastructure.ragflow.exceptions import RagFlowAPIError
from infrastructure.ragflow.models import (
    APIResponse,
    ChatSession,
    Chunk,
    ChunkListData,
    CompletionData,
    CompletionReference,
    CompletionResponse,
    CompletionStreamEvent,
    Paginated,
    ReferenceChunk,
    RelatedQuestionsData,
)


class TestAPIResponse:
    """Test APIResponse model."""

    def test_success_response(self):
        """Test successful API response."""
        response = APIResponse[dict](code=0, message="", data={"key": "value"})
        assert response.is_success
        assert response.data == {"key": "value"}

    def test_error_response(self):
        """Test error API response."""
        response = APIResponse[dict](code=102, message="Invalid input", data=None)
        assert not response.is_success
        assert response.message == "Invalid input"

    def test_raise_for_status_success(self):
        """Test raise_for_status on success."""
        response = APIResponse[dict](code=0, data={"key": "value"})
        response.raise_for_status()  # Should not raise

    def test_raise_for_status_error(self):
        """Test raise_for_status on error."""
        response = APIResponse[dict](code=102, message="Invalid input")
        with pytest.raises(RagFlowAPIError) as exc_info:
            response.raise_for_status()
        assert "Invalid input" in str(exc_info.value)


class TestPaginated:
    """Test Paginated model."""

    def test_empty_paginated(self):
        """Test empty paginated response."""
        paginated = Paginated[dict](items=[], total=0)
        assert paginated.items == []
        assert paginated.total == 0
        assert not paginated.has_next
        assert paginated.total_pages == 0

    def test_paginated_with_items(self):
        """Test paginated response with items."""
        items = [{"id": "1"}, {"id": "2"}]
        paginated = Paginated[dict](items=items, total=10, page=1, page_size=2)
        assert len(paginated.items) == 2
        assert paginated.total == 10
        assert paginated.has_next
        assert paginated.total_pages == 5

    def test_paginated_last_page(self):
        """Test paginated response on last page."""
        paginated = Paginated[dict](items=[{"id": "1"}], total=5, page=5, page_size=1)
        assert not paginated.has_next


class TestCompletionModels:
    """Test completion-related models."""

    def test_reference_chunk(self):
        """Test ReferenceChunk model."""
        chunk = ReferenceChunk(
            id="chunk123",
            content="Test content",
            document_id="doc123",
            document_name="test.txt",
            dataset_id="ds123",
            similarity=0.85,
        )
        assert chunk.id == "chunk123"
        assert chunk.similarity == 0.85

    def test_completion_reference(self):
        """Test CompletionReference model."""
        ref = CompletionReference(total=0, chunks=[], doc_aggs=[])
        assert ref.total == 0
        assert ref.chunks == []

    def test_completion_data(self):
        """Test CompletionData model."""
        data = CompletionData(
            answer="Test answer",
            session_id="sess123",
            reference={},
        )
        assert data.answer == "Test answer"
        assert isinstance(data.reference, CompletionReference)

    def test_completion_response(self):
        """Test CompletionResponse model."""
        response = CompletionResponse(
            code=0,
            data=CompletionData(answer="Test", session_id="sess123", reference={}),
        )
        assert response.is_success
        assert not response.is_final

    def test_completion_response_final(self):
        """Test final CompletionResponse."""
        response = CompletionResponse(code=0, data=True)
        assert response.is_final

    def test_completion_stream_event(self):
        """Test CompletionStreamEvent model."""
        event = CompletionStreamEvent(
            code=0,
            data=CompletionData(answer="Test", session_id="sess123", reference={}),
        )
        assert event.is_success
        assert event.answer == "Test"

    def test_completion_stream_event_final(self):
        """Test final CompletionStreamEvent."""
        event = CompletionStreamEvent(code=0, data=True)
        assert event.is_final
        assert event.answer == ""


class TestChatSession:
    """Test ChatSession model."""

    def test_chat_session_basic(self):
        """Test basic ChatSession."""
        session = ChatSession(id="sess123", name="Test Session")
        assert session.id == "sess123"
        assert session.name == "Test Session"
        assert session.user_id is None

    def test_chat_session_with_timestamps(self):
        """Test ChatSession with timestamps."""
        session = ChatSession(
            id="sess123",
            name="Test",
            create_time=1234567890,
            create_date="2024-01-01",
        )
        assert session.create_time == 1234567890


class TestChunkModels:
    """Test chunk-related models."""

    def test_chunk_basic(self):
        """Test basic Chunk model."""
        chunk = Chunk(
            id="chunk123",
            content="Test content",
            document_id="doc123",
        )
        assert chunk.id == "chunk123"
        assert chunk.content == "Test content"
        assert chunk.available

    def test_chunk_with_similarity(self):
        """Test Chunk with similarity scores."""
        chunk = Chunk(
            id="chunk123",
            content="Test",
            document_id="doc123",
            similarity=0.85,
            vector_similarity=0.9,
            term_similarity=0.8,
        )
        assert chunk.similarity == 0.85

    def test_chunk_list_data(self):
        """Test ChunkListData model."""
        data = ChunkListData(
            chunks=[
                Chunk(id="c1", content="Test", document_id="doc123"),
            ],
            total=1,
        )
        assert len(data.chunks) == 1
        assert data.total == 1


class TestRelatedQuestions:
    """Test RelatedQuestionsData model."""

    def test_related_questions(self):
        """Test RelatedQuestionsData model."""
        data = RelatedQuestionsData(
            questions=["Question 1?", "Question 2?", "Question 3?"]
        )
        assert len(data.questions) == 3

    def test_related_questions_empty(self):
        """Test empty RelatedQuestionsData."""
        data = RelatedQuestionsData(questions=[])
        assert data.questions == []
