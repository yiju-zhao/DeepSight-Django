"""
Notebooks views (consolidated).

This file merges all notebook-related views and viewsets, replacing the
previous notebooks/views/* modules.
"""

import hashlib
import json
import logging
import time
from collections.abc import Generator
from typing import Any

import redis
from core.pagination import LargePageNumberPagination, NotebookPagination
from core.permissions import IsNotebookOwner, IsOwnerPermission
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.http import http_date
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import (
    authentication,
    filters,
    permissions,
    serializers,
    status,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
)

from .models import (
    BatchJob,
    ChatSession,
    KnowledgeBaseItem,
    Notebook,
)
from .serializers import (
    BatchFileUploadSerializer,
    BatchJobSerializer,
    BatchURLParseDocumentSerializer,
    BatchURLParseSerializer,
    BatchURLParseWithMediaSerializer,
    KnowledgeBaseItemSerializer,
    NotebookCreateSerializer,
    NotebookListSerializer,
    NotebookSerializer,
    NotebookUpdateSerializer,
    URLParseDocumentSerializer,
    URLParseSerializer,
    URLParseWithMediaSerializer,
    VideoImageExtractionSerializer,
)
from .services import (
    ChatService,
    FileService,
    KnowledgeBaseService,
    NotebookService,
    URLService,
)
from .utils.view_mixins import ETagCacheMixin
from .constants import RagflowDocStatus, ParsingStatus

logger = logging.getLogger(__name__)


