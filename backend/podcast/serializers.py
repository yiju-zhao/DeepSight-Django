from rest_framework import serializers
from .models import Podcast


class PodcastSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(source='id', read_only=True)
    notebook_id = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Podcast
        fields = [
            "id",
            "job_id",
            "title",
            "description",
            "status",
            "progress",
            "created_at",
            "updated_at",
            "audio_url",
            "conversation_text",
            "error_message",
            "source_file_ids",
            "source_metadata",
            "notebook_id",
        ]
        read_only_fields = [
            "job_id",
            "status",
            "progress",
            "created_at",
            "updated_at",
            "conversation_text",
            "error_message",
            "notebook_id",
        ]

    def get_notebook_id(self, obj):
        return obj.notebook.pk if obj.notebook else None

    def get_audio_url(self, obj):
        """Return the Django streaming endpoint URL for audio playback."""
        return obj.get_audio_url()


class NotebookPodcastCreateSerializer(serializers.Serializer):
    """Serializer for creating podcast jobs within a specific notebook context."""
    source_file_ids = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of source file IDs from the notebook to generate podcast from",
    )
    title = serializers.CharField(
        max_length=200,
        default="Panel Conversation",
        help_text="Title for the generated podcast",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Description for the generated podcast",
    )

    def validate_source_file_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one source file ID is required")
        return value


class PodcastCreateSerializer(serializers.Serializer):
    """Canonical create serializer: accepts notebook id in payload."""
    notebook = serializers.UUIDField(help_text="Notebook ID associated with this job")
    source_file_ids = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of source file IDs from the notebook to generate podcast from",
    )
    title = serializers.CharField(
        max_length=200,
        default="Panel Conversation",
        help_text="Title for the generated podcast",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Description for the generated podcast",
    )

    def validate_source_file_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one source file ID is required")
        return value


class PodcastListSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(source='id', read_only=True)
    notebook_id = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Podcast
        fields = [
            "id",
            "job_id",
            "title",
            "description",
            "status",
            "progress",
            "created_at",
            "updated_at",
            "audio_url",
            "error_message",
            "notebook_id",
        ]
    
    def get_notebook_id(self, obj):
        return obj.notebook.pk if obj.notebook else None

    def get_audio_url(self, obj):
        """Return the Django streaming endpoint URL for audio playback."""
        return obj.get_audio_url()
