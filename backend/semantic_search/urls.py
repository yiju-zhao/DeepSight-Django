"""
URL configuration for semantic_search app.

Defines routes for semantic search operations.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SemanticSearchStreamView, SemanticSearchViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r"publications", SemanticSearchViewSet, basename="publications")

# URL patterns
urlpatterns = [
    # SSE streaming endpoint (must come before router to avoid conflicts)
    path("publications/stream/<str:job_id>/", SemanticSearchStreamView.as_view(), name="semantic-search-stream"),
    # ViewSet routes
    path("", include(router.urls)),
]
