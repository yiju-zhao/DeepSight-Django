"""
Chat session models for managing RagFlow agent conversations.
"""

import uuid

from core.mixins import BaseModel
from django.core.exceptions import ValidationError
from django.db import models


class ChatSession(BaseModel):
    """
    Represents a chat session between a user and a RagFlow agent.
    Each session corresponds to a conversation thread/tab in the frontend.
    """

    STATUS_CHOICES = [
        ("active", "Active"),
        ("closed", "Closed"),
        ("archived", "Archived"),
    ]

    # Unique session identifier
    session_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text="Unique identifier for this chat session",
    )

    # Relationship to notebook (and through it, to the agent/dataset)
    notebook = models.ForeignKey(
        "notebooks.Notebook",
        on_delete=models.CASCADE,
        related_name="chat_sessions",
        help_text="Notebook this chat session belongs to",
    )

    # Session metadata
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Display title for this session (auto-generated if empty)",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
        help_text="Current status of the session",
    )

    # RagFlow specific data
    ragflow_session_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="RagFlow session ID for API calls",
    )
    ragflow_agent_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="RagFlow agent ID associated with this session",
    )

    # Session metadata and settings
    session_metadata = models.JSONField(
        blank=True, null=True, help_text="Additional session configuration and metadata"
    )

    # Timestamps
    last_activity = models.DateTimeField(
        auto_now=True, help_text="Last time there was activity in this session"
    )
    started_at = models.DateTimeField(
        auto_now_add=True, help_text="When this session was started"
    )
    ended_at = models.DateTimeField(
        blank=True, null=True, help_text="When this session was closed/ended"
    )

    class Meta:
        ordering = ["-last_activity"]
        verbose_name = "Chat Session"
        verbose_name_plural = "Chat Sessions"
        indexes = [
            models.Index(fields=["notebook", "status", "-last_activity"]),
            models.Index(fields=["session_id"]),
            models.Index(fields=["ragflow_session_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["notebook", "ragflow_session_id"],
                name="unique_ragflow_session_per_notebook",
                condition=models.Q(ragflow_session_id__isnull=False),
            )
        ]

    def __str__(self):
        title = self.title or f"Session {self.session_id.hex[:8]}"
        return f"{title} ({self.notebook.name})"

    def clean(self):
        """Django model validation."""
        # Validate metadata is a dict if provided
        if self.session_metadata is not None and not isinstance(
            self.session_metadata, dict
        ):
            raise ValidationError("Session metadata must be a dictionary")

    def save(self, *args, **kwargs):
        """Override save to ensure validation and generate title."""
        self.full_clean()

        # Auto-generate title if not provided
        if not self.title:
            # Get the first user message to create a meaningful title
            first_message = self.messages.filter(sender="user").first()
            if first_message:
                # Use first 50 characters of the first message
                self.title = first_message.message[:50] + (
                    "..." if len(first_message.message) > 50 else ""
                )
            else:
                self.title = f"Chat Session {self.session_id.hex[:8]}"

        super().save(*args, **kwargs)

    def is_active(self):
        """Check if this session is active."""
        return self.status == "active"

    def close(self):
        """Close this session."""
        from django.utils import timezone

        self.status = "closed"
        self.ended_at = timezone.now()
        self.save(update_fields=["status", "ended_at", "updated_at"])

    def archive(self):
        """Archive this session."""
        from django.utils import timezone

        self.status = "archived"
        if not self.ended_at:
            self.ended_at = timezone.now()
        self.save(update_fields=["status", "ended_at", "updated_at"])

    def reopen(self):
        """Reopen a closed session."""
        self.status = "active"
        self.ended_at = None
        self.save(update_fields=["status", "ended_at", "updated_at"])

    def get_message_count(self):
        """Get total number of messages in this session."""
        return self.messages.count()

    def get_last_message(self):
        """Get the last message in this session."""
        return self.messages.order_by("-timestamp").first()

    def get_session_duration(self):
        """Get session duration (active time)."""
        from django.utils import timezone

        end_time = self.ended_at or timezone.now()
        return end_time - self.started_at

    def update_metadata(self, key, value):
        """Update a specific metadata key."""
        if not self.session_metadata:
            self.session_metadata = {}

        self.session_metadata[key] = value
        self.save(update_fields=["session_metadata", "updated_at"])

    def get_metadata(self, key, default=None):
        """Get a specific metadata value."""
        if self.session_metadata and isinstance(self.session_metadata, dict):
            return self.session_metadata.get(key, default)
        return default


class SessionChatMessage(BaseModel):
    """
    Chat messages within a specific chat session.
    Extends the basic chat message with session-specific functionality.
    """

    SENDER_CHOICES = [("user", "User"), ("assistant", "Assistant")]

    # Link to the session
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
        help_text="Chat session this message belongs to",
    )

    # Also link to notebook for backwards compatibility and direct queries
    notebook = models.ForeignKey(
        "notebooks.Notebook",
        on_delete=models.CASCADE,
        related_name="session_chat_messages",
        help_text="Notebook this chat message belongs to",
    )

    # Message details
    sender = models.CharField(
        max_length=10, choices=SENDER_CHOICES, help_text="Who sent this message"
    )
    message = models.TextField(help_text="Content of the chat message")
    timestamp = models.DateTimeField(
        auto_now_add=True, help_text="When the message was sent"
    )

    # Message metadata (sources, confidence, etc.)
    metadata = models.JSONField(
        blank=True,
        null=True,
        help_text="Additional metadata like sources, confidence, tokens used, etc.",
    )

    # Message ordering within session
    message_order = models.PositiveIntegerField(
        default=0, help_text="Order of this message within the session"
    )

    class Meta:
        ordering = ["session", "message_order", "timestamp"]
        verbose_name = "Session Chat Message"
        verbose_name_plural = "Session Chat Messages"
        indexes = [
            models.Index(fields=["session", "message_order"]),
            models.Index(fields=["session", "timestamp"]),
            models.Index(fields=["notebook", "timestamp"]),
            models.Index(fields=["sender", "timestamp"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(message=""), name="session_chat_message_not_empty"
            )
        ]

    def __str__(self):
        return f"[{self.session}] {self.sender}: {self.message[:50]}..."

    def clean(self):
        """Django model validation."""
        if not self.message or not self.message.strip():
            raise ValidationError("Chat message cannot be empty")

        # Ensure notebook matches session.notebook
        if self.session and self.notebook != self.session.notebook:
            self.notebook = self.session.notebook

        # Normalize the message
        self.message = self.message.strip()

        # Validate metadata is a dict if provided
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise ValidationError("Metadata must be a dictionary")

    def save(self, *args, **kwargs):
        """Override save to ensure validation and auto-number messages."""
        # Set message order if not provided
        if not self.message_order and self.session:
            last_message = (
                SessionChatMessage.objects.filter(session=self.session)
                .order_by("-message_order")
                .first()
            )
            self.message_order = (last_message.message_order if last_message else 0) + 1

        self.full_clean()

        # Update session last activity
        if self.session:
            self.session.save(update_fields=["last_activity", "updated_at"])

        super().save(*args, **kwargs)

    def is_user_message(self):
        """Check if this message is from a user."""
        return self.sender == "user"

    def is_assistant_message(self):
        """Check if this message is from the assistant."""
        return self.sender == "assistant"

    def get_sources(self):
        """Get sources from metadata if available."""
        if self.metadata and isinstance(self.metadata, dict):
            return self.metadata.get("sources", [])
        return []

    def add_source(self, source_id, source_title=None):
        """Add a source reference to this message."""
        if not self.metadata:
            self.metadata = {}

        if "sources" not in self.metadata:
            self.metadata["sources"] = []

        source_info = {"id": source_id}
        if source_title:
            source_info["title"] = source_title

        if source_info not in self.metadata["sources"]:
            self.metadata["sources"].append(source_info)
            self.save(update_fields=["metadata", "updated_at"])

    def get_confidence(self):
        """Get confidence score if available."""
        if self.metadata and isinstance(self.metadata, dict):
            return self.metadata.get("confidence")
        return None

    def set_confidence(self, confidence_score):
        """Set confidence score for AI responses."""
        if not self.metadata:
            self.metadata = {}

        self.metadata["confidence"] = confidence_score
        self.save(update_fields=["metadata", "updated_at"])
