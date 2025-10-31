"""
RAGFlow custom exceptions.

Provides a hierarchy of exceptions for different error scenarios in RAGFlow integration.
"""

from typing import Any


class RagFlowError(Exception):
    """Base exception for all RAGFlow-related errors."""

    def __init__(self, message: str, details: Any = None):
        """
        Initialize RagFlowError.

        Args:
            message: Human-readable error message
            details: Additional error details (response data, error codes, etc.)
        """
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class RagFlowAPIError(RagFlowError):
    """Exception for HTTP API errors from RAGFlow."""

    def __init__(
        self,
        message: str,
        status_code: int = None,
        response_data: Any = None,
        error_code: str = None,
    ):
        """
        Initialize RagFlowAPIError.

        Args:
            message: Human-readable error message
            status_code: HTTP status code
            response_data: Raw response data from API
            error_code: RAGFlow-specific error code from response
        """
        self.status_code = status_code
        self.response_data = response_data
        self.error_code = error_code
        details = {
            "status_code": status_code,
            "error_code": error_code,
            "response": response_data,
        }
        super().__init__(message, details)

    def __str__(self):
        parts = [self.message]
        if self.status_code:
            parts.append(f"status={self.status_code}")
        if self.error_code:
            parts.append(f"code={self.error_code}")
        return " | ".join(parts)


class RagFlowDatasetError(RagFlowError):
    """Exception for dataset-related errors."""

    def __init__(self, message: str, dataset_id: str = None, details: Any = None):
        """
        Initialize RagFlowDatasetError.

        Args:
            message: Human-readable error message
            dataset_id: ID of the dataset that caused the error
            details: Additional error details
        """
        self.dataset_id = dataset_id
        error_details = {"dataset_id": dataset_id}
        if details:
            error_details.update(details if isinstance(details, dict) else {"data": details})
        super().__init__(message, error_details)


class RagFlowDocumentError(RagFlowError):
    """Exception for document-related errors."""

    def __init__(
        self,
        message: str,
        document_id: str = None,
        dataset_id: str = None,
        details: Any = None,
    ):
        """
        Initialize RagFlowDocumentError.

        Args:
            message: Human-readable error message
            document_id: ID of the document that caused the error
            dataset_id: ID of the associated dataset
            details: Additional error details
        """
        self.document_id = document_id
        self.dataset_id = dataset_id
        error_details = {"document_id": document_id, "dataset_id": dataset_id}
        if details:
            error_details.update(details if isinstance(details, dict) else {"data": details})
        super().__init__(message, error_details)


class RagFlowChatError(RagFlowError):
    """Exception for chat-related errors."""

    def __init__(self, message: str, chat_id: str = None, details: Any = None):
        """
        Initialize RagFlowChatError.

        Args:
            message: Human-readable error message
            chat_id: ID of the chat that caused the error
            details: Additional error details
        """
        self.chat_id = chat_id
        error_details = {"chat_id": chat_id}
        if details:
            error_details.update(details if isinstance(details, dict) else {"data": details})
        super().__init__(message, error_details)


class RagFlowSessionError(RagFlowError):
    """Exception for session-related errors."""

    def __init__(
        self,
        message: str,
        session_id: str = None,
        chat_id: str = None,
        details: Any = None,
    ):
        """
        Initialize RagFlowSessionError.

        Args:
            message: Human-readable error message
            session_id: ID of the session that caused the error
            chat_id: ID of the associated chat
            details: Additional error details
        """
        self.session_id = session_id
        self.chat_id = chat_id
        error_details = {"session_id": session_id, "chat_id": chat_id}
        if details:
            error_details.update(details if isinstance(details, dict) else {"data": details})
        super().__init__(message, error_details)


class RagFlowRateLimitError(RagFlowAPIError):
    """Exception for rate limiting errors (HTTP 429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = None,
        response_data: Any = None,
    ):
        """
        Initialize RagFlowRateLimitError.

        Args:
            message: Human-readable error message
            retry_after: Number of seconds to wait before retrying
            response_data: Raw response data from API
        """
        self.retry_after = retry_after
        super().__init__(
            message=message,
            status_code=429,
            response_data=response_data,
            error_code="RATE_LIMIT_EXCEEDED",
        )
        if retry_after:
            self.details["retry_after"] = retry_after

    def __str__(self):
        base = super().__str__()
        if self.retry_after:
            return f"{base} | retry_after={self.retry_after}s"
        return base


class RagFlowConfigurationError(RagFlowError):
    """Exception for configuration errors (missing API keys, invalid settings, etc.)."""

    def __init__(self, message: str, config_key: str = None):
        """
        Initialize RagFlowConfigurationError.

        Args:
            message: Human-readable error message
            config_key: The configuration key that is missing or invalid
        """
        self.config_key = config_key
        details = {"config_key": config_key} if config_key else None
        super().__init__(message, details)


class RagFlowTimeoutError(RagFlowError):
    """Exception for timeout errors."""

    def __init__(self, message: str, timeout: float = None, operation: str = None):
        """
        Initialize RagFlowTimeoutError.

        Args:
            message: Human-readable error message
            timeout: Timeout value in seconds
            operation: Operation that timed out
        """
        self.timeout = timeout
        self.operation = operation
        details = {"timeout": timeout, "operation": operation}
        super().__init__(message, details)


class RagFlowConnectionError(RagFlowError):
    """Exception for connection errors."""

    def __init__(self, message: str, base_url: str = None, cause: Exception = None):
        """
        Initialize RagFlowConnectionError.

        Args:
            message: Human-readable error message
            base_url: The URL that failed to connect
            cause: The underlying exception that caused the connection error
        """
        self.base_url = base_url
        self.cause = cause
        details = {"base_url": base_url, "cause": str(cause) if cause else None}
        super().__init__(message, details)
