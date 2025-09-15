"""
View tests for the notebooks module.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock

from ..models import Notebook, KnowledgeBaseItem

User = get_user_model()


class NotebookViewTests(APITestCase):
    """Test cases for Notebook API views."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

    def test_create_notebook(self):
        """Test notebook creation via API."""
        url = reverse("notebook-list-create")
        data = {"name": "Test Notebook", "description": "Test description"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Notebook.objects.count(), 1)

        notebook = Notebook.objects.first()
        self.assertEqual(notebook.name, "Test Notebook")
        self.assertEqual(notebook.user, self.user)

    def test_list_notebooks(self):
        """Test notebook listing via API."""
        # Create test notebooks
        Notebook.objects.create(user=self.user, name="Notebook 1")
        Notebook.objects.create(user=self.user, name="Notebook 2")

        # Create notebook for another user (should not appear)
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pass"
        )
        Notebook.objects.create(user=other_user, name="Other Notebook")

        url = reverse("notebook-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["name"], "Notebook 2")  # Most recent first

    def test_retrieve_notebook(self):
        """Test notebook retrieval via API."""
        notebook = Notebook.objects.create(user=self.user, name="Test Notebook")
        
        url = reverse("notebook-detail", kwargs={"pk": str(notebook.id)})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Notebook")

    def test_unauthorized_access(self):
        """Test that unauthorized users cannot access notebooks."""
        self.client.force_authenticate(user=None)
        
        url = reverse("notebook-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_isolation(self):
        """Test that users can only access their own notebooks."""
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pass"
        )
        other_notebook = Notebook.objects.create(user=other_user, name="Other Notebook")

        # Try to access other user's notebook
        url = reverse("notebook-detail", kwargs={"pk": str(other_notebook.id)})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class FileViewSetTests(APITestCase):
    """Test cases for File API views."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

        self.notebook = Notebook.objects.create(user=self.user, name="Test Notebook")
        self.other_notebook = Notebook.objects.create(user=self.other_user, name="Other Notebook")

        self.file_item = KnowledgeBaseItem.objects.create(
            notebook=self.notebook,
            title="test_file.pdf",
            content_type="application/pdf",
            file_path="/path/to/test_file.pdf"
        )
        self.other_file_item = KnowledgeBaseItem.objects.create(
            notebook=self.other_notebook,
            title="other_file.pdf",
            content_type="application/pdf",
            file_path="/path/to/other_file.pdf"
        )

    @patch('notebooks.views.FileViewSet.kb_service')
    def test_raw_action_returns_attachment(self, mock_kb_service):
        """Test that the raw action returns Content-Disposition: attachment."""
        # Mock the service response
        mock_kb_service.get_raw_file.return_value = {
            'data': b'fake file content',
            'content_type': 'application/pdf',
            'filename': 'test_file.pdf'
        }

        url = f"/api/v1/notebooks/{self.notebook.id}/files/{self.file_item.id}/raw/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="test_file.pdf"')
        self.assertNotIn('X-Content-Type-Options', response)
        self.assertEqual(response.content, b'fake file content')

    @patch('notebooks.views.FileViewSet.kb_service')
    def test_inline_action_returns_inline(self, mock_kb_service):
        """Test that the inline action returns Content-Disposition: inline with security headers."""
        # Mock the service response
        mock_kb_service.get_raw_file.return_value = {
            'data': b'fake file content',
            'content_type': 'application/pdf',
            'filename': 'test_file.pdf'
        }

        url = f"/api/v1/notebooks/{self.notebook.id}/files/{self.file_item.id}/inline/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(response['Content-Disposition'], 'inline; filename="test_file.pdf"')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.content, b'fake file content')

    @patch('notebooks.views.FileViewSet.kb_service')
    def test_inline_action_permission_check(self, mock_kb_service):
        """Test that the inline action enforces permission checks."""
        # Try to access another user's file
        url = f"/api/v1/notebooks/{self.other_notebook.id}/files/{self.other_file_item.id}/inline/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_kb_service.get_raw_file.assert_not_called()

    @patch('notebooks.views.FileViewSet.kb_service')
    def test_raw_action_permission_check(self, mock_kb_service):
        """Test that the raw action enforces permission checks."""
        # Try to access another user's file
        url = f"/api/v1/notebooks/{self.other_notebook.id}/files/{self.other_file_item.id}/raw/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_kb_service.get_raw_file.assert_not_called()

    def test_inline_action_unauthenticated(self):
        """Test that the inline action requires authentication."""
        self.client.force_authenticate(user=None)

        url = f"/api/v1/notebooks/{self.notebook.id}/files/{self.file_item.id}/inline/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('notebooks.views.FileViewSet.kb_service')
    def test_inline_action_service_error(self, mock_kb_service):
        """Test that the inline action handles service errors gracefully."""
        # Mock the service to raise an exception
        mock_kb_service.get_raw_file.side_effect = Exception("Service error")

        url = f"/api/v1/notebooks/{self.notebook.id}/files/{self.file_item.id}/inline/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
        self.assertEqual(response.data["detail"], "Service error")

    @patch('notebooks.views.FileViewSet.kb_service')
    def test_inline_action_handles_different_content_types(self, mock_kb_service):
        """Test that the inline action preserves content types correctly."""
        test_cases = [
            {
                'content_type': 'text/plain',
                'filename': 'test.txt',
                'data': b'Hello world'
            },
            {
                'content_type': 'image/jpeg',
                'filename': 'image.jpg',
                'data': b'fake image data'
            },
            {
                'content_type': 'video/mp4',
                'filename': 'video.mp4',
                'data': b'fake video data'
            }
        ]

        for case in test_cases:
            with self.subTest(content_type=case['content_type']):
                mock_kb_service.get_raw_file.return_value = case

                url = f"/api/v1/notebooks/{self.notebook.id}/files/{self.file_item.id}/inline/"
                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response['Content-Type'], case['content_type'])
                self.assertEqual(response['Content-Disposition'], f'inline; filename="{case["filename"]}"')
                self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
                self.assertEqual(response.content, case['data']) 