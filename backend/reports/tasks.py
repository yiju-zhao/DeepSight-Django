"""
Celery tasks for report generation.
"""

import logging
import re
import time
from typing import Dict, Any
from celery import shared_task
from .orchestrator import report_orchestrator

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_report_generation(self, report_id: int):
    """
    Process report generation job with graceful termination handling.
    This task is designed to handle termination signals gracefully and update
    the database status appropriately even when cancelled.
    """
    from .models import Report
    import signal
    import sys

    job_id = None
    progress_handler = None
    root_logger = None
    cancellation_requested = False

    def graceful_termination_handler(signum, frame):
        """Handle termination signals gracefully by updating database status"""
        nonlocal job_id, cancellation_requested
        logger.warning(f"Task {self.request.id} received termination signal {signum}")

        # Set cancellation flag
        cancellation_requested = True

        if job_id:
            try:
                # Update job status to cancelled in database
                report = Report.objects.get(job_id=job_id)
                report.update_status(
                    Report.STATUS_CANCELLED,
                    progress="Task terminated by cancellation request"
                )
                logger.info(f"Updated job {job_id} status to CANCELLED due to termination signal")
            except Exception as e:
                logger.error(f"Failed to update status during termination for job {job_id}: {e}")

        # Clean up progress handler
        if progress_handler and root_logger:
            try:
                root_logger.removeHandler(progress_handler)
            except Exception:
                pass

        # Force termination by raising an exception that will be caught by Celery
        logger.info(f"Task {self.request.id} exiting due to termination signal {signum}")
        raise KeyboardInterrupt(f"Task terminated by signal {signum}")

    def check_cancellation():
        """Check if cancellation has been requested and raise KeyboardInterrupt if so"""
        nonlocal job_id, cancellation_requested

        if cancellation_requested:
            logger.info(f"Task {self.request.id} detected cancellation flag")
            raise KeyboardInterrupt("Task cancellation detected via flag")

        if job_id:
            try:
                # Check database status
                report = Report.objects.get(job_id=job_id)
                if report.status == Report.STATUS_CANCELLED:
                    logger.info(f"Task {self.request.id} detected cancellation in database")
                    raise KeyboardInterrupt("Task was cancelled (detected in database)")
            except Report.DoesNotExist:
                logger.warning(f"Report {job_id} no longer exists - treating as cancellation")
                raise KeyboardInterrupt("Report record no longer exists")
            except Exception as e:
                logger.warning(f"Failed to check cancellation status: {e}")
                # Don't raise here - just continue

    # Set up signal handlers for graceful termination
    signal.signal(signal.SIGTERM, graceful_termination_handler)
    signal.signal(signal.SIGINT, graceful_termination_handler)

    try:
        logger.info(f"Starting robust report generation task for report {report_id}")

        # Get job_id from report
        try:
            report = Report.objects.get(id=report_id)
            job_id = report.job_id
        except Report.DoesNotExist:
            logger.error(f"Report {report_id} not found")
            raise Exception(f"Report {report_id} not found")

        # Check if job was cancelled before we start
        if report.status == Report.STATUS_CANCELLED:
            logger.info(f"Report {report_id} was cancelled before processing started")
            return {"status": "cancelled", "message": "Report was cancelled"}

        # Set up progress handler
        progress_handler = ReportProgressLogHandler(job_id, report_orchestrator)
        root_logger = logging.getLogger()
        root_logger.addHandler(progress_handler)

        try:
            # Update job status to running
            report_orchestrator.update_job_progress(
                job_id, "Starting report generation", Report.STATUS_RUNNING
            )

            # Check for cancellation before starting
            check_cancellation()

            # Generate the report with periodic cancellation checks
            start_ts = time.time()

            # Set up a cancellation-aware wrapper around the report generation
            logger.info(f"Starting report generation for job {job_id}")
            result = report_orchestrator.generate_report(report_id)

            # Check for cancellation after generation (in case it was a long-running operation)
            check_cancellation()

            if result.get('success', False):
                # Update job with success
                report_orchestrator.update_job_result(job_id, result, Report.STATUS_COMPLETED)
                elapsed = time.time() - start_ts
                success_msg = (
                    f"Task reports.tasks.process_report_generation[{self.request.id}] succeeded in {elapsed:.1f}s"
                )
                report_orchestrator.update_job_progress(job_id, success_msg)
                logger.info(f"Successfully completed report generation for report {report_id}")
                return result
            else:
                # Handle generation failure
                error_msg = result.get('error_message', 'Report generation failed')
                report_orchestrator.update_job_error(job_id, error_msg)
                raise Exception(error_msg)

        finally:
            # Always clean up progress handler
            if progress_handler and root_logger:
                try:
                    root_logger.removeHandler(progress_handler)
                except Exception as e:
                    logger.warning(f"Failed to remove progress handler: {e}")

    except KeyboardInterrupt as e:
        logger.info(f"Task {self.request.id} was cancelled: {e}")
        # Don't update status here - it was already updated by the signal handler or DELETE operation
        # Just exit cleanly
        return {"status": "cancelled", "message": str(e)}

    except Exception as e:
        logger.error(f"Error processing report generation for report {report_id}: {e}")

        # Update job with error (only if not already cancelled)
        if job_id:
            try:
                report = Report.objects.get(id=report_id)
                if report.status != Report.STATUS_CANCELLED:
                    report_orchestrator.update_job_error(job_id, str(e))
            except Report.DoesNotExist:
                logger.error(f"Could not update error for report {report_id} - report not found")
            except Exception as update_error:
                logger.error(f"Failed to update job error: {update_error}")

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


