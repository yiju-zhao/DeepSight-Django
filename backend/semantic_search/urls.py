"""
URL configuration for semantic_search app.

Defines routes for semantic search operations.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SemanticSearchViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r"publications", SemanticSearchViewSet, basename="publications")

# URL patterns
urlpatterns = [
    path("", include(router.urls)),
]
