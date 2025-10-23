"""
Canonical report job views (SSE removed) following SOLID principles.
"""

import json
import logging
import time
import shutil
from pathlib import Path

from django.http import FileResponse, Http404, HttpResponse
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
    def get_user_report(report_id: str, user) -> Report:
        """Get a report for a specific user with proper error handling"""
        return get_object_or_404(Report.objects.filter(user=user), id=report_id)

    @staticmethod
    def get_user_notebook(notebook_id: str, user) -> 'Notebook':
        """Get a notebook for a specific user with proper error handling"""
        return get_object_or_404(Notebook.objects.filter(user=user), pk=notebook_id)

    @staticmethod
    def format_report_data(report: Report) -> dict:
        """Format report data for API responses (centralized formatting)"""
        return {
            "report_id": str(report.id),
            "status": report.status,
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
            # Exclude cancelled reports from the list (keep failed reports visible)
            qs = Report.objects.filter(user=request.user).exclude(status=Report.STATUS_CANCELLED)
            if notebook_id:
                notebook = get_object_or_404(
                    Notebook.objects.filter(user=request.user), pk=notebook_id
                )
                qs = qs.filter(notebooks=notebook)

            # Use only() to limit fields for better performance
            reports = qs.only(
                'id', 'status', 'article_title', 'created_at',
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
                            f"Skipping phantom report {report.id} - no files found"
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

            task_result = process_report_generation.delay(report.id)
            report.celery_task_id = task_result.id
            report.save(update_fields=["celery_task_id"])

            logger.info(
                f"Report {report.id} created (canonical)"
            )

            return Response(
                {
                    "report_id": str(report.id),
                    "status": report.status,
                    "message": "Report generation job has been queued",
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Error creating report (canonical): {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportJobDetailView(APIView):
    """Canonical: Get or update a report job by report_id (no notebook in path)."""
    permission_classes = [permissions.IsAuthenticated]

    def _get_report(self, report_id):
        return ReportViewHelper.get_user_report(report_id, self.request.user)

    def get(self, request, report_id):
        try:
            report = self._get_report(report_id)
            job_data = report_orchestrator.get_job_status(report_id)
            if not job_data:
                return Response({"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

            response_data = {
                "report_id": str(report.id),
                "status": report.status,
                "result": job_data.get("result"),
                "error": report.error_message,
                "created_at": report.created_at.isoformat(),
                "updated_at": report.updated_at.isoformat(),
            }
            return Response(response_data)
        except Http404:
            return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting report status (canonical) for report {report_id}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, report_id):
        try:
            report = self._get_report(report_id)
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
                    logger.info(f"Updated report file for report {report_id}")
                except Exception as e:
                    logger.warning(f"Could not update report file for report {report_id}: {e}")

            return Response(
                {
                    "message": "Report updated successfully",
                    "report_id": str(report.id),
                    "updated_at": report.updated_at.isoformat(),
                }
            )
        except Http404:
            return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating report (canonical) report {report_id}: {e}")
            return Response({"detail": f"Error updating report: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, report_id):
        """
        Delete a completed, failed, or cancelled report job.
        For cancelling running jobs, use POST /jobs/{report_id}/cancel/ instead.
        """
        try:
            report = self._get_report(report_id)
            job_service = JobService()

            logger.info(f"DELETE request for report {report_id} (status: {report.status})")

            # Check if job is in a deletable state (not running or pending)
            if report.status in [Report.STATUS_RUNNING, Report.STATUS_PENDING]:
                return Response({
                    "detail": f"Cannot delete job in '{report.status}' status. Use POST /jobs/{report_id}/cancel/ to cancel running jobs first.",
                    "current_status": report.status
                }, status=status.HTTP_400_BAD_REQUEST)

            # Only delete completed, failed, or cancelled jobs
            success = job_service.delete_job(report_id)

            if success:
                return Response({
                    "success": True,
                    "message": f"Job report {report_id} successfully deleted",
                    "report_id": report_id,
                    "previous_status": report.status
                }, status=status.HTTP_200_OK)
            else:
                error_message = f"Failed to delete job report {report_id}"
                logger.error(f"Deletion failed for report {report_id}")
                return Response({
                    "success": False,
                    "message": error_message,
                    "report_id": report_id,
                    "previous_status": report.status,
                    "detail": "Job deletion failed - check logs for details"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Http404:
            return Response(
                {"detail": "Report not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Unexpected error during report deletion report {report_id}: {e}")
            return Response(
                {
                    "success": False,
                    "detail": f"Unexpected error during deletion: {str(e)}",
                    "report_id": report_id
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class ReportJobDownloadView(APIView):
    """Canonical: Download generated report files"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, report_id):
        try:
            report = get_object_or_404(Report.objects.filter(user=request.user), id=report_id)

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
            logger.error(f"Error downloading report (canonical) for report {report_id}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportJobPdfDownloadView(APIView):
    """Canonical: Download generated report files as PDF"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, report_id):
        try:
            report = get_object_or_404(Report.objects.filter(user=request.user), id=report_id)
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
                    logger.error(f"Error reading report file for report {report_id}: {e}")

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
                logger.error(f"Error converting report to PDF for report {report_id}: {e}")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return Response({"detail": f"PDF conversion failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Http404:
            return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error downloading PDF report (canonical) for report {report_id}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportJobFilesView(APIView):
    """Canonical: List all files generated for a specific report job"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, report_id):
        try:
            report = get_object_or_404(Report.objects.filter(user=request.user), id=report_id)
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
                            "download_url": f"/api/v1/reports/jobs/{report_id}/download?filename={filename}",
                        }
                    )
                except Exception as e:
                    logger.warning(f"Error listing files for report {report_id}: {e}")
            return Response({"files": files})
        except Http404:
            return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error listing files (canonical) for report {report_id}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportJobContentView(APIView):
    """Canonical: Get the main report content as text/markdown"""
    permission_classes = [permissions.IsAuthenticated]

    def _replace_image_paths_with_urls(self, content: str, report: Report) -> str:
        """Replace relative image paths with backend API proxy URLs (exactly like KB items do)"""
        import re
        import os
        from urllib.parse import urlparse
        from reports.models import ReportImage

        # Quick exit if no obvious image tokens
        if not content or ('![' not in content and '<img' not in content):
            return content

        # Get all images for this report
        images = ReportImage.objects.filter(report=report).only(
            'id', 'report_figure_minio_object_key', 'image_metadata'
        )

        # Build mapping from original paths and basenames to API proxy URLs
        path_to_url = {}
        basename_to_url = {}

        for img in images:
            # Use backend API proxy URL (like KB items do)
            url = f"/api/v1/reports/{report.id}/image/{img.id}/inline/"

            # Get original file info from metadata (like KB items)
            original_file = None
            original_filename = None
            if isinstance(img.image_metadata, dict):
                original_file = img.image_metadata.get('original_file')
                original_filename = img.image_metadata.get('original_filename')

            # Prefer full relative path match
            if original_file:
                # Normalize to use forward slashes
                norm = original_file.replace('\\', '/')
                path_to_url[norm] = url
                # Also map basename
                basename_to_url[os.path.basename(norm)] = url

            if original_filename:
                basename_to_url[original_filename] = url

            # Fallback: also map MinIO object key filename
            if img.report_figure_minio_object_key:
                filename = img.report_figure_minio_object_key.split('/')[-1]
                basename_to_url[filename] = url

        if not path_to_url and not basename_to_url:
            return content

        # Helper to decide if url is local/relative
        def is_local_path(p: str) -> bool:
            parsed = urlparse(p)
            if parsed.scheme or parsed.netloc:
                return False
            # data URIs or anchors should be left alone
            if p.startswith('data:') or p.startswith('#'):
                return False
            return True

        # Replace in markdown image syntax: ![alt](url)
        md_img_pattern = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+['\"][^)]+['\"])?\)")

        def md_repl(match: re.Match) -> str:
            orig_url = match.group(1)
            if not is_local_path(orig_url):
                return match.group(0)
            norm = orig_url.replace('\\', '/')
            new_url = path_to_url.get(norm)
            if not new_url:
                new_url = basename_to_url.get(os.path.basename(norm))
            if not new_url:
                return match.group(0)
            return match.group(0).replace(orig_url, new_url)

        content = md_img_pattern.sub(md_repl, content)

        # Replace in HTML <img src="...">
        html_img_pattern = re.compile(r"<img([^>]*?)src=[\"\']([^\"\']+)[\"\']([^>]*)>")

        def html_repl(match: re.Match) -> str:
            pre, src, post = match.groups()
            if not is_local_path(src):
                return match.group(0)
            norm = src.replace('\\', '/')
            new_url = path_to_url.get(norm)
            if not new_url:
                new_url = basename_to_url.get(os.path.basename(norm))
            if not new_url:
                return match.group(0)
            return f'<img{pre}src="{new_url}"{post}>'

        content = html_img_pattern.sub(html_repl, content)

        return content

    def get(self, request, report_id):
        try:
            report = get_object_or_404(Report.objects.filter(user=request.user), id=report_id)
            if report.status != Report.STATUS_COMPLETED:
                return Response({"detail": "Job is not completed yet"}, status=status.HTTP_400_BAD_REQUEST)

            content = None

            if report.result_content:
                content = report.result_content
            elif report.main_report_object_key:
                try:
                    from infrastructure.storage.adapters import get_storage_adapter
                    storage_adapter = get_storage_adapter()
                    content_bytes = storage_adapter.get_file_content(report.main_report_object_key, str(request.user.id))
                    if isinstance(content_bytes, bytes):
                        content = content_bytes.decode('utf-8')
                    else:
                        content = content_bytes
                except Exception as e:
                    logger.error(f"Error reading report file for report {report_id}: {e}")

            if content:
                # Replace relative image paths with MinIO URLs (like KB items do)
                content = self._replace_image_paths_with_urls(content, report)

                return Response(
                    {
                        "report_id": str(report.id),
                        "content": content,
                        "article_title": report.article_title,
                        "generated_files": report.generated_files,
                    }
                )

            return Response({"detail": "Report content not found"}, status=status.HTTP_404_NOT_FOUND)
        except Http404:
            return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting report content (canonical) for report {report_id}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportJobImageInlineView(APIView):
    """Serve a report image via API as an inline response (MinIO proxy)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, report_id, image_id):
        """Serve an image inline (similar to KB items)."""
        try:
            from reports.models import ReportImage
            from infrastructure.storage.adapters import get_storage_backend
            from django.utils.http import http_date
            import hashlib

            # Get the report and verify ownership
            report = get_object_or_404(Report.objects.filter(user=request.user), id=report_id)

            # Get the image and verify it belongs to this report
            image = get_object_or_404(ReportImage, id=image_id, report=report)

            # Compute ETag from storage metadata or fallback to a hash of identifiers
            storage = get_storage_backend()
            etag_value = None
            try:
                meta = storage.get_file_metadata(image.report_figure_minio_object_key)
                if meta and isinstance(meta, dict):
                    etag_value = meta.get('etag')
            except Exception:
                etag_value = None

            if not etag_value:
                base = f"{image.id}-{getattr(image, 'updated_at', None) or getattr(image, 'created_at', None)}"
                etag_value = hashlib.sha1(base.encode('utf-8')).hexdigest()

            # Normalize ETag header value (quoted strong ETag)
            etag_header = etag_value if etag_value.startswith('W/"') or etag_value.startswith('"') else f'"{etag_value}"'

            # Handle If-None-Match for conditional GET
            inm = request.headers.get('If-None-Match') or request.META.get('HTTP_IF_NONE_MATCH')
            if inm:
                # Normalize comparison by stripping quotes and weak validators
                def norm(v: str) -> str:
                    return v.strip().lstrip('W/').strip('"')
                if norm(inm) == norm(etag_header):
                    resp = HttpResponse(status=304)
                    resp["ETag"] = etag_header
                    resp["Cache-Control"] = "private, max-age=300"
                    dt = getattr(image, 'updated_at', None) or getattr(image, 'created_at', None)
                    if dt:
                        try:
                            resp["Last-Modified"] = http_date(dt.timestamp())
                        except Exception:
                            pass
                    return resp

            # Get image content from MinIO
            content = image.get_image_content()
            if content is None:
                return Response({"detail": "Image not found"}, status=status.HTTP_404_NOT_FOUND)

            # Build response
            resp = HttpResponse(content, content_type=image.content_type or 'application/octet-stream')

            # Set filename from metadata if available
            filename = 'image'
            if image.image_metadata and isinstance(image.image_metadata, dict):
                filename = image.image_metadata.get('original_filename', 'image')

            resp["Content-Disposition"] = f"inline; filename=\"{filename}\""
            resp["X-Content-Type-Options"] = "nosniff"

            # Add short-lived caching to reduce repeated loads
            resp["Cache-Control"] = "private, max-age=300"

            # Use updated_at or created_at for Last-Modified
            dt = getattr(image, 'updated_at', None) or getattr(image, 'created_at', None)
            if dt:
                try:
                    resp["Last-Modified"] = http_date(dt.timestamp())
                except Exception:
                    pass

            resp["ETag"] = etag_header
            return resp

        except Exception as e:
            logger.exception(f"Failed to serve inline image {image_id} for report {report_id}: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReportJobCancelView(APIView):
    """Canonical: Cancel a running or pending report job"""
    permission_classes = [permissions.IsAuthenticated]

    def _get_report(self, report_id):
        return ReportViewHelper.get_user_report(report_id, self.request.user)

    def post(self, request, report_id):
        """Cancel a running or pending report job immediately with SIGKILL"""
        try:
            report = self._get_report(report_id)

            # Check if job is in a cancellable state
            if report.status not in [Report.STATUS_PENDING, Report.STATUS_RUNNING]:
                return Response(
                    {"detail": f"Job cannot be cancelled. Current status: {report.status}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"Cancelling report {report_id} (status: {report.status}, celery_task_id: {report.celery_task_id})")

            # Step 1: Immediately revoke Celery task with SIGKILL for non-ignorable termination
            if report.celery_task_id:
                try:
                    from backend.celery import app as celery_app

                    # Use SIGKILL for immediate, non-ignorable termination
                    celery_app.control.revoke(
                        report.celery_task_id,
                        terminate=True,
                        signal='SIGKILL'
                    )
                    logger.info(f"Sent SIGKILL to Celery task {report.celery_task_id} for immediate termination")

                except Exception as e:
                    logger.error(f"Failed to revoke Celery task {report.celery_task_id}: {e}")

            # Step 2: Update Report status to CANCELLED
            report.status = Report.STATUS_CANCELLED
            report.save(update_fields=['status', 'updated_at'])

            # Log cancellation with details
            logger.info(
                f"✓ Report generation cancelled successfully:\n"
                f"  - Report ID: {report_id}\n"
                f"  - Celery Task ID: {report.celery_task_id}\n"
                f"  - Status: {Report.STATUS_CANCELLED}\n"
                f"  - User: {request.user.username}"
            )

            return Response({
                "report_id": report_id,
                "status": Report.STATUS_CANCELLED,
                "message": "Job has been cancelled successfully"
            }, status=status.HTTP_200_OK)

        except Report.DoesNotExist:
            return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error cancelling job report {report_id}: {e}", exc_info=True)
            return Response({"detail": f"Error cancelling job: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReportModelsView(APIView):
    """Get available models and configuration options"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get available models and configuration options"""
        try:
            # Get static model providers
            model_providers = [choice[0] for choice in Report.MODEL_PROVIDER_CHOICES]

            return Response(
                {
                    "model_providers": model_providers,
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


class XinferenceModelsView(APIView):
    """Get available models from Xinference server"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get list of running LLM models from Xinference"""
        try:
            from .utils import get_available_xinference_models

            models = get_available_xinference_models()
            return Response({"models": models})
        except Exception as e:
            logger.error(f"Error getting Xinference models: {e}")
            return Response(
                {"detail": str(e), "models": []},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    # SSE endpoint removed: use list/detail polling instead
