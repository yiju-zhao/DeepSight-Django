"""
Conference data processing services

Centralizes data processing logic used across views and serializers.
"""

import hashlib
import logging
import uuid

from django.db import transaction
from rest_framework import status

from .utils import split_comma_values, split_semicolon_values

logger = logging.getLogger(__name__)


class PublicationDataService:
    """Service for processing publication-related data"""

    def process_publication_for_table(self, publication) -> dict:
        """Process a publication instance for table display

        Args:
            publication: Publication model instance

        Returns:
            Dictionary with processed data including split fields
        """
        return {
            "id": publication.id,
            "title": publication.title,
            "authors": publication.authors,
            "rating": publication.rating,
            "research_topic": publication.research_topic,
            "session": publication.session,
            "aff_unique": publication.aff_unique,
            "aff_country_unique": publication.aff_country_unique,
            "keywords": publication.keywords,
            "pdf_url": publication.pdf_url,
            "github": publication.github,
            "site": publication.site,
            "instance_year": publication.instance.year,
            "venue_name": publication.instance.venue.name,
            # Split fields
            "authors_list": split_comma_values(publication.authors),
            "countries_list": split_comma_values(publication.aff_country_unique),
            "keywords_list": split_semicolon_values(publication.keywords),
        }

    def process_publications_for_aggregation(self, publications) -> dict:
        """Process publications for KPI and chart calculations

        Args:
            publications: QuerySet or list of Publication instances

        Returns:
            Dictionary with aggregated data using split values
        """
        all_authors = []
        all_countries = []  # Changed from set to list to preserve duplicates for counting
        all_affiliations = []  # Changed from set to list to preserve duplicates for counting
        all_keywords = []

        for pub in publications:
            # Authors (comma-separated)
            if pub.authors:
                all_authors.extend(split_comma_values(pub.authors))

            # Countries (comma-separated) - preserve duplicates for counting
            if pub.aff_country_unique:
                countries = split_comma_values(pub.aff_country_unique)
                all_countries.extend(countries)

            # Affiliations (semicolon-separated) - preserve duplicates for counting
            if pub.aff_unique:
                affiliations = split_semicolon_values(pub.aff_unique)
                all_affiliations.extend(affiliations)

            # Keywords (semicolon-separated)
            if pub.keywords:
                keywords = split_semicolon_values(pub.keywords)
                all_keywords.extend(keywords)

        return {
            "unique_authors": len(set(all_authors)),
            "unique_countries": len(set(all_countries)),  # Count unique for KPIs
            "unique_affiliations": len(set(all_affiliations)),  # Count unique for KPIs
            "all_authors": all_authors,
            "all_countries": all_countries,  # Keep duplicates for chart counting
            "all_affiliations": all_affiliations,  # Keep duplicates for chart counting
            "all_keywords": all_keywords,
        }


