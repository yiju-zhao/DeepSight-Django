"""
URL Service - Handle URL processing business logic following Django patterns.

All URL processing is now handled asynchronously via Celery tasks.
"""

import logging

from core.services import NotebookBaseService
from django.db import transaction
from rest_framework import status

from ..models import KnowledgeBaseItem
from ..constants import ParsingStatus, ContentType

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
                content_type=ContentType.WEBPAGE,
                parsing_status=ParsingStatus.QUEUEING,
                notes=f"URL: {url}",
                tags=[],
                metadata={"url": url, "upload_url_id": upload_url_id},
            )

            logger.info(f"Created KB item {kb_item.id} for URL: {url}")

            # Trigger async processing with Celery after transaction commits
            transaction.on_commit(
                lambda: parse_url_task.apply_async(
                    args=[url, upload_url_id, str(notebook.id), user.pk, str(kb_item.id)]
                )
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
                content_type=ContentType.WEBPAGE,
                parsing_status=ParsingStatus.QUEUEING,
                notes=f"URL with media: {url}",
                tags=[],
                metadata={
                    "url": url,
                    "upload_url_id": upload_url_id,
                    "extract_media": True,
                },
            )

            logger.info(f"Created KB item {kb_item.id} for URL with media: {url}")

            # Trigger async processing with Celery after transaction commits
            transaction.on_commit(
                lambda: parse_url_with_media_task.apply_async(
                    args=[url, upload_url_id, str(notebook.id), user.pk, str(kb_item.id)]
                )
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
                content_type=ContentType.DOCUMENT,
                parsing_status=ParsingStatus.QUEUEING,
                notes=f"Document URL: {url}",
                tags=[],
                metadata={
                    "url": url,
                    "upload_url_id": upload_url_id,
                    "document_only": True,
                },
            )

            logger.info(f"Created KB item {kb_item.id} for document URL: {url}")

            # Trigger async processing with Celery after transaction commits
            transaction.on_commit(
                lambda: parse_document_url_task.apply_async(
                    args=[url, upload_url_id, str(notebook.id), user.pk, str(kb_item.id)]
                )
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

    @transaction.atomic
    def handle_batch_url_parse(self, urls, upload_url_id, notebook, user):
        """
        Handle batch URL parsing asynchronously using Celery.

        Process multiple URLs in batch, creating KB item placeholders for each
        and triggering async processing. Returns structured response with
        success/failure breakdown.
        """
        successful = []
        failed = []

        for url in urls:
            try:
                result = self.handle_single_url_parse(
                    url=url,
                    upload_url_id=upload_url_id,
                    notebook=notebook,
                    user=user,
                )
                successful.append(
                    {
                        "url": url,
                        "file_id": result["file_id"],
                        "upload_url_id": result["upload_url_id"],
                    }
                )
            except Exception as e:
                logger.exception(f"Failed to process URL {url}: {e}")
                failed.append({"url": url, "reason": str(e)})

        return {
            "success": len(failed) == 0,
            "total_submitted": len(urls),
            "successful": successful,
            "failed": failed,
            "status_code": status.HTTP_207_MULTI_STATUS
            if failed
            else status.HTTP_202_ACCEPTED,
        }

    @transaction.atomic
    def handle_batch_url_with_media(self, urls, upload_url_id, notebook, user):
        """
        Handle batch URL parsing with media extraction asynchronously using Celery.

        Process multiple URLs in batch with media extraction, creating KB item
        placeholders for each and triggering async processing. Returns structured
        response with success/failure breakdown.
        """
        successful = []
        failed = []

        for url in urls:
            try:
                result = self.handle_url_with_media(
                    url=url,
                    upload_url_id=upload_url_id,
                    notebook=notebook,
                    user=user,
                )
                successful.append(
                    {
                        "url": url,
                        "file_id": result["file_id"],
                        "upload_url_id": result["upload_url_id"],
                    }
                )
            except Exception as e:
                logger.exception(f"Failed to process URL with media {url}: {e}")
                failed.append({"url": url, "reason": str(e)})

        return {
            "success": len(failed) == 0,
            "total_submitted": len(urls),
            "successful": successful,
            "failed": failed,
            "status_code": status.HTTP_207_MULTI_STATUS
            if failed
            else status.HTTP_202_ACCEPTED,
        }

    @transaction.atomic
    def handle_batch_document_url(self, urls, upload_url_id, notebook, user):
        """
        Handle batch document URL parsing asynchronously using Celery.

        Process multiple document URLs in batch, creating KB item placeholders
        for each and triggering async processing. Returns structured response
        with success/failure breakdown.
        """
        successful = []
        failed = []

        for url in urls:
            try:
                result = self.handle_document_url(
                    url=url,
                    upload_url_id=upload_url_id,
                    notebook=notebook,
                    user=user,
                )
                successful.append(
                    {
                        "url": url,
                        "file_id": result["file_id"],
                        "upload_url_id": result["upload_url_id"],
                    }
                )
            except Exception as e:
                logger.exception(f"Failed to process document URL {url}: {e}")
                failed.append({"url": url, "reason": str(e)})

        return {
            "success": len(failed) == 0,
            "total_submitted": len(urls),
            "successful": successful,
            "failed": failed,
            "status_code": status.HTTP_207_MULTI_STATUS
            if failed
            else status.HTTP_202_ACCEPTED,
        }
