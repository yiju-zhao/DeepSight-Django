"""
Notebooks App URL Configuration (canonical).

Exposes notebook endpoints under `/api/v1/` via the project router inclusion.
This module wires DRF routers and extra endpoints directly to avoid nested
`api/` subpackages.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

# Import ViewSets from notebooks.views package
from .views import (
    BatchJobViewSet,
    FileStatusSSEView,
    FileViewSet,
    KnowledgeBaseViewSet,
    NotebookJobsSSEView,
    NotebookViewSet,
    SessionChatViewSet,
)

# App namespace
app_name = "notebooks"

# Routers
router = DefaultRouter()
router.register(r"notebooks", NotebookViewSet, basename="notebook")

notebooks_router = routers.NestedDefaultRouter(router, r"notebooks", lookup="notebook")
notebooks_router.register(r"files", FileViewSet, basename="notebook-files")
notebooks_router.register(
    r"chat/sessions", SessionChatViewSet, basename="notebook-chat-sessions"
)
notebooks_router.register(
    r"knowledge", KnowledgeBaseViewSet, basename="notebook-knowledge"
)
notebooks_router.register(r"batches", BatchJobViewSet, basename="notebook-batches")

urlpatterns = [
    # Main router URLs - /api/v1/notebooks/
    path("", include(router.urls)),
    # Nested URLs - /api/v1/notebooks/{id}/...
    path("", include(notebooks_router.urls)),
    # SSE endpoints
    path(
        "notebooks/<uuid:notebook_id>/files/<str:file_id>/status/stream/",
        FileStatusSSEView.as_view(),
        name="file-status-stream",
    ),
    path(
        "notebooks/<uuid:notebook_id>/jobs/stream/",
        NotebookJobsSSEView.as_view(),
        name="notebook-jobs-stream",
    ),
]
