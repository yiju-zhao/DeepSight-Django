"""
Views for semantic search API.

Provides REST API endpoints for Lotus-powered semantic search
across various data types (publications, notebooks, etc.).
"""

import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    SemanticSearchRequestSerializer,
    SemanticSearchResponseSerializer,
)
from .services import lotus_semantic_search_service

logger = logging.getLogger(__name__)


class SemanticSearchViewSet(viewsets.ViewSet):
    """
    ViewSet for general-purpose semantic search operations.

    Provides endpoints for semantic filtering and ranking using Lotus library.
    Supports various entity types (publications, notebooks, etc.).
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="publications")
    def semantic_search_publications(self, request):
        """
        Perform semantic search on conference publications.

        POST /api/v1/semantic-search/semantic-search/publications/

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
