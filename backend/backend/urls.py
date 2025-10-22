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
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Create the schema view for API documentation
schema_view = get_schema_view(
    openapi.Info(
        title="DeepSight API",
        default_version="v1",
        description="Interactive documentation for DeepSight backend with clean app-specific endpoints",
        contact=openapi.Contact(email="you@yourdomain.com"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
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
    
    # Swagger UI (interactive API explorer)
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    
    # ReDoc UI (alternative documentation format)
    path(
        "redoc/", 
        schema_view.with_ui("redoc", cache_timeout=0), 
        name="schema-redoc"
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
- /swagger/ -> Interactive API explorer
- /redoc/ -> Alternative documentation format
"""
