import logging
from ..http_client import RagFlowHttpClient

logger = logging.getLogger(__name__)


class RagflowServiceBase:
    """
    Base service for RAGFlow operations.
    """

    def __init__(self, http_client: RagFlowHttpClient = None):
        """
        Initialize RagflowService.

        Args:
            http_client: RagFlowHttpClient instance (created if not provided)
        """
        self.http_client = http_client or RagFlowHttpClient()

    def close(self):
        """Close underlying HTTP client."""
        if self.http_client:
            self.http_client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def health_check(self) -> bool:
        """
        Check if RAGFlow service is reachable.

        Returns:
            True if service is healthy
        """
        try:
            # Simple health check - try to list datasets with page_size=1
            # This endpoint should be accessible with API key
            response = self.http_client.get("/api/v1/datasets", params={"page_size": 1})
            return response.is_success
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