class ConferenceImportService:
    """Service for importing conference publications to notebooks"""

    def __init__(self):
        pass

    def _calculate_source_hash(self, url: str, user_id: int) -> str:
        """Calculate source hash for duplicate detection"""
        source_string = f"{url}_{user_id}"
        return hashlib.sha256(source_string.encode()).hexdigest()

    def _extract_publication_metadata(self, publication) -> dict:
        """Extract metadata from publication for storage in KB item"""
        return {
            "source_type": "conference_publication",
            "publication_id": str(publication.id),
            "title": publication.title,
            "authors": publication.authors,
            "conference": f"{publication.instance.venue.name} {publication.instance.year}",
            "year": publication.instance.year,
            "venue": publication.instance.venue.name,
            "doi": publication.doi if publication.doi else None,
            "abstract": publication.abstract
            if hasattr(publication, "abstract")
            else None,
            "keywords": publication.keywords
            if hasattr(publication, "keywords")
            else None,
            "research_topic": (
                publication.research_topic
                if hasattr(publication, "research_topic")
                else None
            ),
        }

    def _validate_publications(
        self, publication_ids: list[str], user_id: int, notebook_id: str = None
    ) -> dict:
        """
        Validate publications and extract valid PDF URLs.

        Returns:
            Dict with valid_publications, skipped_no_url, and skipped_duplicate lists
        """
        from notebooks.models import KnowledgeBaseItem
        from .models import Publication

        valid_publications = []
        skipped_no_url = []
        skipped_duplicate = []

        for pub_id in publication_ids:
            try:
                publication = Publication.objects.select_related("instance__venue").get(
                    id=pub_id
                )

                # Check if PDF URL exists
                if not publication.pdf_url or publication.pdf_url.strip() == "":
                    skipped_no_url.append(
                        {
                            "publication_id": str(publication.id),
                            "title": publication.title,
                            "reason": "No PDF URL available",
                        }
                    )
                    continue

                # Check for duplicates if notebook_id provided
                if notebook_id:
                    source_hash = self._calculate_source_hash(
                        publication.pdf_url, user_id
                    )
                    existing = KnowledgeBaseItem.objects.filter(
                        notebook_id=notebook_id, source_hash=source_hash
                    ).first()

                    if existing:
                        skipped_duplicate.append(
                            {
                                "publication_id": str(publication.id),
                                "title": publication.title,
                                "reason": "Already exists in notebook",
                                "existing_item_id": str(existing.id),
                            }
                        )
                        continue

                valid_publications.append(publication)

            except Publication.DoesNotExist:
                logger.warning(f"Publication {pub_id} not found")
                skipped_no_url.append(
                    {
                        "publication_id": str(pub_id),
                        "title": "Unknown",
                        "reason": "Publication not found",
                    }
                )
            except Exception as e:
                logger.exception(f"Error validating publication {pub_id}: {e}")
                skipped_no_url.append(
                    {
                        "publication_id": str(pub_id),
                        "title": "Unknown",
                        "reason": str(e),
                    }
                )

        return {
            "valid_publications": valid_publications,
            "skipped_no_url": skipped_no_url,
            "skipped_duplicate": skipped_duplicate,
        }

    def _get_or_create_batch_job(self, notebook, total_items: int):
        """
        Get active batch job for notebook or create new one.
        Supports appending to active batch.
        """
        from notebooks.models import BatchJob

        # Check for active conference_import job for this notebook
        active_job = (
            BatchJob.objects.filter(
                notebook=notebook,
                job_type="conference_import",
                status__in=["pending", "processing"],
            )
            .order_by("-created_at")
            .first()
        )

        if active_job:
            # Append to existing batch
            logger.info(
                f"Appending to active batch job {active_job.id} for notebook {notebook.id}"
            )
            active_job.total_items += total_items
            active_job.save(update_fields=["total_items"])
            return active_job, True  # True indicates appended

        # Create new batch job
        batch_job = BatchJob.objects.create(
            notebook=notebook,
            job_type="conference_import",
            status="pending",
            total_items=total_items,
        )
        logger.info(f"Created new batch job {batch_job.id} for notebook {notebook.id}")
        return batch_job, False  # False indicates new job

    @transaction.atomic
    def import_publications_to_notebook(
        self,
        publication_ids: list[str],
        notebook,
        user,
    ) -> dict:
        """
        Import conference publications to a notebook.

        Args:
            publication_ids: List of publication UUIDs to import
            notebook: Notebook instance to import into
            user: User performing the import

        Returns:
            Dict with import results including success/failure breakdown
        """
        from notebooks.services.url_service import URLService

        # Validate publications and extract PDF URLs
        validation_result = self._validate_publications(
            publication_ids, user.id, str(notebook.id)
        )

        valid_publications = validation_result["valid_publications"]
        skipped_no_url = validation_result["skipped_no_url"]
        skipped_duplicate = validation_result["skipped_duplicate"]

        # If no valid publications, return early
        if not valid_publications:
            return {
                "success": False,
                "total_requested": len(publication_ids),
                "imported": 0,
                "skipped": len(skipped_no_url) + len(skipped_duplicate),
                "skipped_no_url": skipped_no_url,
                "skipped_duplicate": skipped_duplicate,
                "batch_job_id": None,
                "appended_to_batch": False,
                "message": "No valid publications to import",
                "status_code": status.HTTP_400_BAD_REQUEST,
            }

        # Create or get batch job
        batch_job, appended = self._get_or_create_batch_job(
            notebook, len(valid_publications)
        )

        # Generate unique upload_url_id for this import batch
        upload_url_id = str(uuid.uuid4())

        # Prepare URLs and metadata for batch processing
        urls_with_metadata = []
        for publication in valid_publications:
            urls_with_metadata.append(
                {
                    "url": publication.pdf_url,
                    "metadata": self._extract_publication_metadata(publication),
                    "title": publication.title[:100],  # Truncate for KB item title
                }
            )

        # Use URLService to handle batch document URL processing
        url_service = URLService()
        successful_imports = []
        failed_imports = []

        for item in urls_with_metadata:
            try:
                result = url_service.handle_document_url(
                    url=item["url"],
                    upload_url_id=upload_url_id,
                    notebook=notebook,
                    user=user,
                )

                # Update the created KB item with publication metadata
                from notebooks.models import KnowledgeBaseItem

                kb_item = KnowledgeBaseItem.objects.get(id=result["file_id"])
                kb_item.title = item["title"]
                kb_item.metadata.update(item["metadata"])
                kb_item.save(update_fields=["title", "metadata"])

                successful_imports.append(
                    {
                        "publication_id": item["metadata"]["publication_id"],
                        "title": item["title"],
                        "kb_item_id": result["file_id"],
                        "url": item["url"],
                    }
                )

            except Exception as e:
                logger.exception(f"Failed to import publication: {e}")
                failed_imports.append(
                    {
                        "publication_id": item["metadata"]["publication_id"],
                        "title": item["title"],
                        "url": item["url"],
                        "reason": str(e),
                    }
                )

        # Determine overall success
        all_skipped = len(skipped_no_url) + len(skipped_duplicate)
        total_processed = len(successful_imports) + len(failed_imports)

        return {
            "success": len(failed_imports) == 0 and len(successful_imports) > 0,
            "total_requested": len(publication_ids),
            "imported": len(successful_imports),
            "failed": len(failed_imports),
            "skipped": all_skipped,
            "skipped_no_url": skipped_no_url,
            "skipped_duplicate": skipped_duplicate,
            "successful_imports": successful_imports,
            "failed_imports": failed_imports,
            "batch_job_id": str(batch_job.id),
            "appended_to_batch": appended,
            "message": self._generate_summary_message(
                len(successful_imports),
                len(failed_imports),
                all_skipped,
                appended,
            ),
            "status_code": self._determine_status_code(
                len(successful_imports), len(failed_imports), all_skipped
            ),
        }

    def _generate_summary_message(
        self, imported: int, failed: int, skipped: int, appended: bool
    ) -> str:
        """Generate human-readable summary message"""
        parts = []

        if imported > 0:
            parts.append(f"{imported} publication(s) imported successfully")

        if failed > 0:
            parts.append(f"{failed} failed")

        if skipped > 0:
            parts.append(f"{skipped} skipped")

        if appended:
            parts.append("(added to existing import batch)")

        return "; ".join(parts) if parts else "No publications processed"

    def _determine_status_code(self, imported: int, failed: int, skipped: int) -> int:
        """Determine appropriate HTTP status code based on results"""
        if imported > 0 and failed == 0:
            return status.HTTP_202_ACCEPTED  # All succeeded
        elif imported > 0 and (failed > 0 or skipped > 0):
            return status.HTTP_207_MULTI_STATUS  # Partial success
        elif imported == 0 and (failed > 0 or skipped > 0):
            return status.HTTP_400_BAD_REQUEST  # All failed
        else:
            return status.HTTP_400_BAD_REQUEST  # Nothing processed

    def get_active_imports(self, user) -> list[dict]:
        """
        Get active and recent conference import jobs for a user.

        Returns list of import jobs with progress information.
        """
        from notebooks.models import BatchJob
        from datetime import timedelta
        from django.utils import timezone

        # Get imports from last 24 hours
        cutoff_time = timezone.now() - timedelta(hours=24)

        batch_jobs = (
            BatchJob.objects.filter(
                notebook__user=user,
                job_type="conference_import",
                created_at__gte=cutoff_time,
            )
            .select_related("notebook")
            .order_by("-created_at")[:10]  # Limit to most recent 10
        )

        results = []
        for job in batch_jobs:
            progress_percentage = (
                (job.completed_items / job.total_items * 100)
                if job.total_items > 0
                else 0
            )

            results.append(
                {
                    "batch_job_id": str(job.id),
                    "notebook_id": str(job.notebook.id),
                    "notebook_name": job.notebook.name,
                    "status": job.status,
                    "total_items": job.total_items,
                    "completed_items": job.completed_items,
                    "failed_items": job.failed_items,
                    "progress_percentage": round(progress_percentage, 1),
                    "created_at": job.created_at.isoformat(),
                    "updated_at": job.updated_at.isoformat(),
                }
            )

        return results


# Singleton instances for easy import
publication_data_service = PublicationDataService()
conference_import_service = ConferenceImportService()
