"""
Canonical report job views and SSE endpoints following SOLID principles.
"""

import json
import logging
import time
import shutil
from pathlib import Path

from django.http import FileResponse, Http404, StreamingHttpResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.db import models

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Report
from .serializers import ReportGenerationRequestSerializer
from .orchestrator import report_orchestrator
from notebooks.models import Notebook
from .tasks import process_report_generation
from .services import PdfService, JobService

logger = logging.getLogger(__name__)


# ====== DEPENDENCY INVERSION PRINCIPLE (DIP) ======
# Helper class for common view operations

class ReportViewHelper:
    """Helper class containing common operations for report views"""

    @staticmethod
    def get_user_report(job_id: str, user) -> Report:
        """Get a report for a specific user with proper error handling"""
        return get_object_or_404(Report.objects.filter(user=user), job_id=job_id)

    @staticmethod
    def get_user_notebook(notebook_id: str, user) -> 'Notebook':
        """Get a notebook for a specific user with proper error handling"""
        return get_object_or_404(Notebook.objects.filter(user=user), pk=notebook_id)

    @staticmethod
    def format_report_data(report: Report) -> dict:
        """Format report data for API responses (centralized formatting)"""
        return {
            "job_id": report.job_id,
            "report_id": report.id,
            "status": report.status,
            "progress": report.progress,
            "title": report.article_title,
            "article_title": report.article_title,
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat(),
            "error": report.error_message,
            "has_files": bool(report.main_report_object_key),
            "has_content": bool(report.result_content),
        }


