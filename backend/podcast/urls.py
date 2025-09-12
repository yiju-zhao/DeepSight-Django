"""
Podcast App URL Configuration.

Canonical, notebook-agnostic endpoints for podcast generation and management.

URL Structure:
- /api/v1/podcasts/jobs/              - Podcast jobs (list/create; filter with ?notebook=)
- /api/v1/podcasts/jobs/{job_id}/...  - Job operations (detail/cancel/audio/download/stream)
"""

from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views

# App namespace
app_name = 'podcast'

urlpatterns = [
    # ========================================
    # Canonical Podcast Job Endpoints (no notebook in path)
    # ========================================
    path(
        'jobs/',
        views.PodcastJobListCreateView.as_view(),
        name='podcast-jobs'
    ),
    path(
        'jobs/<uuid:job_id>/',
        views.PodcastJobDetailView.as_view(),
        name='podcast-job-detail'
    ),
    path(
        'jobs/<uuid:job_id>/cancel/',
        views.PodcastJobCancelView.as_view(),
        name='podcast-job-cancel'
    ),
    path(
        'jobs/<uuid:job_id>/audio/',
        views.PodcastJobAudioView.as_view(),
        name='podcast-job-audio'
    ),
    path(
        'jobs/<uuid:job_id>/download/',
        views.PodcastJobDownloadView.as_view(),
        name='podcast-job-download'
    ),
    path(
        'jobs/<uuid:job_id>/stream/',
        csrf_exempt(views.podcast_job_status_stream),
        name='podcast-job-status-stream'
    ),

]

# ========================================
# URL Pattern Documentation
# ========================================

"""
Generated URL Patterns (canonical only):

- GET  /api/v1/podcasts/jobs/?notebook={id}
- POST /api/v1/podcasts/jobs/
- GET  /api/v1/podcasts/jobs/{job_id}/
- DEL  /api/v1/podcasts/jobs/{job_id}/
- POST /api/v1/podcasts/jobs/{job_id}/cancel/
- GET  /api/v1/podcasts/jobs/{job_id}/audio/
- GET  /api/v1/podcasts/jobs/{job_id}/download/
- GET  /api/v1/podcasts/jobs/{job_id}/stream/
"""
