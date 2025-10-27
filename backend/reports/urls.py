"""
Reports App URL Configuration.

Canonical, notebook-agnostic endpoints for report generation and management.

URL Structure:
- /api/v1/reports/models/              - Global report configuration
- /api/v1/reports/                     - Report list/create (filter with ?notebook=)
- /api/v1/reports/{report_id}/...      - Report operations (detail/cancel/files/content/download/stream)
"""

from django.urls import path

from . import views

# App namespace
app_name = "reports"

urlpatterns = [
    # ========================================
    # Global Report Configuration
    # ========================================
    # Report models and configuration (not notebook-specific)
    path("models/", views.ReportModelsView.as_view(), name="report-models"),
    # Get available Xinference models
    path(
        "xinference/models/",
        views.XinferenceModelsView.as_view(),
        name="xinference-models",
    ),
    # ========================================
    # Canonical Report Endpoints (no notebook in path)
    # ========================================
    # List and create reports
    path("", views.ReportJobListCreateView.as_view(), name="report-list-create"),
    # Individual report operations
    path("<str:report_id>/", views.ReportJobDetailView.as_view(), name="report-detail"),
    path(
        "<str:report_id>/download/",
        views.ReportJobDownloadView.as_view(),
        name="report-download",
    ),
    path(
        "<str:report_id>/download-pdf/",
        views.ReportJobPdfDownloadView.as_view(),
        name="report-pdf-download",
    ),
    path(
        "<str:report_id>/files/",
        views.ReportJobFilesView.as_view(),
        name="report-files",
    ),
    path(
        "<str:report_id>/content/",
        views.ReportJobContentView.as_view(),
        name="report-content",
    ),
    path(
        "<str:report_id>/cancel/",
        views.ReportJobCancelView.as_view(),
        name="report-cancel",
    ),
    path(
        "<str:report_id>/image/<str:image_id>/inline/",
        views.ReportJobImageInlineView.as_view(),
        name="report-image-inline",
    ),
    # Stream endpoint removed: progress/SSE no longer supported
]

# ========================================
# URL Pattern Documentation
# ========================================

"""
Generated URL Patterns:

Configuration:
- GET  /api/v1/reports/models/
- GET  /api/v1/reports/xinference/models/

Report Operations:
- GET  /api/v1/reports/?notebook={id}
- POST /api/v1/reports/
- GET  /api/v1/reports/{report_id}/
- PUT  /api/v1/reports/{report_id}/
- DEL  /api/v1/reports/{report_id}/
- GET  /api/v1/reports/{report_id}/files/
- GET  /api/v1/reports/{report_id}/content/
- POST /api/v1/reports/{report_id}/cancel/
- GET  /api/v1/reports/{report_id}/download/
- GET  /api/v1/reports/{report_id}/download-pdf/
- GET  /api/v1/reports/{report_id}/image/{image_id}/inline/
  (stream endpoint removed)

Note: Report images are stored as relative paths (images/filename.jpg) in the database.
      The backend replaces them with API proxy URLs when serving content.
"""
