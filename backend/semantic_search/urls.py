"""
URL configuration for semantic_search app.

Defines routes for streaming semantic search operations.
"""

from django.urls import path

from .views import (
    BulkPublicationFetchView,
    InitiateStreamingSearchView,
    SemanticSearchStreamView,
)

urlpatterns = [
    # Streaming endpoints
    path(
        "publications/stream/",
        InitiateStreamingSearchView.as_view(),
        name="initiate-search-stream",
    ),
    path(
        "publications/stream/<str:job_id>/",
        SemanticSearchStreamView.as_view(),
        name="semantic-search-stream",
    ),
    # Bulk fetch endpoint
    path(
        "publications/bulk/",
        BulkPublicationFetchView.as_view(),
        name="bulk-publication-fetch",
    ),
]
