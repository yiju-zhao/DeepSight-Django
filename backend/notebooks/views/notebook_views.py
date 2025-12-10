"""
Notebook-related views for CRUD operations
"""

import logging
from django.core.exceptions import ValidationError
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
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
    OpenApiExample,
)

from core.pagination import NotebookPagination
from core.permissions import IsNotebookOwner, IsOwnerPermission
from ..models import Notebook, KnowledgeBaseItem, BatchJob
from ..serializers import (
    NotebookCreateSerializer,
    NotebookListSerializer,
    NotebookSerializer,
    NotebookUpdateSerializer,
    KnowledgeBaseItemSerializer,
    BatchJobSerializer,
)
from ..services import NotebookService

logger = logging.getLogger(__name__)


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
            notebook = self.notebook_service.create_notebook(
                user=self.request.user,
                name=serializer.validated_data["name"],
                description=serializer.validated_data.get("description", ""),
            )
            serializer.instance = notebook
        except ValidationError as e:
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


class KnowledgeBaseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = KnowledgeBaseItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotebookOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["content_type", "parsing_status"]

    def get_queryset(self):
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
        if getattr(self, "swagger_fake_view", False):
            return BatchJob.objects.none()

        notebook_id = self.kwargs.get("notebook_pk") or self.kwargs.get("notebook_id")
        return BatchJob.objects.filter(
            notebook__id=notebook_id, notebook__user=self.request.user
        ).order_by("-created_at")
