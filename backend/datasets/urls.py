"""
URL configuration for datasets app.

Defines routes for semantic search and other dataset operations.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SemanticSearchViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r"semantic-search", SemanticSearchViewSet, basename="semantic-search")

# URL patterns
urlpatterns = [
    path("", include(router.urls)),
]
