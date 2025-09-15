"""
Custom managers and querysets for reports models.

Following Django best practices for database query optimization
and common query patterns.
"""

import logging
from django.db import models
from django.db.models import Q, Count
from django.utils import timezone

logger = logging.getLogger(__name__)


class ReportQuerySet(models.QuerySet):
    """Custom queryset for report-related queries."""

    def for_user(self, user):
        """Filter reports for a specific user."""
        return self.filter(user=user)

    def for_notebook(self, notebook):
        """Filter reports for a specific notebook."""
        return self.filter(notebooks=notebook)

    def by_status(self, status):
        """Filter reports by status."""
        return self.filter(status=status)

    def pending(self):
        """Filter pending reports."""
        return self.filter(status='pending')

    def running(self):
        """Filter running reports."""
        return self.filter(status='running')

    def completed(self):
        """Filter completed reports."""
        return self.filter(status='completed')

    def failed(self):
        """Filter failed reports."""
        return self.filter(status='failed')

    def cancelled(self):
        """Filter cancelled reports."""
        return self.filter(status='cancelled')

    def active(self):
        """Filter active (pending or running) reports."""
        return self.filter(status__in=['pending', 'running'])

    def finished(self):
        """Filter finished reports (completed, failed, or cancelled)."""
        return self.filter(status__in=['completed', 'failed', 'cancelled'])

    def with_content(self):
        """Filter reports that have generated content."""
        return self.filter(
            Q(result_content__isnull=False, result_content__gt='') |
            Q(main_report_object_key__isnull=False, main_report_object_key__gt='')
        )

    def by_provider(self, provider):
        """Filter reports by model provider."""
        return self.filter(model_provider=provider)

    def by_retriever(self, retriever):
        """Filter reports by retriever type."""
        return self.filter(retriever=retriever)

    def by_prompt_type(self, prompt_type):
        """Filter reports by prompt type."""
        return self.filter(prompt_type=prompt_type)

    def recent(self, days=7):
        """Filter reports created in the last N days."""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=cutoff_date)

    def search_content(self, query):
        """Simple text search in topic, title, and content."""
        return self.filter(
            Q(topic__icontains=query) |
            Q(article_title__icontains=query) |
            Q(result_content__icontains=query)
        )

    def with_images(self):
        """Filter reports that have associated images."""
        return self.filter(images__isnull=False).distinct()

    def with_files(self):
        """Filter reports that have generated files."""
        return self.exclude(
            Q(main_report_object_key__isnull=True) | Q(main_report_object_key='')
        )

    def with_metadata(self):
        """Annotate reports with useful metadata counts."""
        return self.annotate(
            image_count=Count('images', distinct=True),
            generated_file_count=models.Case(
                models.When(generated_files__isnull=False, then=models.Func(
                    'generated_files', function='jsonb_array_length'
                )),
                default=0,
                output_field=models.IntegerField()
            )
        )


class ReportManager(models.Manager):
    """Custom manager for Report model."""

    def get_queryset(self):
        return ReportQuerySet(self.model, using=self._db)

    def for_user(self, user):
        return self.get_queryset().for_user(user)

    def for_notebook(self, notebook):
        return self.get_queryset().for_notebook(notebook)

    def by_status(self, status):
        return self.get_queryset().by_status(status)

    def pending(self):
        return self.get_queryset().pending()

    def running(self):
        return self.get_queryset().running()

    def completed(self):
        return self.get_queryset().completed()

    def failed(self):
        return self.get_queryset().failed()

    def cancelled(self):
        return self.get_queryset().cancelled()

    def active(self):
        return self.get_queryset().active()

    def finished(self):
        return self.get_queryset().finished()

    def with_content(self):
        return self.get_queryset().with_content()

    def by_provider(self, provider):
        return self.get_queryset().by_provider(provider)

    def by_retriever(self, retriever):
        return self.get_queryset().by_retriever(retriever)

    def by_prompt_type(self, prompt_type):
        return self.get_queryset().by_prompt_type(prompt_type)

    def recent(self, days=7):
        return self.get_queryset().recent(days)

    def search_content(self, query):
        return self.get_queryset().search_content(query)

    def with_images(self):
        return self.get_queryset().with_images()

    def with_files(self):
        return self.get_queryset().with_files()

    def with_metadata(self):
        return self.get_queryset().with_metadata()

    def bulk_update_status(self, report_ids, status, progress=None, error=None):
        """Bulk update status for multiple reports."""
        update_fields = {'status': status, 'updated_at': timezone.now()}
        if progress is not None:
            update_fields['progress'] = progress
        if error is not None:
            update_fields['error_message'] = error

        return self.filter(id__in=report_ids).update(**update_fields)

    def cleanup_old_failed_reports(self, days=30):
        """Remove old failed reports."""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        old_failed = self.filter(
            status='failed',
            created_at__lt=cutoff_date
        )
        count = old_failed.count()
        old_failed.delete()
        return count


class ReportImageQuerySet(models.QuerySet):
    """Custom queryset for report image queries."""

    def for_report(self, report):
        """Filter images for a specific report."""
        return self.filter(report=report)

    def by_content_type(self, content_type):
        """Filter images by content type."""
        return self.filter(content_type=content_type)

    def with_caption(self):
        """Filter images that have captions."""
        return self.exclude(Q(image_caption='') | Q(image_caption__isnull=True))

    def recent(self, days=7):
        """Filter images created in the last N days."""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=cutoff_date)

    def by_size_range(self, min_size=None, max_size=None):
        """Filter images by file size range."""
        qs = self
        if min_size is not None:
            qs = qs.filter(file_size__gte=min_size)
        if max_size is not None:
            qs = qs.filter(file_size__lte=max_size)
        return qs


class ReportImageManager(models.Manager):
    """Custom manager for ReportImage model."""

    def get_queryset(self):
        return ReportImageQuerySet(self.model, using=self._db)

    def for_report(self, report):
        return self.get_queryset().for_report(report)

    def by_content_type(self, content_type):
        return self.get_queryset().by_content_type(content_type)

    def with_caption(self):
        return self.get_queryset().with_caption()

    def recent(self, days=7):
        return self.get_queryset().recent(days)

    def by_size_range(self, min_size=None, max_size=None):
        return self.get_queryset().by_size_range(min_size, max_size)