"""
Views for semantic search API.

Provides REST API endpoints for Lotus-powered semantic search
across various data types (publications, notebooks, etc.).
"""

import logging
import uuid

from django.http import StreamingHttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    SemanticSearchRequestSerializer,
    SemanticSearchResponseSerializer,
)
from .services import lotus_semantic_search_service
from .tasks import semantic_search_streaming_task
from .utils.redis_pubsub import subscribe_to_channel

logger = logging.getLogger(__name__)


class SemanticSearchViewSet(viewsets.ViewSet):
    """
    ViewSet for general-purpose semantic search operations.

    Provides endpoints for semantic filtering and ranking using Lotus library.
    Supports various entity types (publications, notebooks, etc.).
    """

    permission_classes = [IsAuthenticated]

    def create(self, request):
        """
        Perform semantic search on conference publications.

        POST /api/v1/semantic-search/publications/

        Request body:
        {
            "publication_ids": ["uuid-1", "uuid-2", ...],
            "query": "papers about artificial intelligence in healthcare",
            "topk": 10
        }

        Response (success):
        {
            "success": true,
            "query": "papers about artificial intelligence in healthcare",
            "total_input": 450,
            "total_results": 8,
            "results": [
                {
                    "id": "uuid",
                    "title": "...",
                    "abstract": "...",
                    "authors": "...",
                    "keywords": "...",
                    "rating": 4.5,
                    "venue": "CVPR",
                    "year": 2024,
                    "relevance_score": 0.95
                },
                ...
            ],
            "metadata": {
                "llm_model": "gpt-4o-mini",
                "processing_time_ms": 1234
            }
        }

        Response (error):
        {
            "success": false,
            "query": "...",
            "total_input": 450,
            "total_results": 0,
            "results": [],
            "error": "LLM_API_ERROR",
            "detail": "Failed to connect to LLM API",
            "metadata": {...}
        }

        Args:
            request: DRF Request object with publication_ids, query, topk

        Returns:
            Response with semantic search results or error
        """
        # Log request from user
        logger.info(
            f"Semantic search request from user {request.user.id}",
            extra={"user_id": request.user.id, "data_preview": str(request.data)[:200]},
        )

        # Validate request data
        request_serializer = SemanticSearchRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            logger.warning(
                f"Invalid semantic search request: {request_serializer.errors}",
                extra={"user_id": request.user.id, "errors": request_serializer.errors},
            )
            return Response(
                {
                    "error": "VALIDATION_ERROR",
                    "detail": "Invalid request parameters",
                    "field_errors": request_serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract validated data
        validated_data = request_serializer.validated_data
        publication_ids = [str(uuid) for uuid in validated_data["publication_ids"]]
        query = validated_data["query"]
        topk = validated_data["topk"]

        logger.info(
            f"Processing semantic search: {len(publication_ids)} publications, "
            f"query='{query[:50]}...', topk={topk}",
            extra={
                "user_id": request.user.id,
                "publication_count": len(publication_ids),
                "topk": topk,
            },
        )

        # Call semantic search service
        try:
            result = lotus_semantic_search_service.semantic_filter(
                publication_ids=publication_ids, query=query, topk=topk
            )
        except Exception as e:
            # Unexpected service-level exception (should be handled in service)
            logger.error(
                f"Unexpected error in semantic search: {str(e)}",
                exc_info=True,
                extra={"user_id": request.user.id, "query": query},
            )
            return Response(
                {
                    "success": False,
                    "query": query,
                    "total_input": len(publication_ids),
                    "total_results": 0,
                    "results": [],
                    "error": "INTERNAL_ERROR",
                    "detail": "An unexpected error occurred during semantic search",
                    "metadata": {"llm_model": "unknown", "processing_time_ms": 0},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Validate and return response
        response_serializer = SemanticSearchResponseSerializer(data=result)

        if not response_serializer.is_valid():
            # Service returned invalid response format
            logger.error(
                f"Invalid response from semantic search service: {response_serializer.errors}",
                extra={"user_id": request.user.id, "response_data": result},
            )
            return Response(
                {
                    "error": "INTERNAL_ERROR",
                    "detail": "Service returned invalid response format",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Determine HTTP status code based on success
        if result.get("success"):
            response_status = status.HTTP_200_OK
            logger.info(
                f"Semantic search succeeded: {result['total_results']} results in "
                f"{result['metadata'].get('processing_time_ms')}ms",
                extra={
                    "user_id": request.user.id,
                    "total_results": result["total_results"],
                    "processing_time_ms": result["metadata"].get("processing_time_ms"),
                },
            )
        else:
            # Service-level error (LLM API failure, timeout, etc.)
            response_status = status.HTTP_200_OK  # Return 200 with error in body
            logger.warning(
                f"Semantic search failed: {result.get('error')} - {result.get('detail')}",
                extra={
                    "user_id": request.user.id,
                    "error_code": result.get("error"),
                },
            )

        return Response(response_serializer.data, status=response_status)

    @action(detail=False, methods=["post"], url_path="stream")
    def stream_search(self, request):
        """
        Initiate streaming semantic search.

        POST /api/v1/semantic-search/publications/stream/

        Returns job_id immediately. Client should connect to SSE endpoint
        at GET /api/v1/semantic-search/publications/stream/{job_id}/

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
        publication_ids = [str(uuid) for uuid in validated_data["publication_ids"]]
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

    @action(detail=True, methods=["get"], url_path="")
    def stream_progress(self, request, pk=None):
        """
        SSE endpoint for streaming search progress.

        GET /api/v1/semantic-search/publications/stream/{job_id}/

        Returns Server-Sent Events stream with progress updates.

        Event types:
        - started: Search initiated
        - batch: Batch results available
        - complete: Search completed with final results
        - error: Search failed
        """
        job_id = pk

        logger.info(f"Client connected to SSE stream for job {job_id}")

        def event_stream():
            """Generator for SSE events."""
            try:
                channel = f"semantic_search:{job_id}"

                # Send initial connection message
                yield f"data: {{\"type\": \"connected\", \"job_id\": \"{job_id}\"}}\n\n"

                # Subscribe to Redis channel and stream messages
                for message in subscribe_to_channel(channel, timeout=600):
                    import json

                    yield f"data: {json.dumps(message)}\n\n"

                    # Close stream on completion or error
                    if message.get("type") in ["complete", "error"]:
                        break

            except Exception as e:
                logger.error(f"SSE stream error for job {job_id}: {e}", exc_info=True)
                import json

                error_msg = json.dumps({"type": "error", "detail": str(e)})
                yield f"data: {error_msg}\n\n"

        response = StreamingHttpResponse(
            event_stream(), content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"  # Disable nginx buffering
        return response
