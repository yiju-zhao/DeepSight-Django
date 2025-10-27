"""
URL Service - Handle URL processing business logic following Django patterns.

All URL processing is now handled asynchronously via Celery tasks.
"""

import logging

from core.services import NotebookBaseService
from django.db import transaction
from rest_framework import status

from ..models import KnowledgeBaseItem

logger = logging.getLogger(__name__)


class URLService(NotebookBaseService):
    """Handle URL processing business logic using async Celery tasks."""

    def __init__(self):
        super().__init__()

    @transaction.atomic
    def handle_single_url_parse(self, url, upload_url_id, notebook, user):
        """
        Handle single URL parsing asynchronously using Celery.

        Creates a KB item placeholder and triggers async processing.
        """
        try:
            from ..tasks import parse_url_task

            # Create KB item placeholder immediately for tracking
            kb_item = KnowledgeBaseItem.objects.create(
                notebook=notebook,
                title=f"Processing: {url[:100]}",
                content_type="webpage",
                parsing_status="queueing",
                notes=f"URL: {url}",
                tags=[],
                metadata={"url": url, "upload_url_id": upload_url_id},
            )

            logger.info(f"Created KB item {kb_item.id} for URL: {url}")

            # Trigger async processing with Celery
            parse_url_task.apply_async(
                args=[url, upload_url_id, str(notebook.id), user.pk, str(kb_item.id)]
            )

            return {
                "success": True,
                "upload_url_id": upload_url_id,
                "file_id": str(kb_item.id),
                "status_code": status.HTTP_202_ACCEPTED,  # 202 for async processing
            }

        except Exception as e:
            logger.exception(f"Single URL parsing failed for {url}: {e}")
            raise

    @transaction.atomic
    def handle_url_with_media(self, url, upload_url_id, notebook, user):
        """
        Handle URL parsing with media extraction asynchronously using Celery.

        Creates a KB item placeholder and triggers async processing.
        """
        try:
            from ..tasks import parse_url_with_media_task

            # Create KB item placeholder immediately for tracking
            kb_item = KnowledgeBaseItem.objects.create(
                notebook=notebook,
                title=f"Processing with media: {url[:100]}",
                content_type="webpage",
                parsing_status="queueing",
                notes=f"URL with media: {url}",
                tags=[],
                metadata={
                    "url": url,
                    "upload_url_id": upload_url_id,
                    "extract_media": True,
                },
            )

            logger.info(f"Created KB item {kb_item.id} for URL with media: {url}")

            # Trigger async processing with Celery
            parse_url_with_media_task.apply_async(
                args=[url, upload_url_id, str(notebook.id), user.pk, str(kb_item.id)]
            )

            return {
                "success": True,
                "upload_url_id": upload_url_id,
                "file_id": str(kb_item.id),
                "status_code": status.HTTP_202_ACCEPTED,  # 202 for async processing
            }

        except Exception as e:
            logger.exception(f"URL with media parsing failed for {url}: {e}")
            raise

    @transaction.atomic
    def handle_document_url(self, url, upload_url_id, notebook, user):
        """
        Handle document URL parsing asynchronously using Celery.

        Creates a KB item placeholder and triggers async processing.
        """
        try:
            from ..tasks import parse_document_url_task

            # Create KB item placeholder immediately for tracking
            kb_item = KnowledgeBaseItem.objects.create(
                notebook=notebook,
                title=f"Processing document: {url[:100]}",
                content_type="document",
                parsing_status="queueing",
                notes=f"Document URL: {url}",
                tags=[],
                metadata={
                    "url": url,
                    "upload_url_id": upload_url_id,
                    "document_only": True,
                },
            )

            logger.info(f"Created KB item {kb_item.id} for document URL: {url}")

            # Trigger async processing with Celery
            parse_document_url_task.apply_async(
                args=[url, upload_url_id, str(notebook.id), user.pk, str(kb_item.id)]
            )

            return {
                "success": True,
                "upload_url_id": upload_url_id,
                "file_id": str(kb_item.id),
                "status_code": status.HTTP_202_ACCEPTED,  # 202 for async processing
            }

        except Exception as e:
            logger.exception(f"Document URL parsing failed for {url}: {e}")
            raise
