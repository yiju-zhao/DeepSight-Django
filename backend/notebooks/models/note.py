"""
Note models for storing user notes from chat messages or manual entries.
"""

from core.mixins import BaseModel
from django.core.exceptions import ValidationError
from django.db import models


class Note(BaseModel):
    """
    Represents a user note that can be created from chat messages or manually.
    Notes are displayed in the Studio panel alongside reports and podcasts.
    """

    # Relationship to notebook
    notebook = models.ForeignKey(
        "notebooks.Notebook",
        on_delete=models.CASCADE,
        related_name="notes",
        help_text="Notebook this note belongs to",
    )

    # Created by user
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notes",
        help_text="User who created this note",
    )

    # Note content
    title = models.CharField(
        max_length=255,
        help_text="Title of the note",
    )

    content = models.TextField(
        help_text="Main content of the note (supports markdown)",
    )

    # Categorization
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for categorizing this note",
    )

    # Additional metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata (source_message_id, created_from, etc.)",
    )

    # Display preferences
    is_pinned = models.BooleanField(
        default=False,
        help_text="Whether this note is pinned to the top",
    )

    class Meta:
        ordering = ["-is_pinned", "-created_at"]
        verbose_name = "Note"
        verbose_name_plural = "Notes"
        indexes = [
            models.Index(fields=["notebook", "-created_at"]),
            models.Index(fields=["created_by", "-created_at"]),
            models.Index(fields=["-is_pinned", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(title=""),
                name="note_title_not_empty",
            ),
            models.CheckConstraint(
                check=~models.Q(content=""),
                name="note_content_not_empty",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.notebook.name})"

    def clean(self):
        """Django model validation."""
        # Validate title is not empty
        if not self.title or not self.title.strip():
            raise ValidationError("Note title cannot be empty")

        # Validate content is not empty
        if not self.content or not self.content.strip():
            raise ValidationError("Note content cannot be empty")

        # Normalize title and content
        self.title = self.title.strip()
        self.content = self.content.strip()

        # Validate tags is a list
        if not isinstance(self.tags, list):
            raise ValidationError("Tags must be a list")

        # Validate metadata is a dict
        if not isinstance(self.metadata, dict):
            raise ValidationError("Metadata must be a dictionary")

    def save(self, *args, **kwargs):
        """Override save to ensure validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    def add_tag(self, tag):
        """Add a tag to this note."""
        if not isinstance(self.tags, list):
            self.tags = []

        tag = tag.strip()
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.save(update_fields=["tags", "updated_at"])

    def remove_tag(self, tag):
        """Remove a tag from this note."""
        if isinstance(self.tags, list) and tag in self.tags:
            self.tags.remove(tag)
            self.save(update_fields=["tags", "updated_at"])

    def pin(self):
        """Pin this note to the top."""
        if not self.is_pinned:
            self.is_pinned = True
            self.save(update_fields=["is_pinned", "updated_at"])

    def unpin(self):
        """Unpin this note."""
        if self.is_pinned:
            self.is_pinned = False
            self.save(update_fields=["is_pinned", "updated_at"])

    def get_source_message_id(self):
        """Get source message ID if this note was created from a chat message."""
        if isinstance(self.metadata, dict):
            return self.metadata.get("source_message_id")
        return None

    def get_created_from(self):
        """Get how this note was created (chat or manual)."""
        if isinstance(self.metadata, dict):
            return self.metadata.get("created_from", "manual")
        return "manual"

    def update_metadata(self, key, value):
        """Update a specific metadata key."""
        if not isinstance(self.metadata, dict):
            self.metadata = {}

        self.metadata[key] = value
        self.save(update_fields=["metadata", "updated_at"])

    def get_metadata(self, key, default=None):
        """Get a specific metadata value."""
        if isinstance(self.metadata, dict):
            return self.metadata.get(key, default)
        return default
