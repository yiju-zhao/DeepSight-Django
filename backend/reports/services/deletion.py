"""
Report Deletion Service following SOLID principles.

This module provides a comprehensive deletion service that handles:
- Celery task termination
- Storage cleanup
- Database cleanup
- Cache cleanup
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from django.core.cache import cache
from celery.result import AsyncResult
from ..models import Report

logger = logging.getLogger(__name__)


# ====== DEPENDENCY INVERSION PRINCIPLE (DIP) ======
# Abstract interfaces for dependencies

class TaskTerminatorInterface(ABC):
    """Interface for terminating Celery tasks"""

    @abstractmethod
    def terminate_task(self, task_id: str, wait_for_termination: bool = True) -> bool:
        """Terminate a Celery task and optionally wait for confirmation"""
        pass


class StorageCleanupInterface(ABC):
    """Interface for storage cleanup operations"""

    @abstractmethod
    def cleanup_report_files(self, report: Report) -> bool:
        """Clean up all storage files associated with a report"""
        pass


class CacheCleanupInterface(ABC):
    """Interface for cache cleanup operations"""

    @abstractmethod
    def cleanup_report_cache(self, job_id: str) -> bool:
        """Clean up cache entries for a report"""
        pass


class ImageCleanupInterface(ABC):
    """Interface for image cleanup operations"""

    @abstractmethod
    def cleanup_report_images(self, report: Report) -> bool:
        """Clean up ReportImage records"""
        pass


class TempCleanupInterface(ABC):
    """Interface for temporary file cleanup"""

    @abstractmethod
    def cleanup_temp_files(self, job_id: str) -> bool:
        """Clean up temporary directories and files"""
        pass


# ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
# Each class has a single, well-defined responsibility

class CeleryTaskTerminator(TaskTerminatorInterface):
    """Handles Celery task termination with proper confirmation"""

    def __init__(self, termination_timeout: int = 10):
        self.termination_timeout = termination_timeout

    def terminate_task(self, task_id: str, wait_for_termination: bool = True) -> bool:
        """Terminate a Celery task and optionally wait for confirmation"""
        try:
            if not task_id:
                logger.warning("No task ID provided for termination")
                return True

            from backend.celery import app as celery_app

            task_result = AsyncResult(task_id)
            initial_state = task_result.state
            logger.info(f"Terminating task {task_id} (initial state: {initial_state})")

            # Only attempt termination if task is active
            if initial_state in ["PENDING", "STARTED", "RETRY"]:
                celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
                logger.info(f"Sent termination signal to task {task_id}")

                if wait_for_termination:
                    return self._wait_for_termination(task_id)
                return True
            else:
                logger.info(f"Task {task_id} already in final state {initial_state}")
                return True

        except Exception as e:
            logger.error(f"Error terminating Celery task {task_id}: {e}")
            return False

    def _wait_for_termination(self, task_id: str) -> bool:
        """Wait for task termination confirmation"""
        start_time = time.time()

        while (time.time() - start_time) < self.termination_timeout:
            task_result = AsyncResult(task_id)
            current_state = task_result.state

            if current_state in ["REVOKED", "FAILURE", "SUCCESS"]:
                logger.info(f"Task {task_id} terminated with state: {current_state}")
                return True

            time.sleep(0.5)

        logger.warning(f"Task {task_id} termination timeout after {self.termination_timeout}s")
        return False


class MinIOStorageCleanup(StorageCleanupInterface):
    """Handles MinIO storage cleanup operations"""

    def cleanup_report_files(self, report: Report) -> bool:
        """Clean up all MinIO storage files for a report"""
        try:
            if not (report.main_report_object_key or report.generated_files):
                logger.info(f"No storage files to clean up for report {report.id}")
                return True

            from infrastructure.storage.adapters import get_storage_adapter
            storage_adapter = get_storage_adapter()

            files_cleaned = 0

            # Clean up main report file
            if report.main_report_object_key:
                try:
                    storage_adapter.delete_file(report.main_report_object_key, str(report.user.id))
                    files_cleaned += 1
                    logger.info(f"Deleted main report file: {report.main_report_object_key}")
                except Exception as e:
                    logger.warning(f"Failed to delete main report file: {e}")

            # Clean up generated files
            if report.generated_files:
                for file_path in report.generated_files:
                    try:
                        storage_adapter.delete_file(file_path, str(report.user.id))
                        files_cleaned += 1
                        logger.info(f"Deleted generated file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete generated file {file_path}: {e}")

            logger.info(f"Cleaned up {files_cleaned} storage files for report {report.id}")
            return True

        except Exception as e:
            logger.error(f"Error cleaning up storage files for report {report.id}: {e}")
            return False


class RedisCacheCleanup(CacheCleanupInterface):
    """Handles Redis cache cleanup operations"""

    def cleanup_report_cache(self, job_id: str) -> bool:
        """Clean up cache entries for a report"""
        try:
            cache_key = f"report_job:{job_id}"
            cache.delete(cache_key)
            logger.info(f"Cleared cache for job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache for job {job_id}: {e}")
            return False


class ReportImageCleanup(ImageCleanupInterface):
    """Handles ReportImage record cleanup"""

    def cleanup_report_images(self, report: Report) -> bool:
        """Clean up ReportImage records associated with a report"""
        try:
            from .image import ImageService
            image_service = ImageService()
            image_service.cleanup_report_images(report)
            logger.info(f"Cleaned up ReportImage records for report {report.id}")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up ReportImage records for report {report.id}: {e}")
            return False


class TemporaryFileCleanup(TempCleanupInterface):
    """Handles temporary file and directory cleanup"""

    def cleanup_temp_files(self, job_id: str) -> bool:
        """Clean up temporary directories and files"""
        try:
            from ..orchestrator import report_orchestrator
            report_orchestrator.cleanup_failed_job(job_id)
            logger.info(f"Cleaned up temporary files for job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up temp files for job {job_id}: {e}")
            return False


# ====== OPEN/CLOSED PRINCIPLE (OCP) ======
# The deletion service is open for extension but closed for modification

class ReportDeletionService:
    """
    Comprehensive report deletion service following SOLID principles.

    This service orchestrates the complete deletion process:
    1. Terminate running Celery tasks
    2. Clean up storage files
    3. Clean up cache entries
    4. Clean up image records
    5. Clean up temporary files
    6. Delete database record
    """

    def __init__(
        self,
        task_terminator: Optional[TaskTerminatorInterface] = None,
        storage_cleanup: Optional[StorageCleanupInterface] = None,
        cache_cleanup: Optional[CacheCleanupInterface] = None,
        image_cleanup: Optional[ImageCleanupInterface] = None,
        temp_cleanup: Optional[TempCleanupInterface] = None
    ):
        # Dependency injection with default implementations
        self.task_terminator = task_terminator or CeleryTaskTerminator()
        self.storage_cleanup = storage_cleanup or MinIOStorageCleanup()
        self.cache_cleanup = cache_cleanup or RedisCacheCleanup()
        self.image_cleanup = image_cleanup or ReportImageCleanup()
        self.temp_cleanup = temp_cleanup or TemporaryFileCleanup()

    def delete_report(self, report: Report) -> Dict[str, Any]:
        """
        Perform complete report deletion with comprehensive cleanup.

        Returns:
            Dict with success status and details of each cleanup step
        """
        result = {
            "success": True,
            "job_id": report.job_id,
            "report_id": str(report.id),
            "steps": {}
        }

        try:
            # Step 1: Terminate Celery task if running
            if report.status in [Report.STATUS_RUNNING, Report.STATUS_PENDING]:
                result["steps"]["task_termination"] = self._terminate_running_task(report)
            else:
                result["steps"]["task_termination"] = {"success": True, "message": "No running task to terminate"}

            # Step 2: Clean up cache
            result["steps"]["cache_cleanup"] = {
                "success": self.cache_cleanup.cleanup_report_cache(report.job_id),
                "message": "Cache cleanup completed"
            }

            # Step 3: Clean up storage files
            result["steps"]["storage_cleanup"] = {
                "success": self.storage_cleanup.cleanup_report_files(report),
                "message": "Storage files cleanup completed"
            }

            # Step 4: Clean up image records
            result["steps"]["image_cleanup"] = {
                "success": self.image_cleanup.cleanup_report_images(report),
                "message": "ReportImage records cleanup completed"
            }

            # Step 5: Clean up temporary files
            result["steps"]["temp_cleanup"] = {
                "success": self.temp_cleanup.cleanup_temp_files(report.job_id),
                "message": "Temporary files cleanup completed"
            }

            # Step 6: Delete database record
            result["steps"]["database_deletion"] = self._delete_database_record(report)

            # Check if all steps succeeded
            failed_steps = [step for step, details in result["steps"].items() if not details["success"]]
            if failed_steps:
                result["success"] = False
                result["failed_steps"] = failed_steps
                logger.warning(f"Report {report.job_id} deletion completed with failures in: {failed_steps}")
            else:
                logger.info(f"Report {report.job_id} deleted successfully with complete cleanup")

            return result

        except Exception as e:
            logger.error(f"Error during report deletion for {report.job_id}: {e}")
            result["success"] = False
            result["error"] = str(e)
            return result

    def _terminate_running_task(self, report: Report) -> Dict[str, Any]:
        """Terminate a running Celery task"""
        try:
            if not report.celery_task_id:
                return {"success": True, "message": "No Celery task ID to terminate"}

            # Update status to cancelled first
            report.update_status(Report.STATUS_CANCELLED, progress="Job cancelled for deletion")

            # Terminate the task
            success = self.task_terminator.terminate_task(report.celery_task_id, wait_for_termination=True)

            # Clean up temp files for cancelled job
            self.temp_cleanup.cleanup_temp_files(report.job_id)

            return {
                "success": success,
                "message": f"Task {report.celery_task_id} {'terminated' if success else 'termination attempted'}"
            }

        except Exception as e:
            logger.error(f"Error terminating task for report {report.job_id}: {e}")
            return {"success": False, "message": f"Task termination failed: {str(e)}"}

    def _delete_database_record(self, report: Report) -> Dict[str, Any]:
        """Delete the database record"""
        try:
            report_id = str(report.id)
            report.delete()
            return {"success": True, "message": f"Database record {report_id} deleted"}
        except Exception as e:
            logger.error(f"Error deleting database record for report {report.id}: {e}")
            return {"success": False, "message": f"Database deletion failed: {str(e)}"}


# ====== LISKOV SUBSTITUTION PRINCIPLE (LSP) ======
# Factory for creating deletion service instances

class DeletionServiceFactory:
    """Factory for creating deletion service instances with different configurations"""

    @staticmethod
    def create_standard_deletion_service() -> ReportDeletionService:
        """Create a deletion service with standard implementations"""
        return ReportDeletionService()

    @staticmethod
    def create_fast_deletion_service() -> ReportDeletionService:
        """Create a deletion service optimized for speed (no task termination wait)"""
        task_terminator = CeleryTaskTerminator(termination_timeout=2)
        return ReportDeletionService(task_terminator=task_terminator)

    @staticmethod
    def create_custom_deletion_service(
        task_terminator: Optional[TaskTerminatorInterface] = None,
        storage_cleanup: Optional[StorageCleanupInterface] = None,
        cache_cleanup: Optional[CacheCleanupInterface] = None,
        image_cleanup: Optional[ImageCleanupInterface] = None,
        temp_cleanup: Optional[TempCleanupInterface] = None
    ) -> ReportDeletionService:
        """Create a deletion service with custom implementations"""
        return ReportDeletionService(
            task_terminator=task_terminator,
            storage_cleanup=storage_cleanup,
            cache_cleanup=cache_cleanup,
            image_cleanup=image_cleanup,
            temp_cleanup=temp_cleanup
        )