class ReportJobListCreateView(APIView):
    """Canonical: List and create report jobs without notebook in the path.

    - GET /api/v1/reports/jobs/?notebook=<uuid>  -> filter by notebook if provided
    - POST /api/v1/reports/jobs/ with body {..., notebook: <uuid>} -> create
    """
    permission_classes = [permissions.IsAuthenticated]

    # Use centralized helper for formatting

    def get(self, request):
        try:
            notebook_id = request.query_params.get("notebook")
            qs = Report.objects.filter(user=request.user)
            if notebook_id:
                notebook = get_object_or_404(
                    Notebook.objects.filter(user=request.user), pk=notebook_id
                )
                qs = qs.filter(notebooks=notebook)

            # Use only() to limit fields for better performance
            reports = qs.only(
                'id', 'job_id', 'status', 'progress', 'article_title', 'created_at',
                'updated_at', 'error_message', 'main_report_object_key', 'result_content'
            ).order_by('-created_at')

            # Use database aggregation instead of Python max() for better performance
            last_modified = qs.aggregate(max_updated=models.Max('updated_at'))['max_updated']

            validated_reports = []
            for report in reports:
                if report.status == Report.STATUS_COMPLETED:
                    if report.main_report_object_key or report.result_content:
                        validated_reports.append(ReportViewHelper.format_report_data(report))
                    else:
                        logger.warning(
                            f"Skipping phantom job {report.job_id} - no files found"
                        )
                else:
                    validated_reports.append(ReportViewHelper.format_report_data(report))

            response = Response({"reports": validated_reports})
            if last_modified:
                response['Last-Modified'] = last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')

            has_active_jobs = any(r.get('status') in ['pending', 'running'] for r in validated_reports)
            cache_timeout = 2 if has_active_jobs else 5
            response['Cache-Control'] = f'max-age={cache_timeout}, must-revalidate'
            return response
        except Exception as e:
            logger.error(f"Error listing reports: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            # Validate input params (plus optional notebook field)
            serializer = ReportGenerationRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            notebook_id = serializer.validated_data.get("notebook") or request.data.get("notebook")
            if not notebook_id:
                return Response(
                    {"detail": "Field 'notebook' is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            notebook = ReportViewHelper.get_user_notebook(notebook_id, request.user)

            report_data = serializer.validated_data.copy()
            report_data.pop("notebook", None)

            report = report_orchestrator.create_report_job(
                report_data, user=request.user, notebook=notebook
            )

            # Validate Celery broker connection before dispatching task
            try:
                from backend.celery import app

                # Test broker connection - this will fail if broker is down
                app.broker_connection().ensure_connection(max_retries=3, interval_start=0.1, interval_step=0.1)

                # Dispatch task using standard Celery method
                task_result = process_report_generation.delay(report.id)

                # Store the task ID for cancellation
                report.celery_task_id = task_result.id
                report.save(update_fields=["celery_task_id"])

                logger.info(f"Report generation task started with ID: {task_result.id}")

            except Exception as e:
                logger.error(f"Celery broker unavailable: {e}")
                # Clean up report if task dispatch failed
                report.delete()
                return Response(
                    {"detail": f"Report generation service unavailable: {str(e)}"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            logger.info(
                f"Report job {report.job_id} created for report {report.id} (canonical)"
            )

            return Response(
                {
                    "job_id": report.job_id,
                    "report_id": report.id,
                    "status": report.status,
                    "message": "Report generation job has been queued",
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Error creating report (canonical): {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportJobDetailView(APIView):
    """Canonical: Get or update a report job by job_id (no notebook in path)."""
    permission_classes = [permissions.IsAuthenticated]

    def _get_report(self, job_id):
        return ReportViewHelper.get_user_report(job_id, self.request.user)

    def get(self, request, job_id):
        try:
            report = self._get_report(job_id)
            job_data = report_orchestrator.get_job_status(job_id)
            if not job_data:
                return Response({"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

            response_data = {
                "job_id": job_id,
                "report_id": report.id,
                "status": report.status,
                "progress": report.progress,
                "result": job_data.get("result"),
                "error": report.error_message,
                "created_at": report.created_at.isoformat(),
                "updated_at": report.updated_at.isoformat(),
            }
            return Response(response_data)
        except Http404:
            return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting report status (canonical) for {job_id}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, job_id):
        try:
            report = self._get_report(job_id)
            if report.status != Report.STATUS_COMPLETED:
                return Response(
                    {"detail": "Only completed reports can be edited"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            content = request.data.get('content')
            if content is None:
                return Response(
                    {"detail": "Content field is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            report.result_content = content
            report.save(update_fields=['result_content', 'updated_at'])

            if report.main_report_object_key:
                try:
                    from notebooks.utils.file_storage import FileStorageService
                    storage_service = FileStorageService()
                    storage_service.save_file_content(
                        object_key=report.main_report_object_key,
                        content=content.encode('utf-8'),
                        content_type='text/markdown'
                    )
                    logger.info(f"Updated report file for job {job_id}")
                except Exception as e:
                    logger.warning(f"Could not update report file for {job_id}: {e}")

            return Response(
                {
                    "message": "Report updated successfully",
                    "job_id": job_id,
                    "report_id": report.id,
                    "updated_at": report.updated_at.isoformat(),
                }
            )
        except Http404:
            return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating report (canonical) {job_id}: {e}")
            return Response({"detail": f"Error updating report: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, job_id):
        """
        Delete/cancel a report using robust termination and cleanup.
        This is the single, authoritative endpoint for all cancellation and deletion operations.
        """
        try:
            report = self._get_report(job_id)
            job_service = JobService()

            logger.info(f"DELETE request for job {job_id} (status: {report.status})")

            # Perform robust deletion with confirmed termination
            success = job_service.delete_job(job_id)

            if success:
                message = f"Job {job_id} successfully "
                if report.status in [Report.STATUS_RUNNING, Report.STATUS_PENDING]:
                    message += "cancelled and deleted"
                else:
                    message += "deleted"

                return Response({
                    "success": True,
                    "message": message,
                    "job_id": job_id,
                    "previous_status": report.status
                }, status=status.HTTP_200_OK)
            else:
                # Deletion failed - this could be due to termination failure
                error_message = f"Failed to delete job {job_id}"
                if report.status in [Report.STATUS_RUNNING, Report.STATUS_PENDING]:
                    error_message += " - could not terminate running task"

                logger.error(f"Robust deletion failed for job {job_id}")
                return Response({
                    "success": False,
                    "message": error_message,
                    "job_id": job_id,
                    "previous_status": report.status,
                    "detail": "Task termination may have failed - check logs for details"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Http404:
            return Response(
                {"detail": "Report not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Unexpected error during report deletion {job_id}: {e}")
            return Response(
                {
                    "success": False,
                    "detail": f"Unexpected error during deletion: {str(e)}",
                    "job_id": job_id
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class ReportJobDownloadView(APIView):
    """Canonical: Download generated report files"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        try:
            report = get_object_or_404(Report.objects.filter(user=request.user), job_id=job_id)

            if report.status != Report.STATUS_COMPLETED:
                return Response({"detail": "Job is not completed yet"}, status=status.HTTP_400_BAD_REQUEST)

            filename = request.query_params.get("filename")
            if filename:
                if (report.main_report_object_key and report.file_metadata.get('main_report_filename') == filename):
                    file_url = report.get_report_url(expires=86400)
                    if file_url:
                        from django.http import HttpResponseRedirect
                        return HttpResponseRedirect(file_url)
                return Response({"detail": "File not found"}, status=status.HTTP_404_NOT_FOUND)

            if report.main_report_object_key:
                file_url = report.get_report_url(expires=86400)
                if file_url:
                    from django.http import HttpResponseRedirect
                    return HttpResponseRedirect(file_url)

            return Response({"detail": "No downloadable report files found"}, status=status.HTTP_404_NOT_FOUND)
        except Http404:
            return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error downloading report (canonical) for job {job_id}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportJobPdfDownloadView(APIView):
    """Canonical: Download generated report files as PDF"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        try:
            report = get_object_or_404(Report.objects.filter(user=request.user), job_id=job_id)
            if report.status != Report.STATUS_COMPLETED:
                return Response({"detail": "Job is not completed yet"}, status=status.HTTP_400_BAD_REQUEST)

            pdf_service = PdfService()

            markdown_content = None
            if report.result_content:
                markdown_content = report.result_content
            elif report.main_report_object_key:
                try:
                    from infrastructure.storage.adapters import get_storage_adapter
                    storage_adapter = get_storage_adapter()
                    content_bytes = storage_adapter.get_file_content(report.main_report_object_key, str(request.user.id))
                    if isinstance(content_bytes, bytes):
                        markdown_content = content_bytes.decode('utf-8')
                    else:
                        markdown_content = content_bytes
                except Exception as e:
                    logger.error(f"Error reading report file for {job_id}: {e}")

            if not markdown_content:
                return Response({"detail": "No report content found to convert to PDF"}, status=status.HTTP_404_NOT_FOUND)

            report_title = report.article_title or "Research Report"
            filename = f"{report_title.replace(' ', '_')}.pdf"

            import tempfile
            temp_dir = Path(tempfile.mkdtemp())
            pdf_path = temp_dir / filename
            try:
                logger.info("Converting markdown to PDF with automatic image handling")
                pdf_file_path = pdf_service.convert_markdown_to_pdf(
                    markdown_content=markdown_content,
                    output_path=str(pdf_path),
                    title=report_title,
                    input_file_path=None
                )
                response = FileResponse(open(pdf_file_path, "rb"), as_attachment=True, filename=filename, content_type='application/pdf')
                logger.info(f"PDF generated successfully: {pdf_file_path}")
                return response
            except Exception as e:
                logger.error(f"Error converting report to PDF for job {job_id}: {e}")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return Response({"detail": f"PDF conversion failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Http404:
            return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error downloading PDF report (canonical) for job {job_id}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportJobFilesView(APIView):
    """Canonical: List all files generated for a specific report job"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        try:
            report = get_object_or_404(Report.objects.filter(user=request.user), job_id=job_id)
            files = []
            if report.main_report_object_key:
                try:
                    metadata = report.file_metadata or {}
                    filename = metadata.get('main_report_filename', 'report.md')
                    size = metadata.get('main_report_size', 0)
                    file_type = Path(filename).suffix.lower() if filename else '.md'
                    files.append(
                        {
                            "filename": filename,
                            "size": size,
                            "type": file_type,
                            "download_url": f"/api/v1/reports/jobs/{job_id}/download?filename={filename}",
                        }
                    )
                except Exception as e:
                    logger.warning(f"Error listing files for job {job_id}: {e}")
            return Response({"files": files})
        except Http404:
            return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error listing files (canonical) for job {job_id}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportJobContentView(APIView):
    """Canonical: Get the main report content as text/markdown"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        try:
            report = get_object_or_404(Report.objects.filter(user=request.user), job_id=job_id)
            if report.status != Report.STATUS_COMPLETED:
                return Response({"detail": "Job is not completed yet"}, status=status.HTTP_400_BAD_REQUEST)

            if report.result_content:
                return Response(
                    {
                        "job_id": job_id,
                        "report_id": report.id,
                        "content": report.result_content,
                        "article_title": report.article_title,
                        "generated_files": report.generated_files,
                    }
                )

            if report.main_report_object_key:
                try:
                    from infrastructure.storage.adapters import get_storage_adapter
                    storage_adapter = get_storage_adapter()
                    content_bytes = storage_adapter.get_file_content(report.main_report_object_key, str(request.user.id))
                    if isinstance(content_bytes, bytes):
                        content = content_bytes.decode('utf-8')
                    else:
                        content = content_bytes
                    return Response(
                        {
                            "job_id": job_id,
                            "report_id": report.id,
                            "content": content,
                            "article_title": report.article_title,
                            "generated_files": report.generated_files,
                        }
                    )
                except Exception as e:
                    logger.error(f"Error reading report file for {job_id}: {e}")

            return Response({"detail": "Report content not found"}, status=status.HTTP_404_NOT_FOUND)
        except Http404:
            return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting report content (canonical) for job {job_id}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportModelsView(APIView):
    """Get available models and configuration options"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get available models and configuration options"""
        try:
            return Response(
                {
                    "model_providers": [
                        choice[0] for choice in Report.MODEL_PROVIDER_CHOICES
                    ],
                    "retrievers": [choice[0] for choice in Report.RETRIEVER_CHOICES],
                    "time_ranges": [choice[0] for choice in Report.TIME_RANGE_CHOICES],
                    "prompt_types": [
                        choice[0] for choice in Report.PROMPT_TYPE_CHOICES
                    ],
                    "search_depths": [
                        choice[0] for choice in Report.SEARCH_DEPTH_CHOICES
                    ],
                }
            )
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ---------------------------------------------------------------------------
# SSE endpoint (plain Django view) – avoids DRF content-negotiation 406 errors
# ---------------------------------------------------------------------------



def report_status_stream(request, job_id):
    """Canonical SSE endpoint: real-time report-job status updates by job_id."""

    if request.method == "OPTIONS":
        response = HttpResponse(status=200)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Cache-Control, Authorization"
        response["Access-Control-Allow-Credentials"] = "true"
        return response

    if not request.user.is_authenticated:
        response = StreamingHttpResponse(
            f"data: {json.dumps({'type': 'error', 'message': 'Authentication required'})}\n\n",
            content_type="text/event-stream",
            status=401,
        )
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Credentials"] = "true"
        return response

    try:
        if not Report.objects.filter(job_id=job_id, user=request.user).exists():
            response = StreamingHttpResponse(
                f"data: {json.dumps({'type': 'error', 'message': 'Report not found'})}\n\n",
                content_type="text/event-stream",
                status=404,
            )
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Credentials"] = "true"
            return response

        def event_stream():
            last_status = None
            max_duration = 3600
            start_time = time.time()
            poll_interval = 2

            while time.time() - start_time < max_duration:
                try:
                    status_data = report_orchestrator.get_job_status(job_id)
                    if not status_data:
                        # Use only() to limit database fields for better performance
                        current_report = Report.objects.filter(job_id=job_id).only(
                            'id', 'job_id', 'status', 'progress', 'error_message', 'updated_at'
                        ).first()
                        if not current_report:
                            yield f"data: {json.dumps({'type': 'error', 'message': 'Report not found'})}\n\n"
                            break
                        status_data = {
                            "job_id": job_id,
                            "report_id": str(current_report.id),
                            "status": current_report.status,
                            "progress": current_report.progress,
                            "error_message": current_report.error_message,
                            "result": None,
                            "updated_at": current_report.updated_at.isoformat(),
                        }

                    current_status_str = json.dumps(status_data, sort_keys=True)
                    if current_status_str != last_status:
                        yield f"data: {json.dumps({'type': 'job_status', 'data': status_data})}\n\n"
                        last_status = current_status_str

                    if status_data.get("status") in ["completed", "failed", "cancelled"]:
                        break

                    time.sleep(poll_interval)

                except Exception as e:
                    logger.error(f"Error in SSE stream for job {job_id}: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                    break

            yield f"data: {json.dumps({'type': 'stream_closed'})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Cache-Control"
        response["Access-Control-Allow-Credentials"] = "true"
        return response
    except Exception as e:
        logger.error(f"Error setting up SSE stream (canonical) for job {job_id}: {e}")
        response = StreamingHttpResponse(
            f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n",
            content_type="text/event-stream",
        )
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Credentials"] = "true"
        return response
