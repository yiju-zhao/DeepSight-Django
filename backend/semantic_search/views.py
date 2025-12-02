"""
Views for semantic search API.

Provides streaming REST API endpoints for Lotus-powered semantic search
across various data types (publications, notebooks, etc.).
"""

import json
import logging
import uuid

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SemanticSearchRequestSerializer
from .tasks import semantic_search_streaming_task

logger = logging.getLogger(__name__)


class InitiateStreamingSearchView(APIView):
    """
    Initiate streaming semantic search.
    
    POST /api/v1/semantic-search/publications/stream/
    
    Returns job_id immediately. Client should connect to SSE endpoint
    at GET /api/v1/semantic-search/publications/stream/{job_id}/
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Start async semantic search job.
        
        Request body:
        {
            "publication_ids": ["uuid-1", "uuid-2", ...],
            "query": "papers about AI",
            "topk": 20
        }
        
        Response:
        {
            "success": true,
            "job_id": "unique-job-id",
            "stream_url": "/api/v1/semantic-search/publications/stream/unique-job-id/"
        }
        """
        # Validate request
        request_serializer = SemanticSearchRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(
                {
                    "error": "VALIDATION_ERROR",
                    "detail": "Invalid request parameters",
                    "field_errors": request_serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        validated_data = request_serializer.validated_data
        publication_ids = [str(uid) for uid in validated_data["publication_ids"]]
        query = validated_data["query"]
        topk = validated_data["topk"]
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        logger.info(
            f"Starting streaming search job {job_id} for user {request.user.id}: "
            f"{len(publication_ids)} publications"
        )
        
        # Launch Celery task asynchronously
        semantic_search_streaming_task.delay(
            publication_ids=publication_ids, query=query, topk=topk, job_id=job_id
        )
        
        # Return job ID immediately
        return Response(
            {
                "success": True,
                "job_id": job_id,
                "stream_url": f"/api/v1/semantic-search/publications/stream/{job_id}/",
            },
            status=status.HTTP_202_ACCEPTED,
        )



class SemanticSearchStreamView(View):
    """
    SSE endpoint for streaming semantic search progress.
    
    Subscribes to Redis Pub/Sub channel: semantic_search:{job_id}
    Streams progress updates (started, batch, complete, error) to the client.
    """
    
    MAX_DURATION_SECONDS = 600  # 10 minutes max connection time
    
    @method_decorator(csrf_exempt)
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def options(self, request, job_id: str):
        response = HttpResponse()
        # CORS headers for credentials mode
        origin = request.META.get('HTTP_ORIGIN', 'http://localhost:5173')
        response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Credentials"] = "true"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Accept, Authorization, Content-Type"
        return response
    
    def get(self, request, job_id: str):
        """Stream search progress for a specific job."""
        try:
            logger.info(
                f"Starting semantic search stream for job {job_id}, user {request.user.id}"
            )
            
            response = StreamingHttpResponse(
                self.generate_search_stream(job_id), content_type="text/event-stream"
            )
            response["Cache-Control"] = "no-cache"
            response["X-Accel-Buffering"] = "no"  # Disable nginx buffering
            
            # CORS headers for credentials mode
            origin = request.META.get('HTTP_ORIGIN', 'http://localhost:5173')
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Headers"] = "Accept, Authorization, Content-Type"
            response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            return response
            
        except Exception as e:
            logger.exception(f"Failed to create semantic search SSE stream: {e}")
            return HttpResponse(
                f"Error: {str(e)}", status=500, content_type="text/plain"
            )
    
    def generate_search_stream(self, job_id: str):
        """
        Generate SSE stream by subscribing to Redis Pub/Sub channel.
        
        Yields:
            SSE formatted messages with search progress updates
        """
        from .utils.redis_pubsub import subscribe_to_channel
        
        try:
            channel = f"semantic_search:{job_id}"
            
            logger.info(f"Subscribed to Redis channel: {channel}")
            
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'job_id': job_id})}\n\n"
            
            # Subscribe to Redis channel and forward messages
            for message in subscribe_to_channel(channel, timeout=self.MAX_DURATION_SECONDS):
                yield f"data: {json.dumps(message)}\n\n"
                
                # Close stream on completion or error
                if message.get("type") in ["complete", "error"]:
                    logger.info(f"Search job {job_id} finished: {message.get('type')}")
                    break
                    
        except GeneratorExit:
            logger.info(f"Client disconnected from search stream for job {job_id}")
            
        except Exception as e:
            logger.exception(f"Error in search stream for job {job_id}: {e}")
            try:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            except:
                pass
