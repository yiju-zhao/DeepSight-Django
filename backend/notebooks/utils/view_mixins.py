"""
Common view mixins and utilities for notebooks app.
"""

import logging
from typing import Any, Optional

from django.shortcuts import get_object_or_404
from rest_framework import authentication, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse

from ..models import KnowledgeBaseItem, Notebook
from ..constants import DEFAULT_SIGNED_URL_EXPIRES

logger = logging.getLogger(__name__)


class NotebookPermissionMixin:
    """Mixin to handle notebook ownership verification."""

    def get_user_notebook(self, notebook_id: int, user):
        """Get notebook owned by user or raise 404."""
        return get_object_or_404(Notebook, id=notebook_id, user=user)

    def verify_notebook_access(self, notebook_id: int, user) -> bool:
        """Verify user has access to notebook."""
        return Notebook.objects.filter(id=notebook_id, user=user).exists()


class KnowledgeBasePermissionMixin:
    """Mixin to handle knowledge base item ownership verification."""

    def get_notebook_kb_item(self, kb_item_id: str, notebook):
        """Get knowledge base item from specific notebook or raise 404."""
        return get_object_or_404(KnowledgeBaseItem, id=kb_item_id, notebook=notebook)

    def verify_kb_item_access(self, kb_item_id: str, notebook) -> bool:
        """Verify knowledge base item exists in the specified notebook."""
        return KnowledgeBaseItem.objects.filter(
            id=kb_item_id, notebook=notebook
        ).exists()

    # Legacy method for backward compatibility
    def get_user_kb_item(self, kb_item_id: str, user):
        """Legacy method - knowledge base items are now notebook-specific."""
        # This method is deprecated since knowledge base items are now notebook-specific
        # Kept for backward compatibility but will require notebook context
        raise NotImplementedError(
            "Use get_notebook_kb_item with notebook parameter instead"
        )


class StandardAPIView(APIView):
    """Base API view with common settings and error handling."""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication]

    def handle_exception(self, exc):
        """Enhanced exception handling with logging."""
        logger.error(
            f"API Exception in {self.__class__.__name__}: {str(exc)}", exc_info=True
        )
        return super().handle_exception(exc)

    def success_response(
        self, data: Any = None, status_code: int = status.HTTP_200_OK
    ) -> Response:
        """Standardized success response."""
        return Response({"success": True, "data": data}, status=status_code)

    def error_response(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict | None = None,
    ) -> Response:
        """Standardized error response."""
        response_data = {"success": False, "error": message}
        if details:
            response_data["details"] = details
        return Response(response_data, status=status_code)


class FileAccessValidatorMixin:
    """Mixin for validating file access permissions."""

    def validate_notebook_file_access(
        self, notebook_id: int, file_id: str, user
    ) -> tuple:
        """
        Validate user has access to file through notebook.
        Returns (notebook, kb_item) or raises appropriate error.
        """
        notebook = get_object_or_404(Notebook, id=notebook_id, user=user)
        kb_item = get_object_or_404(KnowledgeBaseItem, id=file_id, notebook=notebook)

        return notebook, kb_item


class PaginationMixin:
    """Mixin for handling pagination parameters."""

    def get_pagination_params(self, request) -> tuple:
        """Extract pagination parameters from request."""
        try:
            limit = int(request.GET.get("limit", 50))
            offset = int(request.GET.get("offset", 0))

            # Apply reasonable bounds
            limit = min(max(1, limit), 100)  # Between 1 and 100
            offset = max(0, offset)  # Non-negative

            return limit, offset
        except (ValueError, TypeError):
            return 50, 0  # Default values


