"""
Serializers for semantic search API.

Handles request validation and response formatting for Lotus-powered
semantic search operations.
"""

from rest_framework import serializers


class SemanticSearchRequestSerializer(serializers.Serializer):
    """
    Validates incoming semantic search requests.

    Expected format:
    {
        "publication_ids": ["uuid-1", "uuid-2", ...],
        "query": "natural language query",
        "topk": 20
    }
    """

    publication_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        # Allow many IDs at the API layer; Lotus service
        # will truncate to LOTUS_CONFIG['max_publications'] (10k) internally.
        max_length=100000,
        help_text=(
            "List of publication UUIDs to search within. "
            "If more than 10000 IDs are provided, only the first 10000 will be processed."
        ),
        error_messages={
            "min_length": "At least one publication ID is required",
            "max_length": "Maximum 100000 publication IDs allowed (first 10000 will be processed)",
        },
    )

    query = serializers.CharField(
        min_length=3,
        max_length=500,
        help_text="Natural language semantic query (e.g., 'papers about AI in healthcare')",
        error_messages={
            "min_length": "Query must be at least 3 characters",
            "max_length": "Query must not exceed 500 characters",
        },
    )

    topk = serializers.IntegerField(
        default=20,
        min_value=1,
        max_value=100,
        help_text="Number of top results to return (1-100)",
        error_messages={
            "min_value": "topk must be at least 1",
            "max_value": "topk must not exceed 100",
        },
    )

    def validate_publication_ids(self, value):
        """
        Validate publication_ids list.

        Ensures:
        - No duplicates
        - All UUIDs are valid (handled by UUIDField)
        """
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Duplicate publication IDs are not allowed"
            )
        return value

    def validate_query(self, value):
        """
        Validate semantic query string.

        Ensures:
        - Not just whitespace
        - Contains meaningful content
        """
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError(
                "Query cannot be empty or whitespace only"
            )
        return cleaned


class PublicationResultSerializer(serializers.Serializer):
    """
    Formats a single publication result with relevance score.

    Includes all key publication fields plus a relevance_score
    computed by Lotus semantic ranking.
    """

    id = serializers.UUIDField(help_text="Publication UUID")

    title = serializers.CharField(help_text="Publication title")

    abstract = serializers.CharField(allow_blank=True, help_text="Publication abstract")

    authors = serializers.CharField(
        allow_blank=True, help_text="Semicolon-separated list of authors"
    )

    keywords = serializers.CharField(
        allow_blank=True, help_text="Semicolon-separated list of keywords"
    )

    rating = serializers.FloatField(help_text="Publication rating/score")

    venue = serializers.CharField(
        allow_blank=True, help_text="Conference or journal venue name"
    )

    year = serializers.IntegerField(allow_null=True, help_text="Publication year")

    relevance_score = serializers.FloatField(
        help_text="Semantic relevance score (0.0-1.0, higher is more relevant)"
    )


class SemanticSearchResponseSerializer(serializers.Serializer):
    """
    Formats complete semantic search API response.

    Includes:
    - success: Operation status
    - query: Echo of input query
    - total_input: Number of publications searched
    - total_results: Number of results returned
    - results: List of ranked publications
    - metadata: Processing information
    - error/detail: Error information (only on failure)
    """

    success = serializers.BooleanField(
        help_text="Whether the semantic search completed successfully"
    )

    query = serializers.CharField(help_text="The semantic query that was executed")

    total_input = serializers.IntegerField(
        help_text="Number of publications in the input set"
    )

    total_results = serializers.IntegerField(
        help_text="Number of publications returned after filtering"
    )

    results = PublicationResultSerializer(
        many=True, help_text="List of publications ranked by semantic relevance"
    )

    metadata = serializers.DictField(
        help_text="Processing metadata (llm_model, processing_time_ms)"
    )

    # Error fields (only present on failure)
    error = serializers.CharField(
        required=False, help_text="Error code (only present on failure)"
    )

    detail = serializers.CharField(
        required=False,
        help_text="Human-readable error message (only present on failure)",
    )

    def validate(self, data):
        """
        Cross-field validation.

        Ensures:
        - If success=False, error and detail must be present
        - If success=True, results length matches total_results
        """
        if not data.get("success"):
            if not data.get("error") or not data.get("detail"):
                raise serializers.ValidationError(
                    "Error and detail fields are required when success=False"
                )

        if data.get("success") and len(data.get("results", [])) != data.get(
            "total_results", 0
        ):
            raise serializers.ValidationError(
                f"Results length ({len(data.get('results', []))}) does not match "
                f"total_results ({data.get('total_results', 0)})"
            )

        return data


class BulkPublicationFetchSerializer(serializers.Serializer):
    """
    Validates bulk publication fetch requests.

    Used to fetch full publication details for a list of IDs
    (typically returned from semantic search results).

    Expected format:
    {
        "publication_ids": ["uuid-1", "uuid-2", ...]
    }
    """

    publication_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100,
        help_text="List of publication UUIDs to fetch (max 100 per request)",
        error_messages={
            "min_length": "At least one publication ID is required",
            "max_length": "Maximum 100 publication IDs allowed per request",
        },
    )

    def validate_publication_ids(self, value):
        """
        Validate publication_ids list.

        Ensures:
        - No duplicates
        - All UUIDs are valid (handled by UUIDField)
        """
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Duplicate publication IDs are not allowed"
            )
        return value
