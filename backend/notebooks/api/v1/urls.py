"""
URL configuration for notebooks API v1.

Provides RESTful API endpoints using Django REST Framework patterns
with proper ViewSet routing and nested resource handling.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    NotebookViewSet,
    FileViewSet,
    KnowledgeBaseViewSet,
    BatchJobViewSet
)
from .session_views import SessionChatViewSet, SessionAgentInfoView

# Main router for top-level resources
router = DefaultRouter()
router.register(r'', NotebookViewSet, basename='notebook')

# Nested routers for notebook-related resources  
notebooks_router = routers.NestedDefaultRouter(router, r'', lookup='notebook')
notebooks_router.register(r'files', FileViewSet, basename='notebook-files')
notebooks_router.register(r'chat/sessions', SessionChatViewSet, basename='notebook-chat-sessions')  # Session-based endpoints
notebooks_router.register(r'knowledge', KnowledgeBaseViewSet, basename='notebook-knowledge')
notebooks_router.register(r'batches', BatchJobViewSet, basename='notebook-batches')

app_name = 'notebooks-api-v1'

urlpatterns = [
    # Include main router URLs
    path('', include(router.urls)),
    
    # Include nested router URLs
    path('', include(notebooks_router.urls)),
    
    # Custom endpoints
    path('<uuid:notebook_pk>/chat/agent/', SessionAgentInfoView.as_view(), name='session-agent-info'),
    
    # Additional custom endpoints (if needed)
    # path('health/', HealthCheckView.as_view(), name='health-check'),
]