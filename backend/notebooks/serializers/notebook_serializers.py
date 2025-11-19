"""
Notebook-related serializers for the notebooks module following DRF best practices.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from ..models import Notebook
from ..constants import ParsingStatus


class NotebookCountMixin:
    """Mixin providing common computed count fields for notebooks."""

    def get_source_count(self, obj):
        return obj.knowledge_base_items.count()

    def get_knowledge_item_count(self, obj):
        return obj.knowledge_base_items.filter(
            parsing_status=ParsingStatus.DONE
        ).count()

    def get_parsed_files_count(self, obj):
        """Get count of successfully parsed files (alias for knowledge_item_count)."""
        return self.get_knowledge_item_count(obj)

    def get_has_parsed_files(self, obj):
        """Check if notebook has at least one successfully parsed file."""
        return obj.knowledge_base_items.filter(
            parsing_status=ParsingStatus.DONE
        ).exists()


class NotebookValidationMixin:
    """Shared validation helpers for create/update serializers."""

    def _validate_name_text(self, value: str) -> str:
        if not value or not str(value).strip():
            raise serializers.ValidationError("Notebook name cannot be empty.")
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError(
                "Notebook name must be at least 2 characters long."
            )
        if len(value) > 100:
            raise serializers.ValidationError(
                "Notebook name cannot exceed 100 characters."
            )
        return value

    def _validate_description_text(self, value: str | None) -> str:
        if not value:
            return ""
        value = value.strip()
        if len(value) > 500:
            raise serializers.ValidationError(
                "Description cannot exceed 500 characters."
            )
        return value


User = get_user_model()


class NotebookSerializer(NotebookCountMixin, serializers.ModelSerializer):
    """
    Serializer for Notebook model with comprehensive field handling.

    Provides basic CRUD operations with proper validation and read-only fields.
    """

    # Computed fields
    source_count = serializers.SerializerMethodField()
    knowledge_item_count = serializers.SerializerMethodField()
    parsed_files_count = serializers.SerializerMethodField()
    has_parsed_files = serializers.SerializerMethodField()
    chat_message_count = serializers.SerializerMethodField()
    last_activity = serializers.SerializerMethodField()
    ragflow_dataset_info = serializers.SerializerMethodField()

    class Meta:
        model = Notebook
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
            "source_count",
            "knowledge_item_count",
            "parsed_files_count",
            "has_parsed_files",
            "chat_message_count",
            "last_activity",
            "ragflow_dataset_info",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "source_count",
            "knowledge_item_count",
            "parsed_files_count",
            "has_parsed_files",
            "chat_message_count",
            "last_activity",
            "ragflow_dataset_info",
        ]

    def get_chat_message_count(self, obj):
        """Get count of chat messages in the notebook (across all sessions)."""
        return obj.session_chat_messages.count()

    def get_last_activity(self, obj):
        """Get the timestamp of the last activity in the notebook."""
        latest_kb_item = obj.knowledge_base_items.order_by("-updated_at").first()
        latest_session = obj.chat_sessions.order_by("-last_activity").first()

        last_activity = obj.updated_at

        if latest_kb_item and latest_kb_item.updated_at > last_activity:
            last_activity = latest_kb_item.updated_at

        if latest_session and latest_session.last_activity > last_activity:
            last_activity = latest_session.last_activity

        return last_activity

    def get_ragflow_dataset_info(self, obj):
        """Get RagFlow dataset information for the notebook."""
        try:
            ragflow_dataset = obj.ragflow_dataset
            return {
                "id": ragflow_dataset.ragflow_dataset_id,
                "status": ragflow_dataset.status,
                "is_ready": ragflow_dataset.is_ready(),
                "document_count": ragflow_dataset.get_document_count()
                if ragflow_dataset.is_ready()
                else 0,
                "error_message": ragflow_dataset.error_message or None,
            }
        except AttributeError:
            # No RagFlow dataset exists yet
            return {
                "id": None,
                "status": "not_created",
                "is_ready": False,
                "document_count": 0,
                "error_message": None,
            }

    def validate_name(self, value):
        """Validate notebook name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Notebook name cannot be empty.")

        if len(value.strip()) > 100:
            raise serializers.ValidationError(
                "Notebook name cannot exceed 100 characters."
            )

        return value.strip()

    def validate_description(self, value):
        """Validate notebook description."""
        if value and len(value.strip()) > 500:
            raise serializers.ValidationError(
                "Description cannot exceed 500 characters."
            )

        return value.strip() if value else ""


class NotebookListSerializer(NotebookCountMixin, serializers.ModelSerializer):
    """
    Lightweight serializer for notebook listing with minimal fields.

    Used in list views where full detail is not needed for performance.
    """

    source_count = serializers.SerializerMethodField()
    knowledge_item_count = serializers.SerializerMethodField()
    parsed_files_count = serializers.SerializerMethodField()
    has_parsed_files = serializers.SerializerMethodField()

    class Meta:
        model = Notebook
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
            "source_count",
            "knowledge_item_count",
            "parsed_files_count",
            "has_parsed_files",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "source_count",
            "knowledge_item_count",
            "parsed_files_count",
            "has_parsed_files",
        ]


class NotebookCreateSerializer(NotebookValidationMixin, serializers.ModelSerializer):
    """
    Serializer for notebook creation with specific validation rules.

    Note: Creation is handled by NotebookViewSet.perform_create() via NotebookService
    to ensure proper RAGFlow integration. This serializer only validates input.
    """

    class Meta:
        model = Notebook
        fields = ["name", "description"]

    def validate_name(self, value):
        value = self._validate_name_text(value)
        # Check for duplicate names for the user
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            if Notebook.objects.filter(user=request.user, name__iexact=value).exists():
                raise serializers.ValidationError(
                    "A notebook with this name already exists."
                )
        return value


class NotebookUpdateSerializer(NotebookValidationMixin, serializers.ModelSerializer):
    """
    Serializer for notebook updates with specific validation rules.
    """

    class Meta:
        model = Notebook
        fields = ["name", "description"]

    def validate_name(self, value):
        value = self._validate_name_text(value)
        # Check for duplicate names for the user (excluding current notebook)
        request = self.context.get("request")
        if request and hasattr(request, "user") and self.instance:
            if (
                Notebook.objects.filter(user=request.user, name__iexact=value)
                .exclude(pk=self.instance.pk)
                .exists()
            ):
                raise serializers.ValidationError(
                    "A notebook with this name already exists."
                )
        return value

    def validate_description(self, value):
        return self._validate_description_text(value)
