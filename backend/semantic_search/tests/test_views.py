"""
Integration tests for semantic search streaming API views.

Tests the request/response cycle for initiating streaming semantic search.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from conferences.models import Instance, Publication, Venue

User = get_user_model()


class SemanticSearchStreamingAPITestCase(TestCase):
    """Integration tests for semantic search streaming API endpoint"""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.venue = Venue.objects.create(
            name="CVPR",
            type="Conference",
            description="Computer Vision Conference",
        )

        self.instance = Instance.objects.create(
            venue=self.venue,
            year=2024,
            start_date="2024-06-01",
            end_date="2024-06-05",
            location="Seattle",
        )

        self.publications = []
        for i in range(3):
            publication = Publication.objects.create(
                instance=self.instance,
                title=f"Deep Learning Paper {i}",
                abstract=(f"This paper presents novel approaches to deep learning {i}"),
                keywords=f"deep learning;neural networks;AI {i}",
                authors=f"Researcher {i}",
                rating=4.0,
            )
            self.publications.append(publication)

        self.url = reverse("initiate-search-stream")

    def test_authentication_required_for_streaming_initiation(self) -> None:
        """Unauthenticated requests should be rejected."""
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

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_missing_required_fields_for_streaming(self) -> None:
        """Validation when required fields are missing."""
        response = self.client.post(
            self.url,
            {
                "query": "test query",
                "topk": 5,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "publication_ids" in response.data["field_errors"]

        response = self.client.post(
            self.url,
            {
                "publication_ids": [str(self.publications[0].id)],
                "topk": 5,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "query" in response.data["field_errors"]

    def test_successful_streaming_initiation(self) -> None:
        """Valid request should start streaming job."""
        publication_ids = [str(publication.id) for publication in self.publications]

        response = self.client.post(
            self.url,
            {
                "publication_ids": publication_ids,
                "query": "test query",
                "topk": 5,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data["success"] is True
        assert "job_id" in response.data
        assert "stream_url" in response.data
