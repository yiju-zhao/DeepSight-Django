"""
Tests for RAGFlow HTTP client.

These tests use mocked httpx responses to test the HTTP client logic
without making actual network requests.
"""

import json
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from infrastructure.ragflow.exceptions import (
    RagFlowAPIError,
    RagFlowConfigurationError,
    RagFlowConnectionError,
    RagFlowRateLimitError,
    RagFlowTimeoutError,
)
from infrastructure.ragflow.http_client import RagFlowHttpClient


@pytest.fixture
def mock_settings():
    """Mock Django settings."""
    with patch("infrastructure.ragflow.http_client.settings") as mock:
        mock.RAGFLOW_API_KEY = "test-api-key"
        mock.RAGFLOW_BASE_URL = "http://localhost:9380"
        mock.RAGFLOW_LOGIN_TOKEN = "test-login-token"
        yield mock


@pytest.fixture
def http_client(mock_settings):
    """Create HTTP client for testing."""
    client = RagFlowHttpClient(
        base_url="http://localhost:9380",
        api_key="test-key",
        login_token="test-token",
    )
    yield client
    client.close()


class TestRagFlowHttpClientInit:
    """Test HTTP client initialization."""

    def test_init_with_params(self):
        """Test initialization with explicit parameters."""
        client = RagFlowHttpClient(
            base_url="http://test.com",
            api_key="key123",
            login_token="token123",
        )
        assert client.base_url == "http://test.com"
        assert client.api_key == "key123"
        assert client.login_token == "token123"
        client.close()

    def test_init_missing_api_key(self, mock_settings):
        """Test initialization fails without API key."""
        mock_settings.RAGFLOW_API_KEY = None
        with pytest.raises(RagFlowConfigurationError) as exc_info:
            RagFlowHttpClient()
        assert "API key is required" in str(exc_info.value)

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from base_url."""
        client = RagFlowHttpClient(
            base_url="http://test.com/", api_key="key123"
        )
        assert client.base_url == "http://test.com"
        client.close()


class TestRagFlowHttpClientHeaders:
    """Test header generation."""

    def test_get_headers_default(self, http_client):
        """Test default headers with API key."""
        headers = http_client._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-key"

    def test_get_headers_with_login_token(self, http_client):
        """Test headers with login token."""
        headers = http_client._get_headers(use_login_token=True)
        assert headers["Authorization"] == "Bearer test-token"

    def test_get_headers_with_extra(self, http_client):
        """Test headers with extra headers."""
        extra = {"X-Custom": "value"}
        headers = http_client._get_headers(extra_headers=extra)
        assert headers["X-Custom"] == "value"


class TestRagFlowHttpClientURL:
    """Test URL building."""

    def test_build_url(self, http_client):
        """Test URL building."""
        url = http_client._build_url("/api/v1/test")
        assert url == "http://localhost:9380/api/v1/test"

    def test_build_url_adds_leading_slash(self, http_client):
        """Test URL building adds leading slash."""
        url = http_client._build_url("api/v1/test")
        assert url == "http://localhost:9380/api/v1/test"


class TestRagFlowHttpClientRequest:
    """Test request method with mocked responses."""

    def test_successful_get_request(self, http_client):
        """Test successful GET request."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "data": "test"}

        with patch.object(http_client.client, "request", return_value=mock_response):
            response = http_client.get("/test")
            assert response.is_success
            assert response.json() == {"code": 0, "data": "test"}

    def test_request_with_retry_on_500(self, http_client):
        """Test retry logic on 500 error."""
        # First call fails with 500, second succeeds
        mock_response_fail = Mock(spec=httpx.Response)
        mock_response_fail.is_success = False
        mock_response_fail.status_code = 500

        mock_response_success = Mock(spec=httpx.Response)
        mock_response_success.is_success = True
        mock_response_success.status_code = 200

        with patch.object(
            http_client.client,
            "request",
            side_effect=[mock_response_fail, mock_response_success],
        ):
            with patch("time.sleep"):  # Skip sleep in tests
                response = http_client.get("/test")
                assert response.is_success

    def test_request_raises_rate_limit_error(self, http_client):
        """Test rate limit error is raised."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.is_success = False
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.json.return_value = {
            "code": 429,
            "message": "Rate limit exceeded",
        }
        mock_response.text = "Rate limit exceeded"

        with patch.object(http_client.client, "request", return_value=mock_response):
            with pytest.raises(RagFlowRateLimitError) as exc_info:
                http_client.get("/test")
            assert exc_info.value.retry_after == 60

    def test_request_raises_api_error(self, http_client):
        """Test API error is raised."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.is_success = False
        mock_response.status_code = 400
        mock_response.json.return_value = {"code": 102, "message": "Invalid input"}
        mock_response.text = "Invalid input"

        with patch.object(http_client.client, "request", return_value=mock_response):
            with pytest.raises(RagFlowAPIError) as exc_info:
                http_client.get("/test")
            assert exc_info.value.status_code == 400

    def test_request_timeout_error(self, http_client):
        """Test timeout error handling."""
        with patch.object(
            http_client.client,
            "request",
            side_effect=httpx.TimeoutException("Timeout"),
        ):
            with pytest.raises(RagFlowTimeoutError):
                http_client.get("/test")

    def test_request_connection_error(self, http_client):
        """Test connection error handling."""
        with patch.object(
            http_client.client,
            "request",
            side_effect=httpx.ConnectError("Connection failed"),
        ):
            with pytest.raises(RagFlowConnectionError):
                http_client.get("/test")


class TestRagFlowHttpClientHelperMethods:
    """Test HTTP method helpers."""

    def test_post_method(self, http_client):
        """Test POST helper method."""
        with patch.object(http_client, "request") as mock_request:
            http_client.post("/test", json_data={"key": "value"})
            mock_request.assert_called_once()
            assert mock_request.call_args[0][0] == "POST"

    def test_put_method(self, http_client):
        """Test PUT helper method."""
        with patch.object(http_client, "request") as mock_request:
            http_client.put("/test", json_data={"key": "value"})
            mock_request.assert_called_once()
            assert mock_request.call_args[0][0] == "PUT"

    def test_delete_method(self, http_client):
        """Test DELETE helper method."""
        with patch.object(http_client, "request") as mock_request:
            http_client.delete("/test")
            mock_request.assert_called_once()
            assert mock_request.call_args[0][0] == "DELETE"

    def test_upload_method(self, http_client):
        """Test upload helper method."""
        with patch.object(http_client, "request") as mock_request:
            files = {"file": ("test.txt", b"content")}
            http_client.upload("/test", files=files)
            mock_request.assert_called_once()
            assert mock_request.call_args[1]["files"] == files


class TestRagFlowHttpClientStreaming:
    """Test streaming methods."""

    def test_stream_json(self, http_client):
        """Test stream_json method."""
        # Mock streaming response
        mock_lines = [
            "data:{"code":0,"data":{"answer":"Test"}}",
            "data:{"code":0,"data":true}",
        ]

        with patch.object(http_client, "stream", return_value=iter(mock_lines)):
            events = list(http_client.stream_json("POST", "/test"))
            assert len(events) == 2
            assert events[0]["code"] == 0
            assert events[1]["data"] is True


# TODO: Add more comprehensive tests in Phase 5
