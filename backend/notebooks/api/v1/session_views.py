"""
Session-based Chat API ViewSet for notebooks.

Provides session-based chat functionality with tab management.
"""

import logging
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models import Notebook
from ...services.chat_service import ChatService

logger = logging.getLogger(__name__)


class SessionChatViewSet(viewsets.ViewSet):
    """
    ViewSet for session-based chat operations within notebooks.
    
    Provides endpoints for managing chat sessions and messaging:
    - POST /api/v1/notebooks/{notebook_id}/chat/sessions/ - Create session
    - GET /api/v1/notebooks/{notebook_id}/chat/sessions/ - List sessions  
    - GET /api/v1/notebooks/{notebook_id}/chat/sessions/{session_id}/ - Get session details
    - DELETE /api/v1/notebooks/{notebook_id}/chat/sessions/{session_id}/ - Close session
    - PATCH /api/v1/notebooks/{notebook_id}/chat/sessions/{session_id}/ - Update session
    - POST /api/v1/notebooks/{notebook_id}/chat/sessions/{session_id}/messages/ - Send message
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_service = ChatService()
    
    def get_notebook(self, request, notebook_pk):
        """Get notebook instance with permission check."""
        try:
            return Notebook.objects.get(id=notebook_pk, user=request.user)
        except Notebook.DoesNotExist:
            return None
    
    def list(self, request, notebook_pk=None):
        """List all chat sessions for the notebook."""
        notebook = self.get_notebook(request, notebook_pk)
        if not notebook:
            return Response(
                {"error": "Notebook not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        include_closed = request.query_params.get('include_closed', 'false').lower() == 'true'
        
        try:
            result = self.chat_service.list_chat_sessions(notebook, request.user.id, include_closed)
            
            if not result.get('success'):
                return Response(
                    {"error": result.get('error', 'Unknown error')},
                    status=result.get('status_code', status.HTTP_500_INTERNAL_SERVER_ERROR)
                )
            
            return Response(result)
            
        except Exception as e:
            logger.exception(f"Failed to list sessions: {e}")
            return Response(
                {"error": "Failed to list sessions", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request, notebook_pk=None):
        """Create a new chat session."""
        notebook = self.get_notebook(request, notebook_pk)
        if not notebook:
            return Response(
                {"error": "Notebook not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        title = request.data.get('title')
        
        try:
            result = self.chat_service.create_chat_session(notebook, request.user.id, title)
            
            if not result.get('success'):
                return Response(
                    {"error": result.get('error', 'Unknown error')},
                    status=result.get('status_code', status.HTTP_500_INTERNAL_SERVER_ERROR)
                )
            
            return Response(result, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.exception(f"Failed to create session: {e}")
            return Response(
                {"error": "Failed to create session", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, notebook_pk=None, pk=None):
        """Get details of a specific chat session."""
        notebook = self.get_notebook(request, notebook_pk)
        if not notebook:
            return Response(
                {"error": "Notebook not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            result = self.chat_service.get_chat_session(pk, notebook, request.user.id)
            
            if not result.get('success'):
                return Response(
                    {"error": result.get('error', 'Unknown error')},
                    status=result.get('status_code', status.HTTP_404_NOT_FOUND)
                )
            
            return Response(result)
            
        except Exception as e:
            logger.exception(f"Failed to get session: {e}")
            return Response(
                {"error": "Failed to get session", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, notebook_pk=None, pk=None):
        """Close/delete a chat session."""
        notebook = self.get_notebook(request, notebook_pk)
        if not notebook:
            return Response(
                {"error": "Notebook not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        delete_ragflow_session = request.query_params.get('delete_ragflow', 'true').lower() == 'true'
        
        try:
            result = self.chat_service.close_chat_session(pk, notebook, request.user.id, delete_ragflow_session)
            
            if not result.get('success'):
                return Response(
                    {"error": result.get('error', 'Unknown error')},
                    status=result.get('status_code', status.HTTP_404_NOT_FOUND)
                )
            
            return Response(result, status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.exception(f"Failed to close session: {e}")
            return Response(
                {"error": "Failed to close session", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def partial_update(self, request, notebook_pk=None, pk=None):
        """Update session details (currently only title)."""
        notebook = self.get_notebook(request, notebook_pk)
        if not notebook:
            return Response(
                {"error": "Notebook not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        title = request.data.get('title')
        if not title:
            return Response(
                {"error": "Title is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = self.chat_service.update_session_title(pk, notebook, request.user.id, title)
            
            if not result.get('success'):
                return Response(
                    {"error": result.get('error', 'Unknown error')},
                    status=result.get('status_code', status.HTTP_404_NOT_FOUND)
                )
            
            return Response(result)
            
        except Exception as e:
            logger.exception(f"Failed to update session: {e}")
            return Response(
                {"error": "Failed to update session", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='messages')
    def send_message(self, request, notebook_pk=None, pk=None):
        """Send a message in a specific session with streaming response."""
        notebook = self.get_notebook(request, notebook_pk)
        if not notebook:
            return Response(
                {"error": "Notebook not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        message = request.data.get('message')
        if not message:
            return Response(
                {"error": "Message is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create streaming response
            def generate_response():
                stream = self.chat_service.create_session_chat_stream(
                    session_id=pk,
                    notebook=notebook,
                    user_id=request.user.id,
                    question=message
                )
                
                for chunk in stream:
                    yield chunk
            
            response = StreamingHttpResponse(
                generate_response(),
                content_type='text/plain'
            )
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'  # For nginx
            return response
            
        except Exception as e:
            logger.exception(f"Failed to send message: {e}")
            return Response(
                {"error": "Failed to send message", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='messages')
    def get_messages(self, request, notebook_pk=None, pk=None):
        """Get message history for a specific session."""
        notebook = self.get_notebook(request, notebook_pk)
        if not notebook:
            return Response(
                {"error": "Notebook not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            result = self.chat_service.get_chat_session(pk, notebook, request.user.id)
            
            if not result.get('success'):
                return Response(
                    {"error": result.get('error', 'Unknown error')},
                    status=result.get('status_code', status.HTTP_404_NOT_FOUND)
                )
            
            return Response({
                "success": True,
                "messages": result['session']['messages']
            })
            
        except Exception as e:
            logger.exception(f"Failed to get messages: {e}")
            return Response(
                {"error": "Failed to get messages", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='cleanup')
    def cleanup_inactive_sessions(self, request, notebook_pk=None):
        """Clean up inactive sessions older than specified hours."""
        notebook = self.get_notebook(request, notebook_pk)
        if not notebook:
            return Response(
                {"error": "Notebook not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        max_age_hours = request.data.get('max_age_hours', 24)
        
        try:
            result = self.chat_service.cleanup_inactive_sessions(notebook, max_age_hours)
            
            if not result.get('success'):
                return Response(
                    {"error": result.get('error', 'Unknown error')},
                    status=result.get('status_code', status.HTTP_500_INTERNAL_SERVER_ERROR)
                )
            
            return Response(result)
            
        except Exception as e:
            logger.exception(f"Failed to cleanup sessions: {e}")
            return Response(
                {"error": "Failed to cleanup sessions", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SessionAgentInfoView(APIView):
    """
    Get agent information for a notebook.
    
    GET /api/v1/notebooks/{notebook_id}/chat/agent/
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_service = ChatService()
    
    def get(self, request, notebook_pk):
        """Get agent information for the notebook."""
        try:
            notebook = Notebook.objects.get(id=notebook_pk, user=request.user)
        except Notebook.DoesNotExist:
            return Response(
                {"error": "Notebook not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            result = self.chat_service.get_agent_info(notebook)
            return Response(result)
            
        except Exception as e:
            logger.exception(f"Failed to get agent info: {e}")
            return Response(
                {"error": "Failed to get agent info", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )