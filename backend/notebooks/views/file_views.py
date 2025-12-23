"""
File operation views for uploads and URL parsing
"""

import hashlib
import logging
from typing import Any

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import (
    permissions,
    serializers,
    status,
    viewsets,
    filters,
    authentication,
)
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiResponse,
)

from core.pagination import LargePageNumberPagination
from core.permissions import IsNotebookOwner
from ..models import KnowledgeBaseItem, Notebook
from ..serializers import (
    BatchFileUploadSerializer,
    BatchURLParseDocumentSerializer,
    BatchURLParseSerializer,
    BatchURLParseWithMediaSerializer,
    KnowledgeBaseItemSerializer,
    URLParseDocumentSerializer,
    URLParseSerializer,
    URLParseWithMediaSerializer,
    VideoImageExtractionSerializer,
)
from ..services import FileService, KnowledgeBaseService, URLService
from ..utils.view_mixins import ETagCacheMixin
from ..constants import ParsingStatus, RagflowDocStatus

logger = logging.getLogger(__name__)


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
                disposition="inline",
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
