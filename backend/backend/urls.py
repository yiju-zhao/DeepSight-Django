"""
URL configuration for backend project.

Clean app-specific URL structure following Django best practices:
- Each app manages its own URLs
- Clear separation of concerns
- Better maintainability and testing

API Structure:
- /api/v1/users/ -> User management
- /api/v1/notebooks/ -> Notebook operations and file management
- /api/v1/podcasts/ -> Podcast generation and management
- /api/v1/reports/ -> Report generation and management
- /api/v1/conferences/ -> Conference data and analytics
"""

from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # ========================================
    # Admin Interface
    # ========================================
    path("admin/", admin.site.urls),
    # ========================================
    # API v1 Endpoints (App-Specific)
    # ========================================
    # User management
    path("api/v1/users/", include("users.urls")),
    # Notebook operations (core functionality)
    path("api/v1/", include("notebooks.urls")),  # Handles notebooks/* patterns
    # Podcast generation and management
    path("api/v1/podcasts/", include("podcast.urls")),
    # Report generation and management
    path("api/v1/reports/", include("reports.urls")),
    # Conference data and analytics
    path("api/v1/conferences/", include("conferences.urls")),
    # ========================================
    # API Documentation
    # ========================================
    # OpenAPI schema and documentation (drf-spectacular)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

# ========================================
# URL Pattern Documentation
# ========================================

"""
Complete API Structure:

User Management:
- /api/v1/users/* -> User authentication, profiles, etc.

Notebooks (Core):
- /api/v1/notebooks/ -> CRUD operations, file management, knowledge base
- /api/v1/notebooks/{id}/files/ -> File upload, processing, content access
- /api/v1/notebooks/{id}/chat/ -> Chat sessions and messaging

Podcasts:
- /api/v1/podcasts/ -> Podcasts (list/create; filter with ?notebook=)
- /api/v1/podcasts/{podcast_id}/ -> Detail/delete
- /api/v1/podcasts/{podcast_id}/cancel/ -> Cancel generation
- /api/v1/podcasts/{podcast_id}/audio/ -> Unified audio gateway (302 to fresh presigned URL; supports ?download=1)

Reports:
- /api/v1/reports/models/ -> Report configuration
- /api/v1/reports/ -> Report jobs (list/create; filter with ?notebook=)
- /api/v1/reports/{report_id}/ -> Job detail/cancel/files/content/download/stream

Conferences:
- /api/v1/conferences/venues/ -> Venue CRUD operations
- /api/v1/conferences/instances/ -> Conference instances (filter with ?venue=)
- /api/v1/conferences/publications/ -> Publications (filter with ?instance=)
- /api/v1/conferences/events/ -> Conference events (filter with ?instance=)
- /api/v1/conferences/dashboard/dashboard/ -> Dashboard analytics
- /api/v1/conferences/dashboard/overview/ -> Conferences overview

Documentation:
- /api/schema/ -> Raw OpenAPI schema (JSON)
- /api/schema/swagger-ui/ -> Interactive API explorer
- /api/schema/redoc/ -> Alternative documentation format
"""
