"""
Core exception classes for the DeepSight application.
"""
from typing import Dict, Any, Optional
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError


class DeepSightException(Exception):
    """Base exception class for DeepSight application."""
    pass


class ValidationError(DeepSightException):
    """Raised when data validation fails."""
    pass


class ProcessingError(DeepSightException):
    """Raised when content processing fails."""
    pass


class StorageError(DeepSightException):
    """Raised when storage operations fail."""
    pass


class SearchError(DeepSightException):
    """Raised when search operations fail."""
    pass


class AIServiceError(DeepSightException):
    """Raised when AI service operations fail."""
    pass


def custom_exception_handler(exc, context):
    """
    Custom exception handler that normalizes error responses across the API.

    Returns a consistent error format:
    {
        "detail": "Error message",
        "field_errors": {"field": ["error1", "error2"]},  # For validation errors
        "error_code": "CUSTOM_ERROR_CODE"  # Optional
    }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        custom_response_data = {}

        # Handle validation errors with field-specific messages
        if hasattr(response, 'data') and isinstance(response.data, dict):
            if 'detail' in response.data:
                # Single error message
                custom_response_data['detail'] = response.data['detail']
            else:
                # Field validation errors
                custom_response_data['detail'] = "Validation failed"
                custom_response_data['field_errors'] = response.data
        elif hasattr(response, 'data') and isinstance(response.data, list):
            # List of errors
            custom_response_data['detail'] = response.data[0] if response.data else "An error occurred"
        else:
            custom_response_data['detail'] = str(exc)

        response.data = custom_response_data
    else:
        # Handle custom DeepSight exceptions
        if isinstance(exc, ProcessingError):
            response = Response(
                {"detail": str(exc), "error_code": "PROCESSING_ERROR"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif isinstance(exc, StorageError):
            response = Response(
                {"detail": str(exc), "error_code": "STORAGE_ERROR"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        elif isinstance(exc, SearchError):
            response = Response(
                {"detail": str(exc), "error_code": "SEARCH_ERROR"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        elif isinstance(exc, AIServiceError):
            response = Response(
                {"detail": str(exc), "error_code": "AI_SERVICE_ERROR"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        elif isinstance(exc, ValidationError):
            response = Response(
                {"detail": str(exc), "error_code": "VALIDATION_ERROR"},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif isinstance(exc, Http404):
            response = Response(
                {"detail": "Not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        elif isinstance(exc, PermissionDenied):
            response = Response(
                {"detail": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        elif isinstance(exc, DjangoValidationError):
            response = Response(
                {"detail": "Validation failed", "field_errors": {"non_field_errors": exc.messages}},
                status=status.HTTP_400_BAD_REQUEST
            )

    return response