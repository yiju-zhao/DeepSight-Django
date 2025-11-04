"""
Tests for RAGFlow service layer.

These tests mock the HTTP client to test service orchestration logic.
"""

from unittest.mock import Mock, patch

import httpx
import pytest

from infrastructure.ragflow.exceptions import (
    RagFlowChatError,
    RagFlowSessionError,
)
from infrastructure.ragflow.http_client import RagFlowHttpClient
from infrastructure.ragflow.models import (
    APIResponse,
    ChatSession,
    CompletionResponse,
    CompletionStreamEvent,
    SessionListData,
)
from infrastructure.ragflow.service import RagflowService


@pytest.fixture
def mock_http_client():
    """Create a mocked HTTP client."""
    client = Mock(spec=RagFlowHttpClient)
    return client


@pytest.fixture
def service(mock_http_client):
    """Create a RagflowService with mocked HTTP client."""
    return RagflowService(http_client=mock_http_client)


class TestRagflowServiceConversation:
    """Test conversation methods."""

    def test_non_stream_conversation(self, service, mock_http_client):
        """Test non-streaming conversation."""
        # Mock response
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "answer": "Test answer",
                "session_id": "sess123",
                "reference": {},
            },
        }
        mock_http_client.post.return_value = mock_response

        result = service.conversation(
            chat_id="chat123",
            question="Test question",
            stream=False,
        )

        assert isinstance(result, CompletionResponse)
        assert result.is_success
        mock_http_client.post.assert_called_once()

    def test_stream_conversation(self, service, mock_http_client):
        """Test streaming conversation."""
        # Mock streaming response
        stream_data = [
            {
                "code": 0,
                "data": {"answer": "Test", "session_id": "sess123", "reference": {}},
            },
            {"code": 0, "data": True},
        ]
        mock_http_client.stream_json.return_value = iter(stream_data)

        result = service.conversation(
            chat_id="chat123",
            question="Test question",
            stream=True,
        )

        events = list(result)
        assert len(events) == 2
        assert isinstance(events[0], CompletionStreamEvent)
        assert events[1].is_final


class TestRagflowServiceSessions:
    """Test session management methods."""

    def test_create_session(self, service, mock_http_client):
        """Test creating a chat session."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "id": "sess123",
                "name": "Test Session",
            },
        }
        mock_http_client.post.return_value = mock_response

        session = service.create_chat_session(
            chat_id="chat123",
            name="Test Session",
        )

        assert isinstance(session, ChatSession)
        assert session.id == "sess123"
        assert session.chat_id == "chat123"
        mock_http_client.post.assert_called_once()

    def test_list_sessions(self, service, mock_http_client):
        """Test listing chat sessions."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "sessions": [
                    {"id": "sess1", "name": "Session 1"},
                    {"id": "sess2", "name": "Session 2"},
                ],
                "total": 2,
            },
        }
        mock_http_client.get.return_value = mock_response

        sessions = service.list_chat_sessions(chat_id="chat123")

        assert len(sessions) == 2
        assert all(isinstance(s, ChatSession) for s in sessions)
        assert all(s.chat_id == "chat123" for s in sessions)

    def test_update_session(self, service, mock_http_client):
        """Test updating a chat session."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {
            "code": 0,
            "data": True,
        }
        mock_http_client.put.return_value = mock_response

        result = service.update_chat_session(
            chat_id="chat123",
            session_id="sess123",
            name="Updated Name",
        )

        assert result is True
        mock_http_client.put.assert_called_once()

    def test_delete_sessions(self, service, mock_http_client):
        """Test deleting chat sessions."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {
            "code": 0,
            "data": True,
        }
        mock_http_client.delete.return_value = mock_response

        result = service.delete_chat_sessions(
            chat_id="chat123",
            session_ids=["sess1", "sess2"],
        )

        assert result is True
        mock_http_client.delete.assert_called_once()


class TestRagflowServiceRelatedQuestions:
    """Test related questions generation."""

    def test_related_questions(self, service, mock_http_client):
        """Test generating related questions."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "questions": ["Question 1?", "Question 2?", "Question 3?"],
            },
        }
        mock_http_client.post.return_value = mock_response

        questions = service.related_questions(question="Test question")

        assert len(questions) == 3
        assert all(isinstance(q, str) for q in questions)
        mock_http_client.post.assert_called_once()
        # Verify login token is used
        call_kwargs = mock_http_client.post.call_args[1]
        assert call_kwargs.get("use_login_token") is True


class TestRagflowServiceChunks:
    """Test chunk listing."""

    def test_list_chunks(self, service, mock_http_client):
        """Test listing document chunks."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "chunks": [
                    {
                        "id": "chunk1",
                        "content": "Content 1",
                        "document_id": "doc123",
                        "available": True,
                    },
                ],
                "total": 1,
            },
        }
        mock_http_client.get.return_value = mock_response

        paginated = service.list_chunks(
            dataset_id="ds123",
            document_id="doc123",
        )

        assert paginated.total == 1
        assert len(paginated.items) == 1
        assert paginated.items[0].id == "chunk1"


class TestRagflowServiceHealthCheck:
    """Test health check."""

    def test_health_check_success(self, service, mock_http_client):
        """Test successful health check."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.is_success = True
        mock_http_client.get.return_value = mock_response

        result = service.health_check()
        assert result is True

    def test_health_check_failure(self, service, mock_http_client):
        """Test failed health check."""
        mock_http_client.get.side_effect = Exception("Connection error")

        result = service.health_check()
        assert result is False


class TestRagflowServiceNotImplemented:
    """Test that Phase 3 methods raise NotImplementedError."""

    def test_create_dataset_not_implemented(self, service):
        """Test create_dataset raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            service.create_dataset(name="Test")

    def test_create_chat_not_implemented(self, service):
        """Test create_chat raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            service.create_chat(dataset_ids=["ds1"], name="Test")

    def test_upload_document_not_implemented(self, service):
        """Test upload_document_text raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            service.upload_document_text(
                dataset_id="ds1", content="test", display_name="test.txt"
            )


# TODO: Add more comprehensive tests in Phase 5
# TODO: Add integration tests with real HTTP calls (optional, for local testing)