# ----------------------------
# Notebook CRUD and operations
# ----------------------------
@extend_schema_view(
    list=extend_schema(
        summary="List notebooks",
        description="Get paginated list of notebooks for the authenticated user",
        responses={200: NotebookListSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Get notebook details",
        description="Retrieve detailed information about a specific notebook",
        responses={200: NotebookSerializer},
    ),
    create=extend_schema(
        summary="Create notebook",
        description="Create a new notebook with RAGFlow knowledge base integration",
        request=NotebookCreateSerializer,
        responses={201: NotebookSerializer},
    ),
    update=extend_schema(
        summary="Update notebook",
        description="Update notebook details (full update)",
        request=NotebookUpdateSerializer,
        responses={200: NotebookSerializer},
    ),
    partial_update=extend_schema(
        summary="Partially update notebook",
        description="Update specific fields of a notebook",
        request=NotebookUpdateSerializer,
        responses={200: NotebookSerializer},
    ),
    destroy=extend_schema(
        summary="Delete notebook",
        description="Delete a notebook and cleanup associated RAGFlow resources",
        responses={204: None},
    ),
)
class NotebookViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOwnerPermission]
    authentication_classes = [
        authentication.SessionAuthentication,
        authentication.TokenAuthentication,
    ]
    pagination_class = NotebookPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["created_at"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at", "updated_at"]
    ordering = ["-updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.notebook_service = NotebookService()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notebook.objects.none()
        if not self.request.user.is_authenticated:
            return Notebook.objects.none()
        return (
            Notebook.objects.filter(user=self.request.user)
            .select_related("user")
            .prefetch_related("knowledge_base_items", "batch_jobs", "chat_sessions")
            .order_by("-updated_at")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return NotebookListSerializer
        elif self.action in ["create"]:
            return NotebookCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return NotebookUpdateSerializer
        return NotebookSerializer

    def perform_create(self, serializer):
        try:
            # Use the service layer to create notebook with RAGFlow integration
            notebook = self.notebook_service.create_notebook(
                user=self.request.user,
                name=serializer.validated_data["name"],
                description=serializer.validated_data.get("description", ""),
            )
            # Set the instance so DRF can return it properly
            serializer.instance = notebook
        except ValidationError as e:
            # Re-raise validation errors as DRF ValidationError
            raise serializers.ValidationError({"detail": str(e)})
        except Exception as e:
            logger.exception(f"Failed to create notebook: {e}")
            raise serializers.ValidationError(
                {"detail": f"Failed to create notebook: {str(e)}"}
            )

    def create(self, request, *args, **kwargs):
        """Override create to return full notebook data with NotebookSerializer."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Use NotebookSerializer for response to include all fields (id, created_at, etc.)
        response_serializer = NotebookSerializer(serializer.instance)
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_destroy(self, instance):
        """
        Use the service layer to delete notebook with RAGFlow cleanup.
        """
        try:
            # Use service layer for proper RAGFlow cleanup
            stats = self.notebook_service.delete_notebook(
                notebook_id=str(instance.id), user=self.request.user
            )
            logger.info(
                f"Notebook {instance.id} deleted successfully with stats: {stats}"
            )
        except Exception as e:
            logger.exception(f"Failed to delete notebook {instance.id}: {e}")
            raise

    @extend_schema(
        summary="Get notebook statistics",
        description="Retrieve statistics for a notebook including source counts and processing status",
        responses={
            200: OpenApiResponse(
                description="Notebook statistics",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "total_sources": 10,
                            "completed_sources": 8,
                            "processing_sources": 2,
                            "failed_sources": 0,
                        },
                    )
                ],
            )
        },
    )
    @action(detail=True, methods=["get"], url_path="stats")
    def stats(self, request, pk=None):
        notebook = self.get_object()
        try:
            stats = self.notebook_service.get_notebook_stats(notebook)
            return Response(stats)
        except Exception as e:
            logger.exception(f"Failed to get notebook stats for {pk}: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary="Duplicate notebook",
        description="Create a copy of an existing notebook with all its sources and settings",
        request=None,
        responses={
            201: NotebookSerializer,
            500: OpenApiResponse(description="Failed to duplicate notebook"),
        },
    )
    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request, pk=None):
        notebook = self.get_object()
        try:
            new_notebook = self.notebook_service.duplicate_notebook(
                notebook, user=request.user
            )
            serializer = NotebookSerializer(new_notebook)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"Failed to duplicate notebook {pk}: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ----------------------------
# File operations
# ----------------------------
@extend_schema_view(
    list=extend_schema(
        summary="List files in notebook",
        description="Get paginated list of knowledge base items (files/sources) in a notebook",
        parameters=[
            OpenApiParameter(
                name="include_incomplete",
                type=str,
                description="Include sources not yet completed in RAGFlow (1/true/yes)",
                required=False,
            ),
            OpenApiParameter(
                name="parsing_status",
                type=str,
                description="Filter by parsing status",
                required=False,
            ),
            OpenApiParameter(
                name="content_type",
                type=str,
                description="Filter by content type",
                required=False,
            ),
        ],
        responses={200: KnowledgeBaseItemSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Get file details",
        description="Retrieve details of a specific knowledge base item",
        responses={200: KnowledgeBaseItemSerializer},
    ),
    create=extend_schema(
        summary="Upload file",
        description="Upload a single file to the notebook for processing",
        request=BatchFileUploadSerializer,
        responses={201: KnowledgeBaseItemSerializer},
    ),
    update=extend_schema(
        summary="Update file",
        description="Update file metadata and properties",
        request=KnowledgeBaseItemSerializer,
        responses={200: KnowledgeBaseItemSerializer},
    ),
    partial_update=extend_schema(
        summary="Partially update file",
        description="Update specific fields of a file",
        request=KnowledgeBaseItemSerializer,
        responses={200: KnowledgeBaseItemSerializer},
    ),
    destroy=extend_schema(
        summary="Delete file",
        description="Delete a file from the notebook",
        responses={204: None},
    ),
)
class FileViewSet(ETagCacheMixin, viewsets.ModelViewSet):
    serializer_class = KnowledgeBaseItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotebookOwner]
    pagination_class = LargePageNumberPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["parsing_status", "content_type"]
    search_fields = ["title", "notes"]
    ordering_fields = ["created_at", "updated_at", "title"]
    ordering = ["-created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_service = FileService()
        self.kb_service = KnowledgeBaseService()
        self.url_service = URLService()

    def get_queryset(self):
        # Guard against schema generation
        if getattr(self, "swagger_fake_view", False):
            return KnowledgeBaseItem.objects.none()

        notebook_id = self.kwargs.get("notebook_pk") or self.kwargs.get("notebook_id")
        notebook = get_object_or_404(
            Notebook.objects.filter(user=self.request.user), pk=notebook_id
        )
        qs = KnowledgeBaseItem.objects.filter(notebook=notebook).order_by("-created_at")

        # Show all sources regardless of processing status
        # Users should see uploaded files immediately, including those still processing
        # Original filtering logic kept for reference but disabled:
        # try:
        #     include_incomplete = self.request.query_params.get("include_incomplete", "")
        #     include_flag = str(include_incomplete).lower() in {"1", "true", "yes"}
        # except Exception:
        #     include_flag = False
        #
        # if not include_flag:
        #     qs = qs.filter(ragflow_processing_status=RagflowDocStatus.COMPLETED)

        return qs

    def list(self, request, notebook_pk=None, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, notebook_pk=None, *args, **kwargs):
        serializer = BatchFileUploadSerializer(
            data=request.data, context={"request": request, "notebook_id": notebook_pk}
        )
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                notebook = get_object_or_404(
                    Notebook.objects.filter(user=request.user), pk=notebook_pk
                )

                # Handle single file upload - check both 'file' and 'files' fields
                file_obj = serializer.validated_data.get("file")
                if not file_obj and serializer.validated_data.get("files"):
                    file_obj = serializer.validated_data["files"][0]

                if not file_obj:
                    raise ValidationError("No file provided")

                upload_id = serializer.validated_data.get("upload_file_id", "")
                result = self.file_service.handle_single_file_upload(
                    file_obj=file_obj,
                    upload_id=upload_id,
                    notebook=notebook,
                    user=request.user,
                )

                return Response(
                    result, status=result.get("status_code", status.HTTP_201_CREATED)
                )
        except Exception as e:
            logger.exception(f"Failed to upload files: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="batch_upload")
    def batch_upload(self, request, notebook_pk=None):
        serializer = BatchFileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                notebook = get_object_or_404(
                    Notebook.objects.filter(user=request.user), pk=notebook_pk
                )
                files = self.file_service.handle_batch_upload(
                    user=request.user,
                    notebook=notebook,
                    items=serializer.validated_data["items"],
                )
                data = KnowledgeBaseItemSerializer(files, many=True).data
                return Response(data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"Failed to batch upload files: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="content")
    def content(self, request, notebook_pk=None, pk=None):
        item = self.get_object()
        try:
            # Optional presigned URL expiry from querystring (seconds)
            try:
                expires = int(request.GET.get("expires", "0"))
                if expires <= 0:
                    expires = 3600
            except Exception:
                expires = 3600
            content = self.kb_service.get_processed_content(item, expires=expires)
            return Response({"content": content})
        except Exception as e:
            logger.exception(f"Failed to get content for {pk}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="raw")
    def raw(self, request, notebook_pk=None, pk=None):
        item = self.get_object()
        try:
            file_obj = self.kb_service.get_raw_file(item, request.user.id)
            from infrastructure.storage.adapters import get_storage_adapter

            storage = get_storage_adapter()
            etag_value = None
            object_key = item.original_file_object_key or item.file_object_key
            if object_key:
                etag_value = self._compute_storage_etag(storage, object_key)
            if not etag_value:
                base = f"{item.id}-{item.updated_at.timestamp()}"
                etag_value = hashlib.sha1(base.encode("utf-8")).hexdigest()

            max_age = self.get_signed_url_expires(request)
            return self.build_file_response(
                request,
                filename=file_obj["filename"],
                content_type=file_obj["content_type"],
                content_bytes=file_obj["data"],
                etag=etag_value,
                max_age=max_age,
                disposition="attachment",
            )
        except Exception as e:
            logger.exception(f"Failed to get raw file for {pk}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="inline")
    def inline(self, request, notebook_pk=None, pk=None):
        item = self.get_object()
        try:
            file_obj = self.kb_service.get_raw_file(item, request.user.id)
            from infrastructure.storage.adapters import get_storage_adapter

            storage = get_storage_adapter()
            etag_value = None
            object_key = item.original_file_object_key or item.file_object_key
            if object_key:
                etag_value = self._compute_storage_etag(storage, object_key)
            if not etag_value:
                base = f"{item.id}-{item.updated_at.timestamp()}"
                etag_value = hashlib.sha1(base.encode("utf-8")).hexdigest()

            max_age = self.get_signed_url_expires(request)
            return self.build_file_response(
                request,
                filename=file_obj["filename"],
                content_type=file_obj["content_type"],
                content_bytes=file_obj["data"],
                etag=etag_value,
                max_age=max_age,
                disposition="inline",
            )
        except Exception as e:
            logger.exception(f"Failed to get inline file for {pk}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="images")
    def images(self, request, notebook_pk=None, pk=None):
        item = self.get_object()
        try:
            images = self.kb_service.get_images(item)
            return Response({"images": images})
        except Exception as e:
            logger.exception(f"Failed to get images for {pk}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path=r"image/(?P<image_id>[^/]+)/inline")
    def image_inline(self, request, notebook_pk=None, pk=None, image_id: str = None):
        """Serve an image via API as an inline response (MinIO proxy)."""
        item = self.get_object()
        try:
            from infrastructure.storage.adapters import get_storage_backend
            from .models import KnowledgeBaseImage

            image = get_object_or_404(
                KnowledgeBaseImage, id=image_id, knowledge_base_item=item
            )

            storage = get_storage_backend()
            etag_value = self._compute_storage_etag(storage, image.minio_object_key)
            if not etag_value:
                base = f"{image.id}-{getattr(image, 'updated_at', None) or getattr(image, 'created_at', None)}"
                etag_value = hashlib.sha1(base.encode("utf-8")).hexdigest()

            content = image.get_image_content()
            if content is None:
                return Response(
                    {"detail": "Image not found"}, status=status.HTTP_404_NOT_FOUND
                )

            filename = (
                image.image_metadata.get("original_filename", "image")
                if isinstance(image.image_metadata, dict)
                else "image"
            )
            return self.build_file_response(
                request,
                filename=filename,
                content_type=image.content_type or "application/octet-stream",
                content_bytes=content,
                etag=etag_value,
                max_age=300,
                disposition="inline",
            )
        except Exception as e:
            logger.exception(
                f"Failed to serve inline image {image_id} for KB item {pk}: {e}"
            )
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Parse URL",
        description="Parse a web URL and extract content for the knowledge base",
        request=URLParseSerializer,
        responses={
            201: KnowledgeBaseItemSerializer,
            400: OpenApiResponse(description="Invalid URL or parsing failed"),
        },
    )
    @action(detail=False, methods=["post"], url_path="parse_url")
    def parse_url(self, request, notebook_pk=None):
        serializer = URLParseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            from uuid import uuid4

            notebook = get_object_or_404(
                Notebook.objects.filter(user=request.user), pk=notebook_pk
            )
            url = serializer.validated_data["url"]
            upload_url_id = (
                serializer.validated_data.get("upload_url_id") or uuid4().hex
            )

            result = self.url_service.handle_single_url_parse(
                url=url,
                upload_url_id=upload_url_id,
                notebook=notebook,
                user=request.user,
            )
            return Response(
                result, status=result.get("status_code", status.HTTP_201_CREATED)
            )
        except Exception as e:
            logger.exception(f"Failed to parse URL: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Parse URL with media extraction",
        description="Parse a web URL and extract both text content and media (images/videos)",
        request=URLParseWithMediaSerializer,
        responses={
            201: KnowledgeBaseItemSerializer,
            400: OpenApiResponse(description="Invalid URL or parsing failed"),
        },
    )
    @action(detail=False, methods=["post"], url_path="parse_url_with_media")
    def parse_url_with_media(self, request, notebook_pk=None):
        serializer = URLParseWithMediaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            from uuid import uuid4

            notebook = get_object_or_404(
                Notebook.objects.filter(user=request.user), pk=notebook_pk
            )
            url = serializer.validated_data["url"]
            upload_url_id = (
                serializer.validated_data.get("upload_url_id") or uuid4().hex
            )

            result = self.url_service.handle_url_with_media(
                url=url,
                upload_url_id=upload_url_id,
                notebook=notebook,
                user=request.user,
            )
            return Response(
                result, status=result.get("status_code", status.HTTP_201_CREATED)
            )
        except Exception as e:
            logger.exception(f"Failed to parse URL with media: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Parse document URL",
        description="Parse a URL pointing to a document (PDF, DOC, etc.) and extract content",
        request=URLParseDocumentSerializer,
        responses={
            201: KnowledgeBaseItemSerializer,
            400: OpenApiResponse(description="Invalid document URL or parsing failed"),
        },
    )
    @action(detail=False, methods=["post"], url_path="parse_document_url")
    def parse_document_url(self, request, notebook_pk=None):
        serializer = URLParseDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            from uuid import uuid4

            notebook = get_object_or_404(
                Notebook.objects.filter(user=request.user), pk=notebook_pk
            )
            url = serializer.validated_data["url"]
            upload_url_id = (
                serializer.validated_data.get("upload_url_id") or uuid4().hex
            )

            result = self.url_service.handle_document_url(
                url=url,
                upload_url_id=upload_url_id,
                notebook=notebook,
                user=request.user,
            )
            return Response(
                result, status=result.get("status_code", status.HTTP_201_CREATED)
            )
        except Exception as e:
            logger.exception(f"Failed to parse document URL: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Batch parse URLs",
        description="Parse multiple web URLs in batch. Each URL will be processed asynchronously.",
        request=BatchURLParseSerializer,
        responses={
            207: OpenApiResponse(description="Multi-status - partial success"),
            202: OpenApiResponse(description="All URLs accepted for processing"),
            400: OpenApiResponse(description="Invalid request"),
        },
    )
    @action(detail=False, methods=["post"], url_path="batch_parse_url")
    def batch_parse_url(self, request, notebook_pk=None):
        """Parse multiple URLs in batch."""
        serializer = BatchURLParseSerializer(
            data=request.data,
            context={
                "request": request,
                "notebook_id": notebook_pk,
            },
        )
        serializer.is_valid(raise_exception=True)
        try:
            from uuid import uuid4

            notebook = get_object_or_404(
                Notebook.objects.filter(user=request.user), pk=notebook_pk
            )

            # Get URL or URLs from validated data
            url = serializer.validated_data.get("url")
            urls = serializer.validated_data.get("urls")
            upload_url_id = (
                serializer.validated_data.get("upload_url_id") or uuid4().hex
            )

            # Convert single URL to list for uniform processing
            urls_to_process = [url] if url else urls

            result = self.url_service.handle_batch_url_parse(
                urls=urls_to_process,
                upload_url_id=upload_url_id,
                notebook=notebook,
                user=request.user,
            )
            return Response(
                result, status=result.get("status_code", status.HTTP_202_ACCEPTED)
            )
        except Exception as e:
            logger.exception(f"Failed to batch parse URLs: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Batch parse URLs with media extraction",
        description="Parse multiple web URLs with media extraction in batch. Each URL will be processed asynchronously.",
        request=BatchURLParseWithMediaSerializer,
        responses={
            207: OpenApiResponse(description="Multi-status - partial success"),
            202: OpenApiResponse(description="All URLs accepted for processing"),
            400: OpenApiResponse(description="Invalid request"),
        },
    )
    @action(detail=False, methods=["post"], url_path="batch_parse_url_with_media")
    def batch_parse_url_with_media(self, request, notebook_pk=None):
        """Parse multiple URLs with media extraction in batch."""
        serializer = BatchURLParseWithMediaSerializer(
            data=request.data,
            context={
                "request": request,
                "notebook_id": notebook_pk,
            },
        )
        serializer.is_valid(raise_exception=True)
        try:
            from uuid import uuid4

            notebook = get_object_or_404(
                Notebook.objects.filter(user=request.user), pk=notebook_pk
            )

            # Get URL or URLs from validated data
            url = serializer.validated_data.get("url")
            urls = serializer.validated_data.get("urls")
            upload_url_id = (
                serializer.validated_data.get("upload_url_id") or uuid4().hex
            )

            # Convert single URL to list for uniform processing
            urls_to_process = [url] if url else urls

            result = self.url_service.handle_batch_url_with_media(
                urls=urls_to_process,
                upload_url_id=upload_url_id,
                notebook=notebook,
                user=request.user,
            )
            return Response(
                result, status=result.get("status_code", status.HTTP_202_ACCEPTED)
            )
        except Exception as e:
            logger.exception(f"Failed to batch parse URLs with media: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Batch parse document URLs",
        description="Parse multiple document URLs in batch. Each URL will be processed asynchronously.",
        request=BatchURLParseDocumentSerializer,
        responses={
            207: OpenApiResponse(description="Multi-status - partial success"),
            202: OpenApiResponse(description="All URLs accepted for processing"),
            400: OpenApiResponse(description="Invalid request"),
        },
    )
    @action(detail=False, methods=["post"], url_path="batch_parse_document_url")
    def batch_parse_document_url(self, request, notebook_pk=None):
        """Parse multiple document URLs in batch."""
        serializer = BatchURLParseDocumentSerializer(
            data=request.data,
            context={
                "request": request,
                "notebook_id": notebook_pk,
            },
        )
        serializer.is_valid(raise_exception=True)
        try:
            from uuid import uuid4

            notebook = get_object_or_404(
                Notebook.objects.filter(user=request.user), pk=notebook_pk
            )

            # Get URL or URLs from validated data
            url = serializer.validated_data.get("url")
            urls = serializer.validated_data.get("urls")
            upload_url_id = (
                serializer.validated_data.get("upload_url_id") or uuid4().hex
            )

            # Convert single URL to list for uniform processing
            urls_to_process = [url] if url else urls

            result = self.url_service.handle_batch_document_url(
                urls=urls_to_process,
                upload_url_id=upload_url_id,
                notebook=notebook,
                user=request.user,
            )
            return Response(
                result, status=result.get("status_code", status.HTTP_202_ACCEPTED)
            )
        except Exception as e:
            logger.exception(f"Failed to batch parse document URLs: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="extract_video_images")
    def extract_video_images(self, request, notebook_pk=None):
        serializer = VideoImageExtractionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            notebook = get_object_or_404(
                Notebook.objects.filter(user=request.user), pk=notebook_pk
            )
            images = self.kb_service.extract_video_images(
                user=request.user,
                notebook=notebook,
                video_url=serializer.validated_data["video_url"],
                interval_seconds=serializer.validated_data.get("interval_seconds"),
            )
            return Response({"images": images})
        except Exception as e:
            logger.exception(f"Failed to extract video images: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def perform_destroy(self, instance):
        """
        Handle file deletion with proper cleanup of storage and RagFlow documents.

        Only allows deletion of files in 'done' or 'failed' status to prevent
        deletion of files currently being processed.

        Order of operations (handled by Django signals):
        1. Delete RagFlow document immediately (while IDs are still available)
        2. Delete the database record
        3. Delete MinIO files after transaction commit

        The actual cleanup is handled by Django signals (delete_kb_files_on_pre_delete).
        """
        try:
            # Validate file status before deletion
            processing_statuses = [
                ParsingStatus.QUEUEING,
                ParsingStatus.PARSING,
                ParsingStatus.CAPTIONING,
            ]
            if instance.parsing_status in processing_statuses:
                from rest_framework.exceptions import ValidationError

                raise ValidationError(
                    {
                        "detail": f"Cannot delete file while it is being processed. Current status: {instance.parsing_status}",
                        "parsing_status": instance.parsing_status,
                        "file_id": str(instance.id),
                        "file_title": instance.title,
                    }
                )

            logger.info(
                f"Deleting file '{instance.title}' (ID: {instance.id}, status: {instance.parsing_status}) from notebook {instance.notebook.id}"
            )

            # Log the deletion for audit purposes
            ragflow_doc_info = ""
            if instance.ragflow_document_id and instance.notebook.ragflow_dataset_id:
                ragflow_doc_info = f" and RagFlow document {instance.ragflow_document_id} from dataset {instance.notebook.ragflow_dataset_id}"

            logger.info(
                f"File deletion will clean up RagFlow document first, then MinIO storage{ragflow_doc_info}"
            )

            # If the KB item is linked to RagFlow, attempt deletion up-front so we can fail fast
            if instance.ragflow_document_id and instance.notebook.ragflow_dataset_id:
                try:
                    from infrastructure.ragflow.service import get_ragflow_service

                    ragflow_service = get_ragflow_service()
                    logger.info(
                        f"[FileViewSet.perform_destroy] Deleting RagFlow document {instance.ragflow_document_id} from dataset {instance.notebook.ragflow_dataset_id}"
                    )
                    success = ragflow_service.delete_document(
                        instance.notebook.ragflow_dataset_id,
                        instance.ragflow_document_id,
                    )
                    if not success:
                        from rest_framework.exceptions import ValidationError

                        raise ValidationError(
                            {
                                "detail": "Failed to delete RagFlow document",
                                "ragflow_document_id": instance.ragflow_document_id,
                                "ragflow_dataset_id": instance.notebook.ragflow_dataset_id,
                            }
                        )

                    # Mark on the instance so the pre_delete signal skips duplicate deletion
                    setattr(instance, "_ragflow_deleted", True)

                    # Best-effort dataset update after document deletion
                    try:
                        ragflow_service.update_dataset(
                            instance.notebook.ragflow_dataset_id
                        )
                    except Exception:
                        logger.warning(
                            f"[FileViewSet.perform_destroy] Dataset update failed for {instance.notebook.ragflow_dataset_id}",
                            exc_info=True,
                        )

                except Exception as e:
                    logger.exception(
                        f"[FileViewSet.perform_destroy] Error deleting RagFlow document {instance.ragflow_document_id}: {e}"
                    )
                    raise

            # Delete the instance - signals will handle RAGFlow deletion first, then MinIO cleanup
            instance.delete()

        except Exception as e:
            logger.exception(f"Failed to delete file {instance.id}: {e}")
            raise


# ----------------------------
# Knowledge base and batch jobs
# ----------------------------
class KnowledgeBaseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = KnowledgeBaseItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotebookOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["content_type", "parsing_status"]

    def get_queryset(self):
        # Guard against schema generation
        if getattr(self, "swagger_fake_view", False):
            return KnowledgeBaseItem.objects.none()

        notebook_id = self.kwargs.get("notebook_pk") or self.kwargs.get("notebook_id")
        return KnowledgeBaseItem.objects.filter(
            notebook__id=notebook_id, notebook__user=self.request.user
        ).order_by("-created_at")


class BatchJobViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BatchJobSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotebookOwner]

    def get_queryset(self):
        # Guard against schema generation
        if getattr(self, "swagger_fake_view", False):
            return BatchJob.objects.none()

        notebook_id = self.kwargs.get("notebook_pk") or self.kwargs.get("notebook_id")
        return BatchJob.objects.filter(
            notebook__id=notebook_id, notebook__user=self.request.user
        ).order_by("-created_at")


class ChatModelsView(APIView):
    """
    List and update available chat models for notebook chat.

    - GET: return available models and current model for a notebook
    - POST: update the model used by the RagFlow chat assistant for this notebook
    """

    permission_classes = [permissions.IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_service = ChatService()

    def _get_notebook(self, request, notebook_id: str) -> Notebook:
        return get_object_or_404(
            Notebook.objects.filter(user=request.user), pk=notebook_id
        )

    def get(self, request, notebook_id: str):
        notebook = self._get_notebook(request, notebook_id)

        available_models = self.chat_service.get_available_chat_models()
        current_model_result = self.chat_service.get_current_chat_model(
            notebook, request.user.id
        )

        current_model = (
            current_model_result.get("model")
            if current_model_result.get("success")
            else None
        )

        return Response(
            {
                "available_models": available_models,
                "default_model": getattr(settings, "RAGFLOW_CHAT_MODEL", None),
                "current_model": current_model,
            }
        )

    def post(self, request, notebook_id: str):
        notebook = self._get_notebook(request, notebook_id)
        model_name = (request.data or {}).get("model")

        if not model_name or not isinstance(model_name, str):
            return Response(
                {"detail": "Field 'model' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = self.chat_service.update_chat_model(
            notebook=notebook, user_id=request.user.id, model_name=model_name
        )

        if not result.get("success"):
            return Response(
                {"detail": result.get("error") or "Failed to update chat model"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        available_models = self.chat_service.get_available_chat_models()
        return Response(
            {
                "available_models": available_models,
                "default_model": getattr(settings, "RAGFLOW_CHAT_MODEL", None),
                "current_model": result.get("model"),
            }
        )


# ----------------------------
# Chat sessions
# ----------------------------
class SessionChatViewSet(viewsets.ModelViewSet):
    class ChatSessionSerializer(serializers.ModelSerializer):
        message_count = serializers.SerializerMethodField()
        created_at = serializers.DateTimeField(source="started_at", read_only=True)

        class Meta:
            model = ChatSession
            fields = [
                "id",
                "title",
                "status",
                "message_count",
                "created_at",
                "last_activity",
            ]

        def get_message_count(self, obj):
            return obj.messages.count() if hasattr(obj, "messages") else 0

    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotebookOwner]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_service = ChatService()

    def get_queryset(self):
        # Guard against schema generation
        if getattr(self, "swagger_fake_view", False):
            return ChatSession.objects.none()

        notebook_id = self.kwargs.get("notebook_pk")
        notebook = get_object_or_404(
            Notebook.objects.filter(user=self.request.user), pk=notebook_id
        )

        # Filter by include_closed parameter
        queryset = ChatSession.objects.filter(notebook=notebook)
        include_closed = (
            self.request.query_params.get("include_closed", "false").lower() == "true"
        )
        if not include_closed:
            queryset = queryset.filter(status="active")

        queryset = queryset.order_by("-last_activity")
        logger.info(
            f"[SessionChatViewSet] Returning {queryset.count()} sessions for notebook {notebook_id}"
        )
        return queryset

    def retrieve(self, request, *args, **kwargs):
        """Get session details including messages."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Get messages for this session
        messages = instance.messages.all().order_by("message_order", "timestamp")
        messages_data = [
            {
                "id": msg.id,
                "sender": msg.sender,
                "message": msg.message,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata,
            }
            for msg in messages
        ]

        return Response(
            {"success": True, "session": {**serializer.data, "messages": messages_data}}
        )

    def perform_create(self, serializer):
        """Create a chat session with proper RagFlow integration."""
        notebook_id = self.kwargs.get("notebook_pk")
        notebook = get_object_or_404(
            Notebook.objects.filter(user=self.request.user), pk=notebook_id
        )

        # Get title from validated data
        title = serializer.validated_data.get("title", "New Chat")

        # Use ChatService to create session with RagFlow integration
        result = self.chat_service.create_chat_session(
            notebook=notebook, user_id=self.request.user.id, title=title
        )

        if not result.get("success"):
            error_msg = result.get("error", "Failed to create chat session")
            raise ValidationError(error_msg)

        # Get the created session from database
        session_data = result.get("session", {})
        session_id = session_data.get("id")

        if session_id:
            # Get the actual ChatSession instance
            chat_session = ChatSession.objects.get(session_id=session_id)
            # Set the instance on the serializer
            serializer.instance = chat_session
        else:
            raise ValidationError("Session was created but ID not returned")

    @action(detail=True, methods=["post"], url_path="messages")
    def send_message(self, request, notebook_pk=None, pk=None):
        session = self.get_object()

        class ChatMessageSerializer(serializers.Serializer):
            message = serializers.CharField()

        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            notebook = get_object_or_404(
                Notebook.objects.filter(user=request.user), pk=notebook_pk
            )

            message = serializer.validated_data["message"]
            logger.info(
                f"Received chat message for session {session.session_id}: {message[:100]}"
            )

            # Create streaming response using ChatService
            stream = self.chat_service.create_session_chat_stream(
                session_id=str(session.session_id),
                notebook=notebook,
                user_id=request.user.id,
                question=message,
            )

            response = StreamingHttpResponse(stream, content_type="text/event-stream")
            response["Cache-Control"] = "no-cache"
            response["X-Accel-Buffering"] = "no"
            return response
        except Exception as e:
            logger.exception(f"Failed to send message: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ----------------------------
# SSE views
# ----------------------------
class FileStatusSSEView(View):
    @method_decorator(csrf_exempt)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def options(self, request, notebook_id: str, file_id: str):
        response = HttpResponse()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Accept, Authorization, Content-Type"
        return response

    def get(self, request, notebook_id: str, file_id: str):
        try:
            notebook = get_object_or_404(
                Notebook.objects.filter(user=request.user), pk=notebook_id
            )

            # Handle both upload IDs and UUID file IDs
            import re

            is_uuid = re.match(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
                file_id,
                re.IGNORECASE,
            )

            if is_uuid:
                # It's a UUID, look up by primary key
                file_item = get_object_or_404(
                    KnowledgeBaseItem.objects.filter(notebook=notebook), pk=file_id
                )
            else:
                # It's an upload ID, look up by title or create a placeholder response
                try:
                    file_item = KnowledgeBaseItem.objects.filter(
                        notebook=notebook, title__icontains=file_id
                    ).first()
                    if not file_item:
                        # Return a "not found yet" SSE stream for upload IDs that haven't been processed
                        return self._generate_upload_pending_stream(file_id)
                except Exception:
                    return self._generate_upload_pending_stream(file_id)

            response = StreamingHttpResponse(
                self.generate_file_status_stream(file_item),
                content_type="text/event-stream",
            )
            response["Cache-Control"] = "no-cache"
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Headers"] = (
                "Accept, Authorization, Content-Type"
            )
            response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            return response

        except Exception as e:
            logger.exception(f"Failed to create file status SSE stream: {e}")
            return HttpResponse(
                f"Error: {str(e)}", status=500, content_type="text/plain"
            )

    def generate_file_status_stream(
        self, file_item: KnowledgeBaseItem
    ) -> Generator[str, None, None]:
        try:
            max_iterations = 60
            iteration = 0
            logger.info(f"Starting SSE stream for file {file_item.id}")
            while iteration < max_iterations:
                file_item.refresh_from_db()
                status_data = self.build_status_data(file_item)
                sse_message = {"type": "file_status", "data": status_data}
                yield f"data: {json.dumps(sse_message)}\n\n"

                parsing_done = file_item.parsing_status in ["done", "failed"]
                caption_done = status_data.get("caption_status") in [
                    "completed",
                    "failed",
                    None,
                ]
                ragflow_done = status_data.get("ragflow_processing_status") in [
                    "completed",
                    "failed",
                    None,
                ]

                # Only close when parsing is done AND (no caption processing OR caption is done) AND (no ragflow OR ragflow is done)
                if parsing_done and caption_done and ragflow_done:
                    logger.info(
                        f"File {file_item.id} all processing finished - parsing: {file_item.parsing_status}, "
                        f"caption: {status_data.get('caption_status')}, ragflow: {status_data.get('ragflow_processing_status')}"
                    )
                    close_message = {"type": "close"}
                    yield f"data: {json.dumps(close_message)}\n\n"
                    break
                iteration += 1
                time.sleep(5)
            if iteration >= max_iterations:
                logger.warning(
                    f"SSE stream for file {file_item.id} reached max iterations"
                )
                timeout_message = {
                    "type": "timeout",
                    "message": "Status monitoring timed out",
                }
                yield f"data: {json.dumps(timeout_message)}\n\n"
        except Exception as e:
            logger.exception(
                f"Error in SSE stream generation for file {file_item.id}: {e}"
            )
            error_message = {"type": "error", "message": f"Stream error: {str(e)}"}
            yield f"data: {json.dumps(error_message)}\n\n"

    def build_status_data(self, file_item: KnowledgeBaseItem) -> dict[str, Any]:
        # Use the raw parsing_status for frontend consistency
        # Frontend expects: "queueing", "parsing", "captioning", "done", "failed"
        raw_status = file_item.parsing_status or "queueing"

        return {
            "file_id": str(file_item.id),
            "status": raw_status,  # Send raw status for frontend consistency
            "title": file_item.title,
            "content_type": file_item.content_type,
            "created_at": file_item.created_at.isoformat()
            if file_item.created_at
            else None,
            "updated_at": file_item.updated_at.isoformat()
            if file_item.updated_at
            else None,
            "has_content": bool(file_item.content),
            "processing_status": raw_status,  # Also include in processing_status for compatibility
            "metadata": file_item.metadata or {},
            "captioning_status": file_item.captioning_status,  # Use actual captioning_status field
            "ragflow_processing_status": file_item.ragflow_processing_status,  # Include RagFlow status
        }

    def _generate_upload_pending_stream(self, upload_id: str):
        """Generate SSE stream for upload IDs that haven't been processed yet"""

        def generate_pending_stream():
            # Send a few "processing" messages then close
            for _i in range(3):
                yield f"data: {json.dumps({'type': 'file_status', 'data': {'file_id': upload_id, 'status': 'processing', 'title': f'Upload {upload_id}', 'updated_at': None}})}\n\n"
                time.sleep(1)
            # Send close message
            yield f"data: {json.dumps({'type': 'close', 'message': 'Upload not found'})}\n\n"

        response = StreamingHttpResponse(
            generate_pending_stream(), content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Accept, Authorization, Content-Type"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        return response


class NotebookJobsSSEView(View):
    """
    SSE endpoint for real-time job status updates (podcasts and reports).

    Subscribes to Redis Pub/Sub channel: sse:notebook:{notebook_id}
    Streams job events (STARTED, SUCCESS, FAILURE, CANCELLED) to the client.
    """

    MAX_DURATION_SECONDS = 600  # 10 minutes max connection time
    HEARTBEAT_INTERVAL = 30  # Send heartbeat every 30 seconds

    @method_decorator(csrf_exempt)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def options(self, request, notebook_id: str):
        response = HttpResponse()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Accept, Authorization, Content-Type"
        return response

    def get(self, request, notebook_id: str):
        """Stream job events for a specific notebook."""
        try:
            # Verify notebook ownership
            get_object_or_404(
                Notebook.objects.filter(user=request.user), pk=notebook_id
            )

            logger.info(
                f"Starting job stream for notebook {notebook_id}, user {request.user.id}"
            )

            response = StreamingHttpResponse(
                self.generate_job_stream(notebook_id), content_type="text/event-stream"
            )
            response["Cache-Control"] = "no-cache"
            response["X-Accel-Buffering"] = "no"  # Disable nginx buffering
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Headers"] = (
                "Accept, Authorization, Content-Type"
            )
            response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            return response

        except Exception as e:
            logger.exception(f"Failed to create job SSE stream: {e}")
            return HttpResponse(
                f"Error: {str(e)}", status=500, content_type="text/plain"
            )

    def generate_job_stream(self, notebook_id: str) -> Generator[str, None, None]:
        """
        Generate SSE stream by subscribing to Redis Pub/Sub channel.

        Yields:
            SSE formatted messages with job status updates
        """
        redis_client = None
        pubsub = None

        try:
            # Connect to Redis
            redis_client = redis.Redis.from_url(
                settings.CELERY_BROKER_URL, decode_responses=True
            )
            pubsub = redis_client.pubsub()

            # Subscribe to notebook channel
            channel = f"sse:notebook:{notebook_id}"
            pubsub.subscribe(channel)

            logger.info(f"Subscribed to Redis channel: {channel}")

            # Send initial connection message (ensure UUID is JSON-serializable)
            yield f"data: {json.dumps({'type': 'connected', 'notebookId': str(notebook_id)})}\n\n"

            start_time = time.time()
            last_heartbeat = start_time
            last_event_data = None

            # Listen for messages with timeout
            while True:
                # Check max duration
                elapsed = time.time() - start_time
                if elapsed > self.MAX_DURATION_SECONDS:
                    logger.info(
                        f"Job stream for notebook {notebook_id} reached max duration"
                    )
                    yield f"data: {json.dumps({'type': 'timeout', 'message': 'Stream timeout'})}\n\n"
                    break

                # Get message with timeout
                message = pubsub.get_message(timeout=1.0)

                if message and message["type"] == "message":
                    # Forward the event to client, but avoid duplicate sends of identical payloads
                    event_data = message["data"]
                    if event_data != last_event_data:
                        yield f"data: {event_data}\n\n"
                        last_event_data = event_data
                        logger.debug(f"Forwarded event: {event_data}")
                    last_heartbeat = time.time()

                # Send heartbeat if idle
                elif time.time() - last_heartbeat > self.HEARTBEAT_INTERVAL:
                    yield ": heartbeat\n\n"
                    last_heartbeat = time.time()

        except GeneratorExit:
            logger.info(
                f"Client disconnected from job stream for notebook {notebook_id}"
            )

        except Exception as e:
            logger.exception(f"Error in job stream for notebook {notebook_id}: {e}")
            try:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            except:
                pass

        finally:
            # Clean up Redis connection
            if pubsub:
                try:
                    pubsub.unsubscribe()
                    pubsub.close()
                except:
                    pass

            if redis_client:
                try:
                    redis_client.close()
                except:
                    pass

            logger.info(f"Closed job stream for notebook {notebook_id}")
