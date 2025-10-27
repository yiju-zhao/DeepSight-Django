"""
Podcast App URL Configuration.

Canonical, notebook-agnostic endpoints for podcast generation and management.

URL Structure (report-style):
- /api/v1/podcasts/                      - Podcasts (list/create; filter with ?notebook=)
- /api/v1/podcasts/{podcast_id}/...      - Detail/cancel/audio/download/stream
"""

from django.urls import path

from . import views

# App namespace
app_name = "podcast"

urlpatterns = [
    # ========================================
    # New canonical endpoints (report-style, no 'jobs' in path)
    # ========================================
    path("", views.PodcastListCreateView.as_view(), name="podcast-list-create"),
    path(
        "<uuid:podcast_id>/", views.PodcastDetailView.as_view(), name="podcast-detail"
    ),
    path(
        "<uuid:podcast_id>/cancel/",
        views.PodcastCancelView.as_view(),
        name="podcast-cancel",
    ),
    path(
        "<uuid:podcast_id>/audio/",
        views.PodcastAudioRedirectView.as_view(),
        name="podcast-audio",
    ),
    path(
        "<uuid:podcast_id>/files/",
        views.PodcastFilesView.as_view(),
        name="podcast-files",
    ),
    # Stream endpoint removed: progress/SSE no longer supported
    # Note: legacy '/jobs/' endpoints removed in favor of report-style naming
]

# ========================================
# URL Pattern Documentation
# ========================================

"""
Generated URL Patterns (canonical only):

- GET  /api/v1/podcasts/?notebook={id}
- POST /api/v1/podcasts/
- GET  /api/v1/podcasts/{podcast_id}/
- DEL  /api/v1/podcasts/{podcast_id}/
- POST /api/v1/podcasts/{podcast_id}/cancel/
- GET  /api/v1/podcasts/{podcast_id}/audio/
- GET  /api/v1/podcasts/{podcast_id}/files/
  (stream endpoint removed)
"""
