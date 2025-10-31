"""
Tests for RAGFlow exceptions.
"""

import pytest

from infrastructure.ragflow.exceptions import (
    RagFlowAPIError,
    RagFlowChatError,
    RagFlowConfigurationError,
    RagFlowConnectionError,
    RagFlowDatasetError,
    RagFlowDocumentError,
    RagFlowError,
    RagFlowRateLimitError,
    RagFlowSessionError,
    RagFlowTimeoutError,
)


class TestRagFlowError:
    """Test base RagFlowError exception."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = RagFlowError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details is None

    def test_error_with_details(self):
        """Test error with details."""
        details = {"key": "value"}
        error = RagFlowError("Test error", details=details)
        assert error.details == details
        assert "details:" in str(error)


class TestRagFlowAPIError:
    """Test RagFlowAPIError exception."""

    def test_api_error_basic(self):
        """Test basic API error."""
        error = RagFlowAPIError("API failed", status_code=500)
        assert error.status_code == 500
        assert "status=500" in str(error)

    def test_api_error_with_error_code(self):
        """Test API error with error code."""
        error = RagFlowAPIError(
            "API failed", status_code=400, error_code="INVALID_REQUEST"
        )
        assert error.error_code == "INVALID_REQUEST"
        assert "code=INVALID_REQUEST" in str(error)

    def test_api_error_with_response_data(self):
        """Test API error with response data."""
        response_data = {"code": 102, "message": "Invalid input"}
        error = RagFlowAPIError(
            "API failed", status_code=400, response_data=response_data
        )
        assert error.response_data == response_data
        assert error.details["response"] == response_data


class TestRagFlowDatasetError:
    """Test RagFlowDatasetError exception."""

    def test_dataset_error(self):
        """Test dataset error."""
        error = RagFlowDatasetError("Dataset failed", dataset_id="ds123")
        assert error.dataset_id == "ds123"
        assert error.details["dataset_id"] == "ds123"

    def test_dataset_error_with_details(self):
        """Test dataset error with additional details."""
        error = RagFlowDatasetError(
            "Dataset failed", dataset_id="ds123", details={"extra": "info"}
        )
        assert error.details["dataset_id"] == "ds123"
        assert error.details["extra"] == "info"


class TestRagFlowDocumentError:
    """Test RagFlowDocumentError exception."""

    def test_document_error(self):
        """Test document error."""
        error = RagFlowDocumentError(
            "Document failed", document_id="doc123", dataset_id="ds123"
        )
        assert error.document_id == "doc123"
        assert error.dataset_id == "ds123"


class TestRagFlowChatError:
    """Test RagFlowChatError exception."""

    def test_chat_error(self):
        """Test chat error."""
        error = RagFlowChatError("Chat failed", chat_id="chat123")
        assert error.chat_id == "chat123"


class TestRagFlowSessionError:
    """Test RagFlowSessionError exception."""

    def test_session_error(self):
        """Test session error."""
        error = RagFlowSessionError(
            "Session failed", session_id="sess123", chat_id="chat123"
        )
        assert error.session_id == "sess123"
        assert error.chat_id == "chat123"


class TestRagFlowRateLimitError:
    """Test RagFlowRateLimitError exception."""

    def test_rate_limit_error(self):
        """Test rate limit error."""
        error = RagFlowRateLimitError()
        assert error.status_code == 429
        assert error.error_code == "RATE_LIMIT_EXCEEDED"

    def test_rate_limit_with_retry_after(self):
        """Test rate limit error with retry_after."""
        error = RagFlowRateLimitError(retry_after=60)
        assert error.retry_after == 60
        assert "retry_after=60s" in str(error)


class TestRagFlowConfigurationError:
    """Test RagFlowConfigurationError exception."""

    def test_configuration_error(self):
        """Test configuration error."""
        error = RagFlowConfigurationError(
            "Missing API key", config_key="RAGFLOW_API_KEY"
        )
        assert error.config_key == "RAGFLOW_API_KEY"


class TestRagFlowTimeoutError:
    """Test RagFlowTimeoutError exception."""

    def test_timeout_error(self):
        """Test timeout error."""
        error = RagFlowTimeoutError(
            "Request timeout", timeout=30.0, operation="GET /api/datasets"
        )
        assert error.timeout == 30.0
        assert error.operation == "GET /api/datasets"


class TestRagFlowConnectionError:
    """Test RagFlowConnectionError exception."""

    def test_connection_error(self):
        """Test connection error."""
        error = RagFlowConnectionError(
            "Connection failed", base_url="http://localhost:9380"
        )
        assert error.base_url == "http://localhost:9380"

    def test_connection_error_with_cause(self):
        """Test connection error with cause."""
        cause = Exception("Network error")
        error = RagFlowConnectionError("Connection failed", cause=cause)
        assert error.cause == cause
        assert "Network error" in str(error.details["cause"])
