"""
Celery tasks for report generation.
"""

import logging
import re
import time
from typing import Dict, Any
from celery import shared_task
from .orchestrator import report_orchestrator
from core.utils.sse import publish_notebook_event

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_report_generation(self, report_id: int):
    """Process report generation job - this runs in the background worker"""
    try:
        logger.info(f"Starting report generation task for report {report_id}")

        # Update job status to running
        from .models import Report
        try:
            report = Report.objects.get(id=report_id)
        except Report.DoesNotExist:
            logger.error(f"Report {report_id} not found")
            raise Exception(f"Report {report_id} not found")

        # Check if job was cancelled before we start
        if report.status == Report.STATUS_CANCELLED:
            logger.info(f"Report {report_id} was cancelled before processing started")
            return {"status": "cancelled", "message": "Report was cancelled"}

        # Check if task was revoked by Celery
        if self.request.called_directly is False:  # Only check if running in worker
            from celery.result import AsyncResult
            task_result = AsyncResult(self.request.id)
            if task_result.state == 'REVOKED':
                logger.info(f"Task {self.request.id} was revoked, aborting report generation")
                return {"status": "revoked", "message": "Task was revoked"}

        # Mark as running (status only)
        try:
            report.update_status(Report.STATUS_RUNNING)
        except Exception:
            # Non-fatal: continue generation even if status update fails
            pass

        # Publish STARTED event via SSE
        if report.notebooks:
            publish_notebook_event(
                notebook_id=str(report.notebooks.id),
                entity="report",
                entity_id=str(report.id),
                status="STARTED",
            )

        # Generate the report
        result = report_orchestrator.generate_report(report_id)

        if result.get('success', False):
            # Update job with success
            report_orchestrator.update_job_result(report_id, result, Report.STATUS_COMPLETED)

            # Publish SUCCESS event via SSE
            if report.notebooks:
                publish_notebook_event(
                    notebook_id=str(report.notebooks.id),
                    entity="report",
                    entity_id=str(report.id),
                    status="SUCCESS",
                    payload={
                        "article_title": report.article_title,
                        "pdf_object_key": result.get("pdf_object_key"),
                    }
                )

            logger.info(f"Successfully completed report generation for report {report_id}")
            return result
        else:
            # Handle generation failure
            error_msg = result.get('error_message', 'Report generation failed')
            report_orchestrator.update_job_error(report_id, error_msg)

            # Publish FAILURE event via SSE
            if report.notebooks:
                publish_notebook_event(
                    notebook_id=str(report.notebooks.id),
                    entity="report",
                    entity_id=str(report.id),
                    status="FAILURE",
                    payload={"error": error_msg}
                )

            raise Exception(error_msg)

    except Exception as e:
        logger.error(f"Error processing report generation for report {report_id}: {e}")

        # Update job with error
        try:
            from .models import Report
            report = Report.objects.get(id=report_id)
            report_orchestrator.update_job_error(str(report.id), str(e))

            # Publish FAILURE event via SSE
            if report.notebooks:
                publish_notebook_event(
                    notebook_id=str(report.notebooks.id),
                    entity="report",
                    entity_id=str(report.id),
                    status="FAILURE",
                    payload={"error": str(e)}
                )
        except Report.DoesNotExist:
            logger.error(f"Could not update error for report {report_id} - report not found")

        # Re-raise for Celery to handle
        raise


@shared_task
def cleanup_old_reports():
    """Clean up old report jobs and associated files"""
    try:
        logger.info("Starting cleanup of old reports")
        report_orchestrator.cleanup_old_jobs()
        logger.info("Completed cleanup of old reports")
        return {"status": "success", "message": "Cleanup completed"}
    
    except Exception as e:
        logger.error(f"Error during report cleanup: {e}")
        raise


@shared_task(bind=True)
def delete_report_and_cleanup(self, report_id: int):
    """Delete a report and perform all associated cleanup operations."""
    try:
        logger.info(f"Deleting report {report_id} and performing cleanup")

        from .models import Report
        report = Report.objects.get(id=report_id)
        

        # Cleanup ReportImage records
        try:
            from .services.job import JobService
            job_service = JobService()
            job_service._cleanup_report_images_on_cancellation(report)
        except Exception as e:
            logger.warning(f"Failed to cleanup ReportImage records for report {report_id}: {e}")

        # Additional cleanup operations can be added here
        # (file system cleanup, cache cleanup, etc.)

        # Delete the report record
        report.delete()

        logger.info(f"Successfully deleted report {report_id} and completed cleanup")
        return {"status": "deleted", "report_id": report_id}

    except Report.DoesNotExist:
        logger.error(f"Report {report_id} not found for deletion")
        return {"status": "failed", "report_id": report_id, "message": "Report not found"}
    except Exception as e:
        logger.error(f"Error deleting report {report_id}: {e}")
        raise


@shared_task
def validate_report_configuration(config: Dict[str, Any]):
    """Validate report configuration in background"""
    try:
        logger.info("Validating report configuration")
        
        is_valid = report_orchestrator.validate_report_configuration(config)
        validation_results = report_orchestrator.validate_configuration_settings(config)
        
        return {
            "is_valid": is_valid,
            "validation_results": validation_results,
            "supported_options": report_orchestrator.get_supported_options()
        }
    
    except Exception as e:
        logger.error(f"Error validating report configuration: {e}")
        return {
            "is_valid": False,
            "error": str(e),
            "validation_results": {},
            "supported_options": {}
        }
        
