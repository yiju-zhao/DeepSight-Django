"""
Reports App URL Configuration.

Canonical, notebook-agnostic endpoints for report generation and management.

URL Structure:
- /api/v1/reports/models/              - Global report configuration
- /api/v1/reports/jobs/                - Report jobs (list/create; filter with ?notebook=)
- /api/v1/reports/jobs/{job_id}/...    - Job operations (detail/cancel/files/content/download/stream)
"""

from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views

# App namespace
app_name = 'reports'

urlpatterns = [
    # ========================================
    # Global Report Configuration
    # ========================================
    
    # Report models and configuration (not notebook-specific)
    path(
        'models/',
        views.ReportModelsView.as_view(),
        name='report-models'
    ),

    # ========================================
    # Canonical Report Job Endpoints (no notebook in path)
    # ========================================

    path(
        'jobs/',
        views.ReportJobListCreateView.as_view(),
        name='report-jobs'
    ),
    path(
        'jobs/<str:job_id>/',
        views.ReportJobDetailView.as_view(),
        name='report-job-detail'
    ),
    path(
        'jobs/<str:job_id>/download/',
        views.ReportJobDownloadView.as_view(),
        name='report-job-download'
    ),
    path(
        'jobs/<str:job_id>/download-pdf/',
        views.ReportJobPdfDownloadView.as_view(),
        name='report-job-pdf-download'
    ),
    path(
        'jobs/<str:job_id>/files/',
        views.ReportJobFilesView.as_view(),
        name='report-job-files'
    ),
    path(
        'jobs/<str:job_id>/content/',
        views.ReportJobContentView.as_view(),
        name='report-job-content'
    ),
    path(
        'jobs/<str:job_id>/cancel/',
        views.ReportJobCancelView.as_view(),
        name='report-job-cancel'
    ),
    path(
        'jobs/<str:job_id>/stream/',
        csrf_exempt(views.report_status_stream),
        name='report-job-status-stream'
    ),

]

# ========================================
# URL Pattern Documentation
# ========================================

"""
Generated URL Patterns (canonical only):

- GET  /api/v1/reports/models/
- GET  /api/v1/reports/jobs/?notebook={id}
- POST /api/v1/reports/jobs/
- GET  /api/v1/reports/jobs/{job_id}/
- PUT  /api/v1/reports/jobs/{job_id}/
- DEL  /api/v1/reports/jobs/{job_id}/
- GET  /api/v1/reports/jobs/{job_id}/files/
- GET  /api/v1/reports/jobs/{job_id}/content/
- POST /api/v1/reports/jobs/{job_id}/cancel/
- GET  /api/v1/reports/jobs/{job_id}/download/
- GET  /api/v1/reports/jobs/{job_id}/download-pdf/
- GET  /api/v1/reports/jobs/{job_id}/stream/
"""
