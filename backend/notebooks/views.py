"""
Notebooks views (consolidated).

This file merges all notebook-related views and viewsets, replacing the
previous notebooks/views/* modules.
"""

import json
import logging
import time
from typing import Any, Generator, Dict

from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.http import http_date
import hashlib

from rest_framework import viewsets, permissions, status, filters, authentication, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Notebook,
    KnowledgeBaseItem,
    BatchJob,
    ChatSession,
)
from .serializers import (
    NotebookSerializer,
    NotebookListSerializer,
    NotebookCreateSerializer,
    NotebookUpdateSerializer,
    FileUploadSerializer,
    BatchFileUploadSerializer,
    KnowledgeBaseItemSerializer,
    BatchJobSerializer,
    URLParseSerializer,
    URLParseWithMediaSerializer,
    URLParseDocumentSerializer,
    VideoImageExtractionSerializer,
)
from .services import NotebookService, FileService, KnowledgeBaseService, ChatService
from core.permissions import IsOwnerPermission, IsNotebookOwner
from core.pagination import NotebookPagination, LargePageNumberPagination

logger = logging.getLogger(__name__)


# ----------------------------
# Notebook CRUD and operations
# ----------------------------
class NotebookViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOwnerPermission]
    authentication_classes = [
        authentication.SessionAuthentication,
        authentication.TokenAuthentication,
    ]
    pagination_class = NotebookPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
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
            validated_data = serializer.validated_data
            notebook = self.notebook_service.create_notebook(
                user=self.request.user,
                name=validated_data['name'],
                description=validated_data.get('description', '')
            )

            # Update the serializer's instance with the created notebook
            serializer.instance = notebook

        except Exception as e:
            logger.exception(f"Failed to create notebook: {e}")
            raise

    def perform_destroy(self, instance):
        """
        Use the service layer to delete notebook with RAGFlow cleanup.
        """
        try:
            # Use service layer for proper RAGFlow cleanup
            stats = self.notebook_service.delete_notebook(
                notebook_id=str(instance.id),
                user=self.request.user
            )
            logger.info(f"Notebook {instance.id} deleted successfully with stats: {stats}")
        except Exception as e:
            logger.exception(f"Failed to delete notebook {instance.id}: {e}")
            raise

    @action(detail=True, methods=["get"], url_path="stats")
    def stats(self, request, pk=None):
        notebook = self.get_object()
        try:
            stats = self.notebook_service.get_notebook_stats(notebook)
            return Response(stats)
        except Exception as e:
            logger.exception(f"Failed to get notebook stats for {pk}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ----------------------------
# File operations
# ----------------------------
class FileViewSet(viewsets.ModelViewSet):
    serializer_class = KnowledgeBaseItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotebookOwner]
    pagination_class = LargePageNumberPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["parsing_status", "content_type"]
    search_fields = ["title", "notes"]
    ordering_fields = ["created_at", "updated_at", "title"]
    ordering = ["-created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_service = FileService()
        self.kb_service = KnowledgeBaseService()

    def get_queryset(self):
        notebook_id = self.kwargs.get("notebook_pk") or self.kwargs.get("notebook_id")
        notebook = get_object_or_404(Notebook.objects.filter(user=self.request.user), pk=notebook_id)
        return KnowledgeBaseItem.objects.filter(notebook=notebook).order_by("-created_at")

    def list(self, request, notebook_pk=None, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, notebook_pk=None, *args, **kwargs):
        serializer = BatchFileUploadSerializer(data=request.data, context={'request': request, 'notebook_id': notebook_pk})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                notebook = get_object_or_404(Notebook.objects.filter(user=request.user), pk=notebook_pk)
                
                # Handle single file upload - check both 'file' and 'files' fields
                file_obj = serializer.validated_data.get("file")
                if not file_obj and serializer.validated_data.get("files"):
                    file_obj = serializer.validated_data["files"][0]
                    
                if not file_obj:
                    raise ValidationError("No file provided")
                
                upload_id = serializer.validated_data.get('upload_file_id', '')
                result = self.file_service.handle_single_file_upload(
                    file_obj=file_obj,
                    upload_id=upload_id,
                    notebook=notebook,
                    user=request.user,
                )
                
                return Response(result, status=result.get('status_code', status.HTTP_201_CREATED))
        except Exception as e:
            logger.exception(f"Failed to upload files: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="batch_upload")
    def batch_upload(self, request, notebook_pk=None):
        serializer = BatchFileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                notebook = get_object_or_404(Notebook.objects.filter(user=request.user), pk=notebook_pk)
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
                expires = int(request.GET.get('expires', '0'))
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
            file_obj = self.kb_service.get_raw_file(item)
            response = HttpResponse(file_obj["data"], content_type=file_obj["content_type"])
            response["Content-Disposition"] = f"attachment; filename=\"{file_obj['filename']}\""
            return response
        except Exception as e:
            logger.exception(f"Failed to get raw file for {pk}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="inline")
    def inline(self, request, notebook_pk=None, pk=None):
        item = self.get_object()
        try:
            file_obj = self.kb_service.get_raw_file(item)
            response = HttpResponse(file_obj["data"], content_type=file_obj["content_type"])
            response["Content-Disposition"] = f"inline; filename=\"{file_obj['filename']}\""
            response["X-Content-Type-Options"] = "nosniff"
            return response
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
            from .models import KnowledgeBaseImage
            from infrastructure.storage.adapters import get_storage_backend
            image = get_object_or_404(KnowledgeBaseImage, id=image_id, knowledge_base_item=item)
            # Compute ETag from storage metadata or fallback to a hash of identifiers
            storage = get_storage_backend()
            etag_value = None
            try:
                meta = storage.get_file_metadata(image.minio_object_key)
                if meta and isinstance(meta, dict):
                    etag_value = meta.get('etag')
            except Exception:
                etag_value = None
            if not etag_value:
                base = f"{image.id}-{getattr(image, 'updated_at', None) or getattr(image, 'created_at', None)}"
                etag_value = hashlib.sha1(base.encode('utf-8')).hexdigest()
            # Normalize ETag header value (quoted strong ETag)
            etag_header = etag_value if etag_value.startswith('W/"') or etag_value.startswith('"') else f'"{etag_value}"'

            # Handle If-None-Match for conditional GET
            inm = request.headers.get('If-None-Match') or request.META.get('HTTP_IF_NONE_MATCH')
            if inm:
                # Normalize comparison by stripping quotes and weak validators
                def norm(v: str) -> str:
                    return v.strip().lstrip('W/').strip('"')
                if norm(inm) == norm(etag_header):
                    resp = HttpResponse(status=304)
                    resp["ETag"] = etag_header
                    resp["Cache-Control"] = "private, max-age=300"
                    dt = getattr(image, 'updated_at', None) or getattr(image, 'created_at', None)
                    if dt:
                        try:
                            resp["Last-Modified"] = http_date(dt.timestamp())
                        except Exception:
                            pass
                    return resp
            content = image.get_image_content()
            if content is None:
                return Response({"detail": "Image not found"}, status=status.HTTP_404_NOT_FOUND)
            resp = HttpResponse(content, content_type=image.content_type or 'application/octet-stream')
            resp["Content-Disposition"] = f"inline; filename=\"{image.image_metadata.get('original_filename', 'image')}\"" if isinstance(image.image_metadata, dict) else "inline"
            resp["X-Content-Type-Options"] = "nosniff"
            # Add short-lived caching to reduce repeated loads
            resp["Cache-Control"] = "private, max-age=300"
            # Use updated_at or created_at for Last-Modified
            dt = getattr(image, 'updated_at', None) or getattr(image, 'created_at', None)
            if dt:
                try:
                    resp["Last-Modified"] = http_date(dt.timestamp())
                except Exception:
                    pass
            resp["ETag"] = etag_header
            return resp
        except Exception as e:
            logger.exception(f"Failed to serve inline image {image_id} for KB item {pk}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="parse_url")
    def parse_url(self, request, notebook_pk=None):
        serializer = URLParseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            notebook = get_object_or_404(Notebook.objects.filter(user=request.user), pk=notebook_pk)
            item = self.kb_service.parse_url(
                user=request.user,
                notebook=notebook,
                url=serializer.validated_data["url"],
                notes=serializer.validated_data.get("notes", ""),
            )
            return Response(KnowledgeBaseItemSerializer(item).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"Failed to parse URL: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="parse_url_with_media")
    def parse_url_with_media(self, request, notebook_pk=None):
        serializer = URLParseWithMediaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            notebook = get_object_or_404(Notebook.objects.filter(user=request.user), pk=notebook_pk)
            item = self.kb_service.parse_url_with_media(
                user=request.user,
                notebook=notebook,
                url=serializer.validated_data["url"],
                notes=serializer.validated_data.get("notes", ""),
            )
            return Response(KnowledgeBaseItemSerializer(item).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"Failed to parse URL with media: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="parse_document_url")
    def parse_document_url(self, request, notebook_pk=None):
        serializer = URLParseDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            notebook = get_object_or_404(Notebook.objects.filter(user=request.user), pk=notebook_pk)
            item = self.kb_service.parse_document_url(
                user=request.user,
                notebook=notebook,
                url=serializer.validated_data["url"],
                notes=serializer.validated_data.get("notes", ""),
            )
            return Response(KnowledgeBaseItemSerializer(item).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(f"Failed to parse document URL: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="extract_video_images")
    def extract_video_images(self, request, notebook_pk=None):
        serializer = VideoImageExtractionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            notebook = get_object_or_404(Notebook.objects.filter(user=request.user), pk=notebook_pk)
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


# ----------------------------
# Knowledge base and batch jobs
# ----------------------------
class KnowledgeBaseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = KnowledgeBaseItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotebookOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["content_type", "parsing_status"]

    def get_queryset(self):
        notebook_id = self.kwargs.get("notebook_pk") or self.kwargs.get("notebook_id")
        return KnowledgeBaseItem.objects.filter(
            notebook__id=notebook_id, notebook__user=self.request.user
        ).order_by("-created_at")


class BatchJobViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BatchJobSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotebookOwner]

    def get_queryset(self):
        notebook_id = self.kwargs.get("notebook_pk") or self.kwargs.get("notebook_id")
        return BatchJob.objects.filter(
            notebook__id=notebook_id, notebook__user=self.request.user
        ).order_by("-created_at")


# ----------------------------
# Chat sessions
# ----------------------------
class SessionChatViewSet(viewsets.ModelViewSet):
    class ChatSessionSerializer(serializers.ModelSerializer):
        class Meta:
            model = ChatSession
            fields = [
                "id",
                "session_id",
                "title",
                "status",
                "ragflow_session_id",
                "ragflow_agent_id",
                "session_metadata",
                "last_activity",
                "started_at",
                "ended_at",
            ]

    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotebookOwner]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_service = ChatService()

    def get_queryset(self):
        notebook_id = self.kwargs.get("notebook_pk")
        notebook = get_object_or_404(Notebook.objects.filter(user=self.request.user), pk=notebook_id)
        return ChatSession.objects.filter(notebook=notebook).order_by("-last_activity")

    @action(detail=True, methods=["post"], url_path="messages")
    def send_message(self, request, notebook_pk=None, pk=None):
        session = self.get_object()
        class ChatMessageSerializer(serializers.Serializer):
            message = serializers.CharField()

        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reply = self.chat_service.send_message(session, serializer.validated_data["message"], request.user)
            return Response({"reply": reply})
        except Exception as e:
            logger.exception(f"Failed to send message: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SessionAgentInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotebookOwner]

    def get(self, request, notebook_pk=None):
        notebook = get_object_or_404(Notebook.objects.filter(user=request.user), pk=notebook_pk)
        info = ChatService().get_agent_info(notebook)
        return Response(info)


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
            notebook = get_object_or_404(Notebook.objects.filter(user=request.user), pk=notebook_id)
            
            # Handle both upload IDs and UUID file IDs
            import re
            is_uuid = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', file_id, re.IGNORECASE)
            
            if is_uuid:
                # It's a UUID, look up by primary key
                file_item = get_object_or_404(KnowledgeBaseItem.objects.filter(notebook=notebook), pk=file_id)
            else:
                # It's an upload ID, look up by title or create a placeholder response
                try:
                    file_item = KnowledgeBaseItem.objects.filter(notebook=notebook, title__icontains=file_id).first()
                    if not file_item:
                        # Return a "not found yet" SSE stream for upload IDs that haven't been processed
                        return self._generate_upload_pending_stream(file_id)
                except Exception:
                    return self._generate_upload_pending_stream(file_id)

            response = StreamingHttpResponse(
                self.generate_file_status_stream(file_item), content_type="text/event-stream"
            )
            response["Cache-Control"] = "no-cache"
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Headers"] = "Accept, Authorization, Content-Type"
            response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            return response

        except Exception as e:
            logger.exception(f"Failed to create file status SSE stream: {e}")
            return HttpResponse(f"Error: {str(e)}", status=500, content_type="text/plain")

    def generate_file_status_stream(self, file_item: KnowledgeBaseItem) -> Generator[str, None, None]:
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
                caption_done = status_data.get('caption_status') in ["completed", "failed"]

                if parsing_done and (not status_data.get('caption_status') or caption_done):
                    logger.info(
                        f"File {file_item.id} processing finished with status: {file_item.parsing_status} and caption status: {status_data.get('caption_status')}"
                    )
                    close_message = {"type": "close"}
                    yield f"data: {json.dumps(close_message)}\n\n"
                    break
                iteration += 1
                time.sleep(5)
            if iteration >= max_iterations:
                logger.warning(f"SSE stream for file {file_item.id} reached max iterations")
                timeout_message = {"type": "timeout", "message": "Status monitoring timed out"}
                yield f"data: {json.dumps(timeout_message)}\n\n"
        except Exception as e:
            logger.exception(f"Error in SSE stream generation for file {file_item.id}: {e}")
            error_message = {"type": "error", "message": f"Stream error: {str(e)}"}
            yield f"data: {json.dumps(error_message)}\n\n"

    def build_status_data(self, file_item: KnowledgeBaseItem) -> Dict[str, Any]:
        # Map model parsing_status (single-field state machine) to frontend status
        status_mapping = {
            "queueing": "processing",
            "parsing": "processing",
            "captioning": "processing",
            "done": "done",
            "failed": "failed",
        }
        frontend_status = status_mapping.get(file_item.parsing_status, "processing")

        # Derive caption status for backward-compatible UI hints
        # - captioning -> captioning
        # - done -> completed
        # - failed -> failed
        # - otherwise None
        caption_status = None
        if file_item.parsing_status == 'captioning':
            caption_status = 'captioning'
        elif file_item.parsing_status == 'done':
            caption_status = 'completed'
        elif file_item.parsing_status == 'failed':
            caption_status = 'failed'

        return {
            "file_id": str(file_item.id),
            "status": frontend_status,
            "title": file_item.title,
            "content_type": file_item.content_type,
            "created_at": file_item.created_at.isoformat() if file_item.created_at else None,
            "updated_at": file_item.updated_at.isoformat() if file_item.updated_at else None,
            "has_content": bool(file_item.content),
            "processing_status": file_item.parsing_status,
            "metadata": file_item.metadata or {},
            "caption_status": caption_status,
        }

    def _generate_upload_pending_stream(self, upload_id: str):
        """Generate SSE stream for upload IDs that haven't been processed yet"""
        def generate_pending_stream():
            # Send a few "processing" messages then close
            for i in range(3):
                yield f"data: {json.dumps({'type': 'file_status', 'data': {'file_id': upload_id, 'status': 'processing', 'title': f'Upload {upload_id}', 'updated_at': None}})}\n\n"
                time.sleep(1)
            # Send close message
            yield f"data: {json.dumps({'type': 'close', 'message': 'Upload not found'})}\n\n"
        
        response = StreamingHttpResponse(generate_pending_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Accept, Authorization, Content-Type"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        return response


class NotebookFilesSSEView(View):
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
