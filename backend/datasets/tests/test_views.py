"""
Integration tests for semantic search API views.

Tests the complete request/response cycle including authentication,
validation, and service integration.
"""

from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from conferences.models import Instance, Publication, Venue

User = get_user_model()


class SemanticSearchAPITestCase(TestCase):
    """Integration tests for semantic search API endpoint"""

    def setUp(self):
        """Set up test fixtures"""
        # Create test user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Create API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create test venue
        self.venue = Venue.objects.create(
            name="CVPR", type="Conference", description="Computer Vision Conference"
        )

        # Create test instance
        self.instance = Instance.objects.create(
            venue=self.venue,
            year=2024,
            start_date="2024-06-01",
            end_date="2024-06-05",
            location="Seattle",
        )

        # Create test publications
        self.publications = []
        for i in range(10):
            pub = Publication.objects.create(
                instance=self.instance,
                title=f"Deep Learning Paper {i}",
                abstract=f"This paper presents novel approaches to deep learning {i}",
                keywords=f"deep learning;neural networks;AI {i}",
                authors=f"Researcher {i}",
                rating=4.0 + i * 0.1,
            )
            self.publications.append(pub)

        # API endpoint URL
        self.url = reverse("semantic-search-semantic-search-publications")

    def test_authentication_required(self):
        """Test that authentication is required"""
        # Create unauthenticated client
        unauth_client = APIClient()

        response = unauth_client.post(
            self.url,
            {
                "publication_ids": [str(self.publications[0].id)],
                "query": "test query",
                "topk": 5,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_required_fields(self):
        """Test validation when required fields are missing"""
        # Missing publication_ids
        response = self.client.post(
            self.url, {"query": "test query", "topk": 5}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("publication_ids", response.data["field_errors"])

        # Missing query
        response = self.client.post(
            self.url,
            {"publication_ids": [str(self.publications[0].id)], "topk": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("query", response.data["field_errors"])

    def test_invalid_field_types(self):
        """Test validation with invalid field types"""
        # Invalid UUID format
        response = self.client.post(
            self.url,
            {"publication_ids": ["not-a-uuid"], "query": "test", "topk": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid topk (too large)
        response = self.client.post(
            self.url,
            {
                "publication_ids": [str(self.publications[0].id)],
                "query": "test",
                "topk": 1000,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid topk (negative)
        response = self.client.post(
            self.url,
            {
                "publication_ids": [str(self.publications[0].id)],
                "query": "test",
                "topk": -1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_publication_ids(self):
        """Test validation with empty publication_ids list"""
        response = self.client.post(
            self.url, {"publication_ids": [], "query": "test", "topk": 5}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("publication_ids", response.data["field_errors"])

    def test_duplicate_publication_ids(self):
        """Test validation with duplicate publication IDs"""
        pub_id = str(self.publications[0].id)
        response = self.client.post(
            self.url,
            {"publication_ids": [pub_id, pub_id], "query": "test", "topk": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_query_too_short(self):
        """Test validation with too short query"""
        response = self.client.post(
            self.url,
            {"publication_ids": [str(self.publications[0].id)], "query": "ab", "topk": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("query", response.data["field_errors"])

    def test_query_whitespace_only(self):
        """Test validation with whitespace-only query"""
        response = self.client.post(
            self.url,
            {"publication_ids": [str(self.publications[0].id)], "query": "   ", "topk": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("datasets.views.lotus_semantic_search_service.semantic_filter")
    def test_successful_semantic_search(self, mock_semantic_filter):
        """Test successful semantic search request"""
        # Mock service response
        mock_semantic_filter.return_value = {
            "success": True,
            "query": "papers about deep learning",
            "total_input": 3,
            "total_results": 2,
            "results": [
                {
                    "id": str(self.publications[0].id),
                    "title": "Deep Learning Paper 0",
                    "abstract": "This paper presents novel approaches to deep learning 0",
                    "authors": "Researcher 0",
                    "keywords": "deep learning;neural networks;AI 0",
                    "rating": 4.0,
                    "venue": "CVPR",
                    "year": 2024,
                    "relevance_score": 0.95,
                },
                {
                    "id": str(self.publications[1].id),
                    "title": "Deep Learning Paper 1",
                    "abstract": "This paper presents novel approaches to deep learning 1",
                    "authors": "Researcher 1",
                    "keywords": "deep learning;neural networks;AI 1",
                    "rating": 4.1,
                    "venue": "CVPR",
                    "year": 2024,
                    "relevance_score": 0.87,
                },
            ],
            "metadata": {"llm_model": "gpt-4o-mini", "processing_time_ms": 1234},
        }

        # Make request
        pub_ids = [str(pub.id) for pub in self.publications[:3]]
        response = self.client.post(
            self.url,
            {"publication_ids": pub_ids, "query": "papers about deep learning", "topk": 5},
            format="json",
        )

        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["query"], "papers about deep learning")
        self.assertEqual(response.data["total_input"], 3)
        self.assertEqual(response.data["total_results"], 2)
        self.assertEqual(len(response.data["results"]), 2)

        # Verify result structure
        first_result = response.data["results"][0]
        self.assertIn("id", first_result)
        self.assertIn("title", first_result)
        self.assertIn("relevance_score", first_result)
        self.assertEqual(first_result["relevance_score"], 0.95)

        # Verify metadata
        self.assertIn("metadata", response.data)
        self.assertEqual(response.data["metadata"]["llm_model"], "gpt-4o-mini")

    @patch("datasets.views.lotus_semantic_search_service.semantic_filter")
    def test_semantic_search_with_service_error(self, mock_semantic_filter):
        """Test handling of service-level errors"""
        # Mock service error response
        mock_semantic_filter.return_value = {
            "success": False,
            "query": "test query",
            "total_input": 5,
            "total_results": 0,
            "results": [],
            "error": "LLM_API_ERROR",
            "detail": "Failed to connect to OpenAI API",
            "metadata": {"llm_model": "gpt-4o-mini", "processing_time_ms": 0},
        }

        # Make request
        pub_ids = [str(pub.id) for pub in self.publications[:5]]
        response = self.client.post(
            self.url, {"publication_ids": pub_ids, "query": "test query", "topk": 5}, format="json"
        )

        # Should return 200 with error in body
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"], "LLM_API_ERROR")
        self.assertIn("OpenAI API", response.data["detail"])

    @patch("datasets.views.lotus_semantic_search_service.semantic_filter")
    def test_semantic_search_empty_results(self, mock_semantic_filter):
        """Test successful search with no matching results"""
        # Mock empty results
        mock_semantic_filter.return_value = {
            "success": True,
            "query": "nonexistent topic",
            "total_input": 5,
            "total_results": 0,
            "results": [],
            "metadata": {"llm_model": "gpt-4o-mini", "processing_time_ms": 500},
        }

        # Make request
        pub_ids = [str(pub.id) for pub in self.publications[:5]]
        response = self.client.post(
            self.url, {"publication_ids": pub_ids, "query": "nonexistent topic", "topk": 5}, format="json"
        )

        # Verify response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["total_results"], 0)
        self.assertEqual(len(response.data["results"]), 0)

    @patch("datasets.views.lotus_semantic_search_service.semantic_filter")
    def test_topk_default_value(self, mock_semantic_filter):
        """Test that topk defaults to 10 when not provided"""
        mock_semantic_filter.return_value = {
            "success": True,
            "query": "test",
            "total_input": 5,
            "total_results": 5,
            "results": [],
            "metadata": {"llm_model": "gpt-4o-mini", "processing_time_ms": 100},
        }

        # Make request without topk
        pub_ids = [str(pub.id) for pub in self.publications[:5]]
        response = self.client.post(
            self.url, {"publication_ids": pub_ids, "query": "test"}, format="json"
        )

        # Verify service was called with default topk=10
        mock_semantic_filter.assert_called_once()
        call_args = mock_semantic_filter.call_args
        self.assertEqual(call_args.kwargs["topk"], 10)

    @patch("datasets.views.lotus_semantic_search_service.semantic_filter")
    def test_unexpected_service_exception(self, mock_semantic_filter):
        """Test handling of unexpected exceptions from service"""
        # Mock unexpected exception
        mock_semantic_filter.side_effect = Exception("Unexpected error")

        # Make request
        pub_ids = [str(pub.id) for pub in self.publications[:3]]
        response = self.client.post(
            self.url, {"publication_ids": pub_ids, "query": "test", "topk": 5}, format="json"
        )

        # Should return 500
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"], "INTERNAL_ERROR")

    def test_nonexistent_publication_ids(self):
        """Test with non-existent publication IDs"""
        fake_ids = [str(uuid4()) for _ in range(3)]

        # This should not error, but return empty results
        with patch("datasets.views.lotus_semantic_search_service.semantic_filter") as mock_filter:
            mock_filter.return_value = {
                "success": True,
                "query": "test",
                "total_input": 3,
                "total_results": 0,
                "results": [],
                "metadata": {"llm_model": "gpt-4o-mini", "processing_time_ms": 50},
            }

            response = self.client.post(
                self.url, {"publication_ids": fake_ids, "query": "test", "topk": 5}, format="json"
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["total_results"], 0)
