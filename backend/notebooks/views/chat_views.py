"""
Chat-related views for models and sessions
"""

import logging

from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import StreamingHttpResponse
from rest_framework import permissions, serializers, status, viewsets, authentication
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema

from core.permissions import IsNotebookOwner
from ..models import ChatSession, Notebook
from ..services import ChatService

logger = logging.getLogger(__name__)


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

    @action(detail=True, methods=["post"], url_path="clear")
    def clear(self, request, notebook_pk=None, pk=None):
        """
        Clear (archive) a chat session.

        This archives the session, hiding it from the UI but keeping it in the database.
        """
        try:
            session = self.get_object()
            notebook = get_object_or_404(
                Notebook.objects.filter(user=request.user), pk=notebook_pk
            )

            logger.info(f"Clearing session {session.session_id} for notebook {notebook_pk}")

            # Call service to clear the session
            result = self.chat_service.clear_chat_session(
                session_id=str(session.session_id),
                notebook=notebook,
                user_id=request.user.id,
            )

            if not result.get("success"):
                error_msg = result.get("error", "Failed to clear session")
                status_code = result.get("status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
                return Response({"detail": error_msg}, status=status_code)

            return Response(
                {
                    "success": True,
                    "message": result.get("message", "Session cleared successfully"),
                    "session_id": result.get("session_id"),
                    "status": result.get("status"),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.exception(f"Failed to clear session: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
