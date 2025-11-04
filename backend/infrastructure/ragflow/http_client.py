"""
RAGFlow HTTP client using httpx.

Provides a thin wrapper around httpx for making HTTP requests to RAGFlow API
with retry logic, timeout handling, and error mapping.
"""

import json
import logging
import time
from collections.abc import Iterator
from typing import Any

import httpx
from django.conf import settings

from .exceptions import (
    RagFlowAPIError,
    RagFlowConfigurationError,
    RagFlowConnectionError,
    RagFlowRateLimitError,
    RagFlowTimeoutError,
)

logger = logging.getLogger(__name__)


class RagFlowHttpClient:
    """
    HTTP client for RAGFlow API.

    Handles authentication, retries, timeouts, and error mapping for all
    HTTP interactions with RAGFlow.
    """

    # Default timeouts (in seconds)
    DEFAULT_CONNECT_TIMEOUT = 3.0
    DEFAULT_READ_TIMEOUT = 30.0
    DEFAULT_STREAM_TIMEOUT = 120.0

    # Retry configuration
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0
    RETRY_BACKOFF_FACTOR = 2.0
    RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        login_token: str | None = None,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        read_timeout: float = DEFAULT_READ_TIMEOUT,
        stream_timeout: float = DEFAULT_STREAM_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        """
        Initialize RagFlowHttpClient.

        Args:
            base_url: RAGFlow base URL (defaults to settings.RAGFLOW_BASE_URL)
            api_key: RAGFlow API key (defaults to settings.RAGFLOW_API_KEY)
            login_token: RAGFlow login token for certain endpoints (defaults to settings.RAGFLOW_LOGIN_TOKEN)
            connect_timeout: Connection timeout in seconds
            read_timeout: Read timeout for regular requests
            stream_timeout: Read timeout for streaming requests
            max_retries: Maximum number of retries for failed requests

        Raises:
            RagFlowConfigurationError: If required configuration is missing
        """
        self.base_url = (
            base_url
            or getattr(settings, "RAGFLOW_BASE_URL", None)
            or "http://localhost:9380"
        )
        self.api_key = api_key or getattr(settings, "RAGFLOW_API_KEY", None)
        self.login_token = login_token or getattr(settings, "RAGFLOW_LOGIN_TOKEN", None)

        if not self.api_key:
            raise RagFlowConfigurationError(
                "RAGFlow API key is required", config_key="RAGFLOW_API_KEY"
            )

        # Remove trailing slash from base_url
        self.base_url = self.base_url.rstrip("/")

        # Timeout configuration
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.stream_timeout = stream_timeout
        self.max_retries = max_retries

        # Create httpx client (will be reused for connection pooling)
        self._client: httpx.Client | None = None

        logger.info(f"RagFlowHttpClient initialized with base_url: {self.base_url}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close client."""
        self.close()

    def close(self):
        """Close the underlying httpx client."""
        if self._client:
            self._client.close()
            self._client = None

    @property
    def client(self) -> httpx.Client:
        """Get or create the httpx client (lazy initialization)."""
        if self._client is None:
            timeout = httpx.Timeout(
                connect=self.connect_timeout,
                read=self.read_timeout,
                write=self.read_timeout,
                pool=5.0,
            )
            self._client = httpx.Client(
                timeout=timeout,
                follow_redirects=True,
            )
        return self._client

    def _get_headers(
        self, use_login_token: bool = False, extra_headers: dict = None
    ) -> dict:
        """
        Get request headers with authentication.

        Args:
            use_login_token: Use login token instead of API key
            extra_headers: Additional headers to include

        Returns:
            Headers dictionary
        """
        headers = {}

        if use_login_token and self.login_token:
            headers["Authorization"] = f"Bearer {self.login_token}"
        elif self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        if extra_headers:
            headers.update(extra_headers)

        return headers

    def _build_url(self, path: str) -> str:
        """
        Build full URL from path.

        Args:
            path: API path (should start with /)

        Returns:
            Full URL
        """
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.base_url}{path}"

    def _handle_error_response(self, response: httpx.Response, operation: str = None):
        """
        Handle error HTTP responses and raise appropriate exceptions.

        Args:
            response: httpx Response object
            operation: Optional operation description for error context

        Raises:
            RagFlowRateLimitError: For 429 status
            RagFlowAPIError: For other error statuses
        """
        status_code = response.status_code

        # Try to parse error response
        try:
            data = response.json()
            message = data.get("message", response.text)
            error_code = data.get("code")
        except Exception:
            message = response.text or f"HTTP {status_code}"
            data = None
            error_code = None

        # Handle rate limiting
        if status_code == 429:
            retry_after = response.headers.get("Retry-After")
            retry_after = int(retry_after) if retry_after else None
            raise RagFlowRateLimitError(
                message=message or "Rate limit exceeded",
                retry_after=retry_after,
                response_data=data,
            )

        # Build error message
        error_msg = f"{operation}: {message}" if operation else message

        raise RagFlowAPIError(
            message=error_msg,
            status_code=status_code,
            response_data=data,
            error_code=str(error_code) if error_code else None,
        )

    def _should_retry(self, status_code: int, attempt: int) -> bool:
        """
        Determine if a request should be retried.

        Args:
            status_code: HTTP status code
            attempt: Current attempt number (0-indexed)

        Returns:
            True if should retry
        """
        return status_code in self.RETRY_STATUS_CODES and attempt < self.max_retries

    def _calculate_retry_delay(self, attempt: int, base_delay: float = None) -> float:
        """
        Calculate exponential backoff delay.

        Args:
            attempt: Current attempt number (0-indexed)
            base_delay: Base delay in seconds

        Returns:
            Delay in seconds
        """
        base = base_delay or self.DEFAULT_RETRY_DELAY
        return base * (self.RETRY_BACKOFF_FACTOR**attempt)

    def request(
        self,
        method: str,
        path: str,
        params: dict = None,
        json_data: dict = None,
        data: Any = None,
        files: dict = None,
        headers: dict = None,
        use_login_token: bool = False,
        timeout: float = None,
        stream: bool = False,
    ) -> httpx.Response:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: API path (relative to base_url)
            params: Query parameters
            json_data: JSON body data
            data: Form data or raw body
            files: Files for multipart upload
            headers: Additional headers
            use_login_token: Use login token instead of API key
            timeout: Override default timeout
            stream: Enable streaming response

        Returns:
            httpx.Response object

        Raises:
            RagFlowConnectionError: For connection errors
            RagFlowTimeoutError: For timeout errors
            RagFlowRateLimitError: For rate limiting (429)
            RagFlowAPIError: For other API errors
        """
        url = self._build_url(path)
        headers = self._get_headers(use_login_token, headers)

        # Override timeout if specified
        if timeout is not None:
            request_timeout = httpx.Timeout(
                connect=self.connect_timeout,
                read=timeout,
                write=timeout,
                pool=5.0,
            )
        elif stream:
            request_timeout = httpx.Timeout(
                connect=self.connect_timeout,
                read=self.stream_timeout,
                write=self.stream_timeout,
                pool=5.0,
            )
        else:
            request_timeout = None  # Use client default

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    data=data,
                    files=files,
                    headers=headers,
                    timeout=request_timeout,
                )

                # Check if we should retry based on status code
                if not response.is_success and self._should_retry(
                    response.status_code, attempt
                ):
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        f"Request failed with status {response.status_code}, "
                        f"retrying in {delay}s (attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    time.sleep(delay)
                    continue

                # Raise for error status
                if not response.is_success:
                    self._handle_error_response(response, f"{method} {path}")

                return response

            except httpx.TimeoutException as e:
                last_exception = RagFlowTimeoutError(
                    f"Request timeout: {method} {path}",
                    timeout=timeout or self.read_timeout,
                    operation=f"{method} {path}",
                )
                if attempt < self.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        f"Request timeout, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    time.sleep(delay)
                else:
                    raise last_exception from e

            except (httpx.ConnectError, httpx.NetworkError) as e:
                last_exception = RagFlowConnectionError(
                    f"Connection error: {method} {path}",
                    base_url=self.base_url,
                    cause=e,
                )
                if attempt < self.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        f"Connection error, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    time.sleep(delay)
                else:
                    raise last_exception from e

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise RagFlowAPIError(f"Request failed after {self.max_retries + 1} attempts")

    def get(
        self,
        path: str,
        params: dict = None,
        headers: dict = None,
        use_login_token: bool = False,
        timeout: float = None,
    ) -> httpx.Response:
        """Make a GET request."""
        return self.request(
            "GET",
            path,
            params=params,
            headers=headers,
            use_login_token=use_login_token,
            timeout=timeout,
        )

    def post(
        self,
        path: str,
        json_data: dict = None,
        data: Any = None,
        params: dict = None,
        headers: dict = None,
        use_login_token: bool = False,
        timeout: float = None,
    ) -> httpx.Response:
        """Make a POST request."""
        return self.request(
            "POST",
            path,
            params=params,
            json_data=json_data,
            data=data,
            headers=headers,
            use_login_token=use_login_token,
            timeout=timeout,
        )

    def put(
        self,
        path: str,
        json_data: dict = None,
        params: dict = None,
        headers: dict = None,
        use_login_token: bool = False,
        timeout: float = None,
    ) -> httpx.Response:
        """Make a PUT request."""
        return self.request(
            "PUT",
            path,
            params=params,
            json_data=json_data,
            headers=headers,
            use_login_token=use_login_token,
            timeout=timeout,
        )

    def delete(
        self,
        path: str,
        json_data: dict = None,
        params: dict = None,
        headers: dict = None,
        use_login_token: bool = False,
        timeout: float = None,
    ) -> httpx.Response:
        """Make a DELETE request."""
        return self.request(
            "DELETE",
            path,
            params=params,
            json_data=json_data,
            headers=headers,
            use_login_token=use_login_token,
            timeout=timeout,
        )

    def upload(
        self,
        path: str,
        files: dict,
        data: dict = None,
        params: dict = None,
        headers: dict = None,
        use_login_token: bool = False,
        timeout: float = None,
    ) -> httpx.Response:
        """
        Upload files using multipart/form-data.

        Args:
            path: API path
            files: Dictionary of files to upload {field_name: file_content or (filename, file_content)}
            data: Additional form data
            params: Query parameters
            headers: Additional headers
            use_login_token: Use login token instead of API key
            timeout: Override default timeout

        Returns:
            httpx.Response object
        """
        return self.request(
            "POST",
            path,
            params=params,
            data=data,
            files=files,
            headers=headers,
            use_login_token=use_login_token,
            timeout=timeout,
        )

    def stream(
        self,
        method: str,
        path: str,
        params: dict = None,
        json_data: dict = None,
        headers: dict = None,
        use_login_token: bool = False,
        timeout: float = None,
    ) -> Iterator[str]:
        """
        Make a streaming request and yield response lines.

        Used for Server-Sent Events (SSE) style streaming responses.
        Each line is yielded as a string.

        Args:
            method: HTTP method
            path: API path
            params: Query parameters
            json_data: JSON body data
            headers: Additional headers
            use_login_token: Use login token instead of API key
            timeout: Override default timeout

        Yields:
            Response lines as strings

        Raises:
            RagFlowConnectionError: For connection errors
            RagFlowTimeoutError: For timeout errors
            RagFlowAPIError: For API errors
        """
        url = self._build_url(path)
        headers = self._get_headers(use_login_token, headers)

        # Use stream timeout
        timeout_config = httpx.Timeout(
            connect=self.connect_timeout,
            read=timeout or self.stream_timeout,
            write=timeout or self.stream_timeout,
            pool=5.0,
        )

        try:
            with self.client.stream(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=headers,
                timeout=timeout_config,
            ) as response:
                # Check initial status
                if not response.is_success:
                    # Read full response for error handling
                    response.read()
                    self._handle_error_response(response, f"{method} {path} (stream)")

                # Yield lines
                for line in response.iter_lines():
                    yield line

        except httpx.TimeoutException as e:
            raise RagFlowTimeoutError(
                f"Stream timeout: {method} {path}",
                timeout=timeout or self.stream_timeout,
                operation=f"{method} {path} (stream)",
            ) from e

        except (httpx.ConnectError, httpx.NetworkError) as e:
            raise RagFlowConnectionError(
                f"Stream connection error: {method} {path}",
                base_url=self.base_url,
                cause=e,
            ) from e

    def stream_json(
        self,
        method: str,
        path: str,
        params: dict = None,
        json_data: dict = None,
        headers: dict = None,
        use_login_token: bool = False,
        timeout: float = None,
        data_prefix: str = "data:",
    ) -> Iterator[dict]:
        """
        Make a streaming request and yield parsed JSON objects.

        Parses Server-Sent Events (SSE) style streaming where each line
        is prefixed with "data:" and contains a JSON object.

        Args:
            method: HTTP method
            path: API path
            params: Query parameters
            json_data: JSON body data
            headers: Additional headers
            use_login_token: Use login token instead of API key
            timeout: Override default timeout
            data_prefix: Prefix to strip from each line (default: "data:")

        Yields:
            Parsed JSON objects

        Raises:
            RagFlowConnectionError: For connection errors
            RagFlowTimeoutError: For timeout errors
            RagFlowAPIError: For API errors
        """
        for line in self.stream(
            method, path, params, json_data, headers, use_login_token, timeout
        ):
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Strip data prefix if present
            if data_prefix and line.startswith(data_prefix):
                line = line[len(data_prefix) :].strip()

            # Try to parse JSON
            try:
                data = json.loads(line)
                yield data
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Failed to parse JSON from stream: {line[:100]}... Error: {e}"
                )
                # Don't raise, just skip malformed lines
                continue
