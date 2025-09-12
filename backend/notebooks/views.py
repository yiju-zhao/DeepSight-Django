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
            with transaction.atomic():
                notebook = serializer.save(
                    user=self.request.user,
                    created_at=timezone.now(),
                    updated_at=timezone.now(),
                )
        except Exception as e:
            logger.exception(f"Failed to create notebook: {e}")
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
        serializer = FileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                notebook = get_object_or_404(Notebook.objects.filter(user=request.user), pk=notebook_pk)
                files = self.file_service.handle_upload(
                    user=request.user,
                    notebook=notebook,
                    files=serializer.validated_data["files"],
                    notes=serializer.validated_data.get("notes", ""),
                )
                data = KnowledgeBaseItemSerializer(files, many=True).data
                return Response(data, status=status.HTTP_201_CREATED)
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
            content = self.kb_service.get_processed_content(item)
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

    @action(detail=True, methods=["get"], url_path="images")
    def images(self, request, notebook_pk=None, pk=None):
        item = self.get_object()
        try:
            images = self.kb_service.get_images(item)
            return Response({"images": images})
        except Exception as e:
            logger.exception(f"Failed to get images for {pk}: {e}")
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
        return ChatSession.objects.filter(notebook=notebook).order_by("-timestamp")

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
            file_item = get_object_or_404(KnowledgeBaseItem.objects.filter(notebook=notebook), pk=file_id)

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
                if file_item.processing_status in ["completed", "failed", "error"]:
                    logger.info(
                        f"File {file_item.id} processing finished with status: {file_item.processing_status}"
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
        status_mapping = {
            "processing": "processing",
            "completed": "done",
            "failed": "failed",
            "error": "failed",
            "queued": "processing",
            "pending": "processing",
        }
        frontend_status = status_mapping.get(file_item.processing_status, file_item.processing_status)
        return {
            "file_id": str(file_item.id),
            "status": frontend_status,
            "title": file_item.title,
            "content_type": file_item.content_type,
            "created_at": file_item.created_at.isoformat() if file_item.created_at else None,
            "updated_at": file_item.updated_at.isoformat() if file_item.updated_at else None,
            "has_content": bool(file_item.content),
            "processing_status": file_item.processing_status,
            "metadata": file_item.metadata or {},
        }


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
