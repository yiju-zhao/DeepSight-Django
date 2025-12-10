"""
Chat-related views for models and sessions
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import StreamingHttpResponse
from drf_spectacular.utils import extend_schema

from ..models import ChatSession, Notebook
from ..services import ChatService

logger = logging.getLogger(__name__)

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
                "default_model": available_models[0] if available_models else None,
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
                "default_model": available_models[0] if available_models else None,
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
