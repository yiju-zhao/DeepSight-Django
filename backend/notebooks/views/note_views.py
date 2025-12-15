"""
Note-related views for CRUD operations on user notes.
"""

import logging

from django.core.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
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

from core.pagination import NotebookPagination
from core.permissions import IsNotebookOwner

from ..models import Note, Notebook
from ..serializers import (
    NoteCreateSerializer,
    NoteFromMessageSerializer,
    NoteListSerializer,
    NoteSerializer,
    NoteUpdateSerializer,
)

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="List notes",
        description="Get paginated list of notes for a specific notebook",
        responses={200: NoteListSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Get note details",
        description="Retrieve detailed information about a specific note",
        responses={200: NoteSerializer},
    ),
    create=extend_schema(
        summary="Create note",
        description="Create a new note in the notebook",
        request=NoteCreateSerializer,
        responses={201: NoteSerializer},
    ),
    update=extend_schema(
        summary="Update note",
        description="Update note details (full update)",
        request=NoteUpdateSerializer,
        responses={200: NoteSerializer},
    ),
    partial_update=extend_schema(
        summary="Partially update note",
        description="Update specific fields of a note",
        request=NoteUpdateSerializer,
        responses={200: NoteSerializer},
    ),
    destroy=extend_schema(
        summary="Delete note",
        description="Delete a note from the notebook",
        responses={204: None},
    ),
)
class NoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user notes within notebooks.

    Provides CRUD operations and additional actions for note management.
    """

    permission_classes = [permissions.IsAuthenticated, IsNotebookOwner]
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
    filterset_fields = ["is_pinned", "created_at"]
    search_fields = ["title", "content", "tags"]
    ordering_fields = ["title", "is_pinned", "created_at", "updated_at"]
    ordering = ["-is_pinned", "-created_at"]

    def get_queryset(self):
        """Return notes for the specified notebook."""
        if getattr(self, "swagger_fake_view", False):
            return Note.objects.none()

        if not self.request.user.is_authenticated:
            return Note.objects.none()

        # Get notebook from URL (notebook_pk from NestedDefaultRouter)
        notebook_id = self.kwargs.get("notebook_pk")

        if not notebook_id:
            return Note.objects.none()

        # Filter notes by notebook and user
        return (
            Note.objects.filter(notebook_id=notebook_id, created_by=self.request.user)
            .select_related("notebook", "created_by")
            .order_by("-is_pinned", "-created_at")
        )

    def get_notebook(self):
        """Get the notebook instance from URL kwargs."""
        notebook_id = self.kwargs.get("notebook_pk")

        if not notebook_id:
            raise serializers.ValidationError({"detail": "Notebook ID is required."})

        try:
            notebook = Notebook.objects.get(id=notebook_id, user=self.request.user)
            return notebook
        except Notebook.DoesNotExist:
            raise serializers.ValidationError(
                {"detail": "Notebook not found or access denied."}
            )

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "list":
            return NoteListSerializer
        elif self.action == "create":
            return NoteCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return NoteUpdateSerializer
        elif self.action == "from_message":
            return NoteFromMessageSerializer
        return NoteSerializer

    def get_serializer_context(self):
        """Add notebook to serializer context."""
        context = super().get_serializer_context()
        if hasattr(self, "kwargs") and "notebook_pk" in self.kwargs:
            try:
                context["notebook"] = self.get_notebook()
            except Exception:
                pass
        return context

    def perform_create(self, serializer):
        """Create note with created_by set to current user."""
        try:
            notebook = self.get_notebook()

            # Create the note
            note = serializer.save(
                notebook=notebook,
                created_by=self.request.user,
            )

            # Store instance for response
            serializer.instance = note

        except ValidationError as e:
            raise serializers.ValidationError({"detail": str(e)})
        except Exception as e:
            logger.exception(f"Failed to create note: {e}")
            raise serializers.ValidationError(
                {"detail": f"Failed to create note: {str(e)}"}
            )

    def create(self, request, *args, **kwargs):
        """Override create to return full note data with NoteSerializer."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Return full note data
        response_serializer = NoteSerializer(serializer.instance)
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def perform_update(self, serializer):
        """Update note."""
        try:
            serializer.save()
        except ValidationError as e:
            raise serializers.ValidationError({"detail": str(e)})
        except Exception as e:
            logger.exception(f"Failed to update note: {e}")
            raise serializers.ValidationError(
                {"detail": f"Failed to update note: {str(e)}"}
            )

    def perform_destroy(self, instance):
        """Delete note."""
        try:
            instance.delete()
        except Exception as e:
            logger.exception(f"Failed to delete note: {e}")
            raise serializers.ValidationError(
                {"detail": f"Failed to delete note: {str(e)}"}
            )

    @extend_schema(
        summary="Create note from chat message",
        description="Create a new note from a chat message in the notebook",
        request=NoteFromMessageSerializer,
        responses={201: NoteSerializer},
        examples=[
            OpenApiExample(
                "Create from message",
                value={
                    "message_id": 123,
                    "title": "Important finding about quantum computing",
                    "tags": ["research", "quantum"],
                },
                request_only=True,
            )
        ],
    )
    @action(detail=False, methods=["post"], url_path="from-message")
    def from_message(self, request, notebook_pk=None):
        """
        Create a note from a chat message.

        Endpoint: POST /api/v1/notebooks/{notebook_pk}/notes/from-message/
        """
        try:
            notebook = self.get_notebook()

            serializer = NoteFromMessageSerializer(
                data=request.data,
                context={
                    "notebook": notebook,
                    "request": request,
                },
            )
            serializer.is_valid(raise_exception=True)

            # Create the note from message
            note = serializer.save()

            # Return full note data
            response_serializer = NoteSerializer(note)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception(f"Failed to create note from message: {e}")
            return Response(
                {"detail": f"Failed to create note from message: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Pin note",
        description="Pin a note to the top of the list",
        responses={200: NoteSerializer},
    )
    @action(detail=True, methods=["post"], url_path="pin")
    def pin(self, request, notebook_pk=None, pk=None):
        """
        Pin a note to the top.

        Endpoint: POST /api/v1/notebooks/{notebook_pk}/notes/{id}/pin/
        """
        try:
            note = self.get_object()
            note.pin()

            serializer = NoteSerializer(note)
            return Response(serializer.data)

        except Exception as e:
            logger.exception(f"Failed to pin note: {e}")
            return Response(
                {"detail": f"Failed to pin note: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Unpin note",
        description="Unpin a note from the top of the list",
        responses={200: NoteSerializer},
    )
    @action(detail=True, methods=["post"], url_path="unpin")
    def unpin(self, request, notebook_pk=None, pk=None):
        """
        Unpin a note.

        Endpoint: POST /api/v1/notebooks/{notebook_pk}/notes/{id}/unpin/
        """
        try:
            note = self.get_object()
            note.unpin()

            serializer = NoteSerializer(note)
            return Response(serializer.data)

        except Exception as e:
            logger.exception(f"Failed to unpin note: {e}")
            return Response(
                {"detail": f"Failed to unpin note: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
