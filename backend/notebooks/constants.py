"""
Centralized constants and enums for the notebooks app.

Keep stringly-typed values out of business logic to improve maintainability.
"""

from django.db import models


class ParsingStatus(models.TextChoices):
    QUEUEING = "queueing", "Queueing"
    PARSING = "parsing", "Parsing"
    CAPTIONING = "captioning", "Captioning"
    DONE = "done", "Done"
    FAILED = "failed", "Failed"


class CaptioningStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    NOT_REQUIRED = "not_required", "Not Required"


class RagflowDocStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    UPLOADING = "uploading", "Uploading"
    PARSING = "parsing", "Parsing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class ContentType(models.TextChoices):
    TEXT = "text", "Text Content"
    DOCUMENT = "document", "Document"
    WEBPAGE = "webpage", "Webpage"
    MEDIA = "media", "Media File"


# SSE event constants
class SseStatus:
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


# Default timing parameters
DEFAULT_SIGNED_URL_EXPIRES = 3600  # seconds
JOB_SSE_MAX_DURATION_SECONDS = 600
JOB_SSE_HEARTBEAT_SECONDS = 30
