"""
Note-related serializers for the notebooks module.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from ..models import Note, SessionChatMessage

User = get_user_model()


class NoteSerializer(serializers.ModelSerializer):
    """
    Serializer for Note model with comprehensive field handling.

    Provides basic CRUD operations with proper validation and read-only fields.
    """

    # Include created_by user details
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True
    )
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    # Include notebook name
    notebook_name = serializers.CharField(source="notebook.name", read_only=True)

    # Computed fields
    tag_count = serializers.SerializerMethodField()
    source_message_id = serializers.SerializerMethodField()
    created_from = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = [
            "id",
            "notebook",
            "notebook_name",
            "created_by",
            "created_by_username",
            "created_by_email",
            "title",
            "content",
            "tags",
            "tag_count",
            "metadata",
            "is_pinned",
            "source_message_id",
            "created_from",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "notebook_name",
            "created_by_username",
            "created_by_email",
        ]

    def get_tag_count(self, obj):
        """Get number of tags."""
        if isinstance(obj.tags, list):
            return len(obj.tags)
        return 0

    def get_source_message_id(self, obj):
        """Get source message ID if note was created from chat."""
        return obj.get_source_message_id()

    def get_created_from(self, obj):
        """Get how this note was created (chat or manual)."""
        return obj.get_created_from()


class NoteListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing notes.

    Optimized for list views with minimal data.
    """

    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True
    )
    tag_count = serializers.SerializerMethodField()
    content_preview = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = [
            "id",
            "title",
            "content_preview",
            "tags",
            "tag_count",
            "is_pinned",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by_username",
            "created_at",
            "updated_at",
        ]

    def get_tag_count(self, obj):
        """Get number of tags."""
        if isinstance(obj.tags, list):
            return len(obj.tags)
        return 0

    def get_content_preview(self, obj):
        """Get truncated content for preview (first 150 chars)."""
        if len(obj.content) > 150:
            return obj.content[:150] + "..."
        return obj.content


class NoteCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating notes.

    Validates all required fields and handles default values.
    """

    class Meta:
        model = Note
        fields = [
            "title",
            "content",
            "tags",
            "metadata",
            "is_pinned",
        ]

    def validate_title(self, value):
        """Validate note title."""
        if not value or not value.strip():
            raise serializers.ValidationError("Note title cannot be empty.")

        value = value.strip()

        if len(value) < 1:
            raise serializers.ValidationError(
                "Note title must be at least 1 character long."
            )

        if len(value) > 255:
            raise serializers.ValidationError(
                "Note title cannot exceed 255 characters."
            )

        return value

    def validate_content(self, value):
        """Validate note content."""
        if not value or not value.strip():
            raise serializers.ValidationError("Note content cannot be empty.")

        value = value.strip()

        if len(value) < 1:
            raise serializers.ValidationError(
                "Note content must be at least 1 character long."
            )

        return value

    def validate_tags(self, value):
        """Validate tags is a list."""
        if value is None:
            return []

        if not isinstance(value, list):
            raise serializers.ValidationError("Tags must be a list.")

        # Validate each tag is a string
        for tag in value:
            if not isinstance(tag, str):
                raise serializers.ValidationError("Each tag must be a string.")
            if not tag.strip():
                raise serializers.ValidationError("Tags cannot be empty strings.")

        # Remove duplicates and strip whitespace
        cleaned_tags = list(set(tag.strip() for tag in value if tag.strip()))

        return cleaned_tags

    def validate_metadata(self, value):
        """Validate metadata is a dict."""
        if value is None:
            return {}

        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be a dictionary.")

        return value

    def create(self, validated_data):
        """Create note with created_by from request user."""
        # created_by should be set by the view
        return super().create(validated_data)


class NoteUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating notes.

    Allows partial updates with validation.
    """

    class Meta:
        model = Note
        fields = [
            "title",
            "content",
            "tags",
            "metadata",
            "is_pinned",
        ]

    def validate_title(self, value):
        """Validate note title."""
        if value is not None:
            if not value or not value.strip():
                raise serializers.ValidationError("Note title cannot be empty.")

            value = value.strip()

            if len(value) > 255:
                raise serializers.ValidationError(
                    "Note title cannot exceed 255 characters."
                )

        return value

    def validate_content(self, value):
        """Validate note content."""
        if value is not None:
            if not value or not value.strip():
                raise serializers.ValidationError("Note content cannot be empty.")

        return value

    def validate_tags(self, value):
        """Validate tags is a list."""
        if value is not None:
            if not isinstance(value, list):
                raise serializers.ValidationError("Tags must be a list.")

            # Validate each tag is a string
            for tag in value:
                if not isinstance(tag, str):
                    raise serializers.ValidationError("Each tag must be a string.")
                if not tag.strip():
                    raise serializers.ValidationError("Tags cannot be empty strings.")

            # Remove duplicates and strip whitespace
            value = list(set(tag.strip() for tag in value if tag.strip()))

        return value


class NoteFromMessageSerializer(serializers.Serializer):
    """
    Serializer for creating a note from a chat message.

    Validates message ID and optional title override.
    """

    message_id = serializers.IntegerField(required=True)
    title = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Optional title override. If not provided, auto-generates from message.",
    )
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="Optional tags to add to the note.",
    )

    def validate_message_id(self, value):
        """Validate message exists and belongs to the notebook."""
        notebook = self.context.get("notebook")

        if not notebook:
            raise serializers.ValidationError("Notebook context is required.")

        try:
            message = SessionChatMessage.objects.get(id=value, notebook=notebook)
        except SessionChatMessage.DoesNotExist:
            raise serializers.ValidationError(
                f"Chat message with ID {value} not found in this notebook."
            )

        # Only allow saving assistant messages (not user messages)
        if message.sender != "assistant":
            raise serializers.ValidationError(
                "Only assistant messages can be saved as notes."
            )

        return value

    def validate_title(self, value):
        """Validate and normalize title."""
        if value:
            value = value.strip()
            if len(value) > 255:
                raise serializers.ValidationError("Title cannot exceed 255 characters.")
        return value

    def validate_tags(self, value):
        """Validate tags list."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Tags must be a list.")

        cleaned_tags = []
        for tag in value:
            if not isinstance(tag, str):
                raise serializers.ValidationError("Each tag must be a string.")
            tag = tag.strip()
            if tag and tag not in cleaned_tags:
                cleaned_tags.append(tag)

        return cleaned_tags

    def create(self, validated_data):
        """Create a note from the chat message."""
        message_id = validated_data["message_id"]
        custom_title = validated_data.get("title", "").strip()
        tags = validated_data.get("tags", [])

        notebook = self.context["notebook"]
        user = self.context["request"].user

        # Get the message
        message = SessionChatMessage.objects.get(id=message_id, notebook=notebook)

        # Generate title if not provided
        if custom_title:
            title = custom_title
        else:
            # Use first 50 chars of message as title
            title = message.message[:50]
            if len(message.message) > 50:
                title += "..."

        # Create the note
        note = Note.objects.create(
            notebook=notebook,
            created_by=user,
            title=title,
            content=message.message,
            tags=tags,
            metadata={
                "source_message_id": message.id,
                "created_from": "chat",
                "session_id": str(message.session.session_id),
            },
        )

        return note
