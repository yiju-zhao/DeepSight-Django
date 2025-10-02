"""
Unified ImageService under the new services layout.
Implements image handling by consolidating logic used for report images.
"""

import logging
import os
import glob
import json
from pathlib import Path
from typing import List, Tuple, Dict, Optional

from django.db import transaction
from django.conf import settings
from notebooks.models import KnowledgeBaseImage
from notebooks.utils.storage import get_minio_backend
from reports.models import Report, ReportImage
from reports.utils import (
    extract_figure_ids_from_content,
    extract_figure_data_from_markdown,
    convert_to_uuid_objects,
    ImageInsertionService,
    DatabaseUrlProvider,
)

logger = logging.getLogger(__name__)


class ImageService:
    """Service for handling report image operations including copying and managing figures."""

    def __init__(self):
        self._minio_backend = None

    def _get_minio_backend(self):
        if self._minio_backend is None:
            self._minio_backend = get_minio_backend()
        return self._minio_backend

    def find_images_by_figure_ids(self, figure_ids: List[str], user_id: int) -> List[KnowledgeBaseImage]:
        """Find KnowledgeBaseImage records by figure_id field."""
        if not figure_ids:
            return []

        uuid_figure_ids = convert_to_uuid_objects(figure_ids)

        images = (
            KnowledgeBaseImage.objects.filter(
                figure_id__in=uuid_figure_ids, knowledge_base_item__user__id=user_id
            )
            .select_related("knowledge_base_item")
        )

        logger.info(f"Found {images.count()} images for {len(figure_ids)} figure IDs")
        return list(images)

    def copy_images_to_report(self, report: Report, kb_images: List[KnowledgeBaseImage]) -> List[ReportImage]:
        """Copy selected images from knowledge base to report folder and create ReportImage records."""
        if not kb_images:
            logger.info("No images to copy")
            return []

        report_images: List[ReportImage] = []

        notebook_part = report.notebooks.id if report.notebooks else "standalone"
        report_image_folder = f"{report.user.id}/notebook/{notebook_part}/report/{report.id}/images"

        with transaction.atomic():
            for kb_image in kb_images:
                try:
                    source_key = kb_image.minio_object_key
                    file_extension = os.path.splitext(source_key)[1] or ".jpg"
                    dest_key = f"{report_image_folder}/{kb_image.figure_id}{file_extension}"

                    success = self._get_minio_backend().copy_file(source_key, dest_key)
                    if not success:
                        logger.error(
                            f"Failed to copy image {source_key} to {dest_key}"
                        )
                        continue

                    report_image, created = ReportImage.objects.get_or_create(
                        figure_id=kb_image.figure_id,
                        report=report,
                        defaults={
                            "image_caption": kb_image.image_caption,
                            "report_figure_minio_object_key": dest_key,
                            "image_metadata": kb_image.image_metadata,
                            "content_type": kb_image.content_type,
                            "file_size": kb_image.file_size,
                        },
                    )

                    report_images.append(report_image)
                    logger.debug(
                        f"{'Created' if created else 'Found existing'} ReportImage for figure_id: {kb_image.figure_id}"
                    )
                except Exception as e:
                    logger.error(f"Error copying image {kb_image.figure_id}: {e}")
                    continue

        logger.info(f"Successfully copied {len(report_images)} images to report {report.id}")
        return report_images

    def process_report_images(self, report: Report, content: str) -> Tuple[List[ReportImage], str]:
        """Extract figure IDs from content, copy images, and return updated content."""
        figure_ids = extract_figure_ids_from_content(content)
        if not figure_ids:
            logger.info("No figure IDs found in report content")
            return [], content

        kb_images = self.find_images_by_figure_ids(figure_ids, report.user.id)
        if not kb_images:
            logger.warning(f"No images found for figure IDs: {figure_ids}")
            return [], content

        report_images = self.copy_images_to_report(report, kb_images)
        updated_content = self._insert_figure_images(content, report_images, report.id)
        return report_images, updated_content

    def _insert_figure_images(
        self, content: str, report_images: List[ReportImage], report_id=None
    ) -> str:
        if not report_images:
            return content

        # Extract figure IDs from ReportImage objects
        figure_ids = [str(img.figure_id) for img in report_images]

        service = ImageInsertionService(DatabaseUrlProvider())
        return service.insert_images_into_content(content, figure_ids)

    # Public convenience to align with existing call sites
    def insert_figure_images(
        self, content: str, report_images: List[ReportImage], report_id=None
    ) -> str:
        return self._insert_figure_images(content, report_images, report_id)

    def cleanup_report_images(self, report: Report):
        """Clean up images for a report (used when report is deleted)."""
        try:
            report_images = ReportImage.objects.filter(report=report)
            for img in report_images:
                try:
                    self._get_minio_backend().delete_file(
                        img.report_figure_minio_object_key
                    )
                except Exception as e:
                    logger.error(
                        f"Error deleting image {img.report_figure_minio_object_key}: {e}"
                    )
            count = report_images.count()
            report_images.delete()
            logger.info(f"Cleaned up {count} images for report {report.id}")
        except Exception as e:
            logger.error(f"Error cleaning up report images: {e}")

    # =============================================================================
    # FIGURE DATA SERVICE METHODS (Merged from FigureDataService)
    # =============================================================================

    def create_knowledge_base_figure_data(self, user_id: int, file_id: str, figure_data: List[Dict]) -> Optional[str]:
        """
        Store figure data in database for a knowledge base item.
        This replaces the old figure_data.json file approach.

        Args:
            user_id: User ID
            file_id: Knowledge base file ID (without f_ prefix)
            figure_data: List of figure dictionaries

        Returns:
            str: Success message or None if failed
        """
        try:
            from notebooks.services.knowledge_base_service import KnowledgeBaseService

            kb_service = KnowledgeBaseService()

            # Update images from figure data
            success = kb_service.update_images_from_figure_data(
                kb_item_id=int(file_id),
                figure_data=figure_data,
                user_id=user_id
            )

            if success:
                logger.info(f"Stored figure data in database for kb_item {file_id}")
                return f"database_storage_kb_{file_id}"  # Return a success indicator
            else:
                logger.warning(f"Failed to store figure data in database for kb_item {file_id}")
                return None

        except Exception as e:
            logger.error(f"Error storing figure data in database for kb_item {file_id}: {e}")
            return None

    def create_combined_figure_data(self, report, selected_file_ids: List[str]) -> Optional[str]:
        """
        Get combined figure data from database for a report.
        This replaces creating combined figure_data.json files.

        Args:
            report: Report instance
            selected_file_ids: List of knowledge base file IDs (with f_ prefix)

        Returns:
            str: Success indicator or None if no figure data found
        """
        try:
            from notebooks.services.knowledge_base_service import KnowledgeBaseService

            kb_service = KnowledgeBaseService()

            # Get combined figure data from database
            combined_figure_data = kb_service.get_combined_figure_data_for_files(
                file_ids=selected_file_ids,
                user_id=report.user.pk
            )

            if not combined_figure_data:
                logger.info("No figure data found in database for selected files")
                return None

            # Store the figure data directly in the report instance for immediate use
            # This avoids the need to create temporary files
            report._cached_figure_data = combined_figure_data

            logger.info(f"Retrieved combined figure data from database: {len(combined_figure_data)} figures")
            return f"database_combined_{report.id}"  # Return success indicator

        except Exception as e:
            logger.error(f"Error creating combined figure data from database: {e}")
            return None

    def get_cached_figure_data(self, user_id: int, reference: Optional[str]) -> Optional[Dict]:
        """
        Get cached figure data for a user and reference.

        Args:
            user_id: User ID
            reference: Reference to the figure data (report ID, notebook ID, etc.)

        Returns:
            Dict: Figure data dictionary or None if not found
        """
        try:
            # This method provides a unified interface for getting figure data
            # Implementation can be expanded based on caching needs
            if not reference:
                return None

            # For now, delegate to load_combined_figure_data
            figure_list = self.load_combined_figure_data(f"database_kb_{reference}")

            if figure_list:
                return {"figures": figure_list}

            return None

        except Exception as e:
            logger.error(f"Error getting cached figure data for user {user_id}, reference {reference}: {e}")
            return None

    def load_combined_figure_data(self, figure_data_reference: str) -> List[Dict]:
        """
        Load figure data from KnowledgeBaseImage table using database references.
        No longer uses JSON files - everything comes from database.
        """
        if not figure_data_reference:
            return []

        try:
            # Check if this is a database reference
            if figure_data_reference.startswith('database_'):
                # Extract identifiers from the reference
                if 'combined_' in figure_data_reference:
                    # This is a combined figure data request for a report
                    report_id = figure_data_reference.split('_')[-1]

                    # Try to get from cached data first
                    from reports.models import Report
                    try:
                        report = Report.objects.get(id=report_id)
                        if hasattr(report, '_cached_figure_data'):
                            return report._cached_figure_data
                    except Exception:
                        pass

                    # If no cached data, return empty list
                    logger.warning(f"No cached figure data found for report {report_id}")
                    return []

                elif 'kb_' in figure_data_reference:
                    # This is a single knowledge base item request
                    kb_item_id = figure_data_reference.split('_')[-1]
                    return self._load_kb_item_figure_data(int(kb_item_id))

            # Direct knowledge base item ID (new approach)
            elif figure_data_reference.isdigit():
                kb_item_id = int(figure_data_reference)
                return self._load_kb_item_figure_data(kb_item_id)

        except Exception as e:
            logger.error(f"Error loading figure data from reference {figure_data_reference}: {e}")

        return []

    def _load_kb_item_figure_data(self, kb_item_id: int) -> List[Dict]:
        """Load figure data directly from KnowledgeBaseImage table"""
        try:
            from notebooks.models import KnowledgeBaseImage

            # Get all images for this knowledge base item
            images = KnowledgeBaseImage.objects.filter(
                knowledge_base_item_id=kb_item_id
            ).order_by('created_at')

            figure_data = []
            for image in images:
                # Use to_figure_data_dict method for consistency
                figure_dict = image.to_figure_data_dict()
                # Add additional metadata for backwards compatibility if needed
                figure_dict.update({
                    'content_type': image.content_type,
                    'file_size': image.file_size,
                    'minio_object_key': image.minio_object_key,
                    'kb_item_id': kb_item_id,
                })
                figure_data.append(figure_dict)

            logger.info(f"Loaded {len(figure_data)} figures for KB item {kb_item_id}")
            return figure_data

        except Exception as e:
            logger.error(f"Error loading figure data for KB item {kb_item_id}: {e}")
            return []

    def get_figure_data_for_knowledge_base_item(self, user_id: int, file_id: str) -> List[Dict]:
        """
        Get figure data for a single knowledge base item from database.
        This is a new method that directly queries the database.

        Args:
            user_id: User ID
            file_id: Knowledge base file ID (without f_ prefix)

        Returns:
            List of figure data dictionaries
        """
        try:
            from notebooks.services.knowledge_base_service import KnowledgeBaseService

            kb_service = KnowledgeBaseService()

            return kb_service.get_images_for_knowledge_base_item(
                kb_item_id=int(file_id),
                user_id=user_id
            )

        except Exception as e:
            logger.error(f"Error getting figure data for kb_item {file_id}: {e}")
            return []

__all__ = ["ImageService"]