class FileMetadataExtractorMixin:
    """Mixin for extracting metadata from file objects."""

    def extract_original_filename(self, metadata: dict, fallback_title: str) -> str:
        """Extract original filename from metadata."""
        if metadata:
            # Try different metadata keys
            for key in ["original_filename", "filename", "name"]:
                if key in metadata and metadata[key]:
                    return metadata[key]
        return fallback_title

    def extract_file_extension(self, metadata: dict) -> str | None:
        """Extract file extension from metadata."""
        if metadata and "file_extension" in metadata:
            return metadata["file_extension"]
        return None

    def extract_file_size(self, metadata: dict) -> int | None:
        """Extract file size from metadata."""
        if metadata and "file_size" in metadata:
            try:
                return int(metadata["file_size"])
            except (ValueError, TypeError):
                pass
        return None


class FileListResponseMixin(FileMetadataExtractorMixin):
    """Mixin for generating standardized file list responses."""

    def build_file_response_data(self, kb_item: KnowledgeBaseItem) -> dict[str, Any]:
        """Build standardized file response data from KnowledgeBaseItem."""

        # Use metadata directly (file_metadata has been merged into metadata)
        combined_metadata = {**(kb_item.metadata or {})}

        file_data = {
            "file_id": str(kb_item.id),
            "title": kb_item.title,
            "content_type": kb_item.content_type,
            "tags": kb_item.tags,
            "created_at": kb_item.created_at.isoformat(),
            "updated_at": kb_item.updated_at.isoformat(),
            "notes": kb_item.notes,
            "metadata": combined_metadata,
            "has_file": bool(kb_item.file_object_key),
            "has_content": bool(kb_item.content),
            "has_original_file": bool(kb_item.original_file_object_key),
            "parsing_status": kb_item.parsing_status,
            # Extract metadata from knowledge base item
            "original_filename": self.extract_original_filename(
                kb_item.metadata, kb_item.title
            ),
            "file_extension": self.extract_file_extension(kb_item.metadata),
            "file_size": self.extract_file_size(kb_item.metadata),
            "uploaded_at": kb_item.created_at.isoformat(),
        }

        return file_data


class ETagCacheMixin:
    """Reusable helpers for setting ETag/Cache headers and handling conditional requests.

    Views can call `build_inline_file_response` with a content resolver to get a
    properly cached response (or 304 if client cache is fresh).
    """

    def _compute_storage_etag(self, storage, object_key: str) -> Optional[str]:
        try:
            meta = storage.get_file_metadata(object_key)
            if isinstance(meta, dict):
                etag = meta.get("etag") or meta.get("ETag")
                if etag:
                    return str(etag).strip('"')
        except Exception:
            return None
        return None

    def _client_etag_matches(self, request, etag: Optional[str]) -> bool:
        if not etag:
            return False
        client_etag = request.META.get("HTTP_IF_NONE_MATCH")
        if not client_etag:
            return False
        # Support weak/strong etags and quoted values
        client_etag = client_etag.strip().strip("W/").strip('"')
        return client_etag == etag

    def build_file_response(
        self,
        request,
        *,
        filename: str,
        content_type: str,
        content_bytes: bytes,
        etag: Optional[str] = None,
        max_age: int = 3600,
        disposition: str = "inline",
    ) -> HttpResponse:
        """Return HttpResponse with proper caching headers or 304 if ETag matches.

        disposition: "inline" or "attachment".
        """

        if self._client_etag_matches(request, etag):
            resp = HttpResponse(status=304)
            resp["ETag"] = f'"{etag}"'
            resp["Cache-Control"] = f"private, max-age={max_age}"
            resp["X-Content-Type-Options"] = "nosniff"
            return resp

        resp = HttpResponse(content_bytes, content_type=content_type)
        if disposition not in {"inline", "attachment"}:
            disposition = "inline"
        resp["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        resp["X-Content-Type-Options"] = "nosniff"
        if etag:
            resp["ETag"] = f'"{etag}"'
        resp["Cache-Control"] = f"private, max-age={max_age}"
        return resp

    def get_signed_url_expires(self, request) -> int:
        try:
            expires = int(request.GET.get("expires", "0"))
            return expires if expires > 0 else DEFAULT_SIGNED_URL_EXPIRES
        except Exception:
            return DEFAULT_SIGNED_URL_EXPIRES