# Removed: cancel_report_generation task - now handled synchronously by JobService.delete_job()
# This eliminates the dual cancellation mechanisms and unreliable async cancellation


@shared_task(bind=True)
def delete_report_and_cleanup(self, report_id: int):
    """Delete a report and perform all associated cleanup operations."""
    try:
        logger.info(f"Deleting report {report_id} and performing cleanup")

        from .models import Report
        report = Report.objects.get(id=report_id)
        job_id = report.job_id

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
        return {"status": "deleted", "report_id": report_id, "job_id": job_id}

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


# ---------------------------------------------------------------------------
# Progress-bar support – custom log handler
# ---------------------------------------------------------------------------


class ReportProgressLogHandler(logging.Handler):
    """Intercept specific Celery worker INFO messages and push them to the
    report orchestrator so that the frontend progress-bar can update in real
    time. We only care about five well-defined stages of report generation.
    
    Additionally, forward all ERROR messages to the orchestrator so they can be
    displayed in the SSE progress bar. Only MainProcess ERROR messages will cause
    task failure, while other ERROR messages are displayed without stopping the task.

    The handler is lightweight and attaches only for the lifetime of the
    `process_report_generation` task – see usage below.
    """

    # Pre-compile regexes once; keep order to map to user-visible stages
    _PATTERNS = [
        re.compile(r"run_knowledge_curation_module executed", re.IGNORECASE),
        re.compile(r"run_outline_generation_module executed", re.IGNORECASE),
        re.compile(r"run_article_generation_module executed", re.IGNORECASE),
        re.compile(r"run_article_polishing_module executed", re.IGNORECASE),
        re.compile(r"Task reports\.tasks\.process_report_generation\[.*?\] succeeded", re.IGNORECASE),
    ]

    def __init__(self, job_id: str, orchestrator):
        super().__init__(level=logging.INFO)  # Monitor both INFO and ERROR levels
        self.job_id = job_id
        self.orchestrator = orchestrator

    def emit(self, record: logging.LogRecord):
        try:
            msg = record.getMessage()
            
            # Handle ERROR messages - forward all ERROR messages to orchestrator
            # The orchestrator will decide whether to fail the task (MainProcess) or just display (others)
            if record.levelno == logging.ERROR:
                try:
                    self.orchestrator.update_job_progress(self.job_id, msg)
                except Exception as e:  # pragma: no cover – never crash handler
                    logging.getLogger(__name__).warning(
                        f"Failed to process error message for {self.job_id}: {e}"
                    )
                return
            
            # Handle INFO messages that match our progress patterns
            if record.levelno == logging.INFO:
                for pattern in self._PATTERNS:
                    if pattern.search(msg):
                        # Push raw log line to progress – keeps message identical to log
                        try:
                            self.orchestrator.update_job_progress(self.job_id, msg)
                        except Exception as e:  # pragma: no cover – never crash handler
                            logging.getLogger(__name__).warning(
                                f"Failed to update progress for {self.job_id}: {e}"
                            )
                        break  # Stop after first match
        except Exception:
            # Never raise from a logging handler – swallow any errors gracefully
            pass
