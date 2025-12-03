"""
Views for semantic search API.

Provides streaming REST API endpoints for Lotus-powered semantic search
across various data types (publications, notebooks, etc.).
"""

import json
import logging
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from conferences.models import Publication
from conferences.serializers import PublicationTableSerializer

from .serializers import BulkPublicationFetchSerializer, SemanticSearchRequestSerializer
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

        Uses non-blocking get_message() with heartbeat to maintain connection.
        Based on successful pattern from notebooks/views.py NotebookJobsSSEView.

        Yields:
            SSE formatted messages with search progress updates
        """
        import redis
        import time

        redis_client = None
        pubsub = None

        try:
            # Connect to Redis
            redis_client = redis.Redis.from_url(
                settings.CELERY_BROKER_URL, decode_responses=True
            )
            pubsub = redis_client.pubsub()

            # Subscribe to channel
            channel = f"semantic_search:{job_id}"
            pubsub.subscribe(channel)

            logger.info(f"Subscribed to Redis channel: {channel}")

            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'job_id': job_id})}\n\n"

            start_time = time.time()
            last_heartbeat = start_time
            last_event_data = None
            HEARTBEAT_INTERVAL = 30  # Send heartbeat every 30 seconds

            # Listen for messages with timeout and heartbeat
            while True:
                # Check max duration
                elapsed = time.time() - start_time
                if elapsed > self.MAX_DURATION_SECONDS:
                    logger.info(f"Search stream for job {job_id} reached max duration")
                    yield f"data: {json.dumps({'type': 'timeout', 'message': 'Stream timeout'})}\n\n"
                    break

                # Get message with short timeout (allows heartbeat and duration checks)
                message = pubsub.get_message(timeout=1.0)

                if message and message["type"] == "message":
                    # Forward the event to client, avoid duplicate sends
                    event_data = message["data"]
                    if event_data != last_event_data:
                        yield f"data: {event_data}\n\n"
                        last_event_data = event_data
                        logger.debug(f"Forwarded search event: {event_data[:100]}...")
                    last_heartbeat = time.time()

                    # Check if this is completion or error
                    try:
                        parsed = json.loads(event_data)
                        if parsed.get("type") in ["complete", "error"]:
                            logger.info(
                                f"Search job {job_id} finished: {parsed.get('type')}"
                            )
                            break
                    except json.JSONDecodeError:
                        pass

                # Send heartbeat if idle (keeps connection alive)
                elif time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
                    yield ": heartbeat\n\n"
                    last_heartbeat = time.time()

        except GeneratorExit:
            logger.info(f"Client disconnected from search stream for job {job_id}")

        except Exception as e:
            logger.exception(f"Error in search stream for job {job_id}: {e}")
            try:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            except:
                pass

        finally:
            # Clean up Redis connection
            if pubsub:
                try:
                    pubsub.unsubscribe()
                    pubsub.close()
                except:
                    pass

            if redis_client:
                try:
                    redis_client.close()
                except:
                    pass

            logger.info(f"Closed search stream for job {job_id}")


class BulkPublicationFetchView(APIView):
    """
    Fetch full publication details for a list of IDs.

    POST /api/v1/semantic-search/publications/bulk/
    Body: { "publication_ids": ["uuid1", "uuid2", ...] }

    Used by frontend to fetch full publication data after receiving
    only IDs from semantic search streaming results.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Fetch publications by ID list.

        Returns publications in the same order as requested IDs.
        Missing IDs are silently skipped.
        """
        # Validate request
        serializer = BulkPublicationFetchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "error": "VALIDATION_ERROR",
                    "detail": "Invalid request parameters",
                    "field_errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ids = serializer.validated_data["publication_ids"]

        logger.info(
            f"Bulk fetching {len(ids)} publications for user {request.user.id}"
        )

        try:
            # Fetch publications with related data
            publications = Publication.objects.filter(id__in=ids).select_related(
                "instance",
                "instance__venue"
            ).prefetch_related()

            # Create ID to publication mapping
            id_to_pub = {p.id: p for p in publications}

            # Return publications in requested order, skip missing IDs
            ordered_pubs = [
                id_to_pub[pub_id]
                for pub_id in ids
                if pub_id in id_to_pub
            ]

            logger.info(
                f"Found {len(ordered_pubs)}/{len(ids)} publications"
            )

            # Serialize and return
            result_serializer = PublicationTableSerializer(ordered_pubs, many=True)
            return Response(result_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to fetch publications: {e}", exc_info=True)
            return Response(
                {
                    "error": "FETCH_FAILED",
                    "detail": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
