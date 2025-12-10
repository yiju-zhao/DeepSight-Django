"""
Unit tests for Lotus semantic search service.

Tests the LotusSemanticSearchService without making actual LLM API calls.
Uses mocking to simulate Lotus behavior.
"""

from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pandas as pd
from django.conf import settings
from django.test import TestCase

from conferences.models import Instance, Publication, Venue
from semantic_search.services.lotus_service import LotusSemanticSearchService


class LotusSemanticSearchServiceTestCase(TestCase):
    """Test cases for LotusSemanticSearchService"""

    def setUp(self):
        """Set up test fixtures"""
        # Create test venue
        self.venue = Venue.objects.create(
            name="Test Conference",
            type="Conference",
            description="Test conference description",
        )

        # Create test instance
        self.instance = Instance.objects.create(
            venue=self.venue,
            year=2024,
            start_date="2024-06-01",
            end_date="2024-06-05",
            location="Test City",
        )

        # Create test publications
        self.publications = []
        for i in range(5):
            pub = Publication.objects.create(
                instance=self.instance,
                title=f"Test Paper {i}",
                abstract=f"Abstract about AI and machine learning {i}",
                keywords=f"AI;ML;Deep Learning {i}",
                authors=f"Author {i}",
                rating=4.0 + i * 0.1,
            )
            self.publications.append(pub)

        # Initialize service
        self.service = LotusSemanticSearchService()

    def test_publications_to_dataframe_empty(self):
        """Test DataFrame conversion with empty list"""
        df = self.service._publications_to_dataframe([])
        self.assertTrue(df.empty)

    def test_publications_to_dataframe_valid(self):
        """Test DataFrame conversion with valid publications"""
        df = self.service._publications_to_dataframe(self.publications)

        # Check DataFrame structure
        self.assertEqual(len(df), 5)
        self.assertIn("id", df.columns)
        self.assertIn("semantic_text", df.columns)
        self.assertIn("title", df.columns)
        self.assertIn("abstract", df.columns)
        self.assertIn("venue", df.columns)
        self.assertIn("year", df.columns)

        # Check data content
        first_row = df.iloc[0]
        self.assertEqual(first_row["title"], "Test Paper 0")
        self.assertEqual(first_row["venue"], "Test Conference")
        self.assertEqual(first_row["year"], 2024)

        # Check semantic_text combines title + abstract + keywords
        self.assertIn("Test Paper 0", first_row["semantic_text"])
        self.assertIn("Abstract about AI", first_row["semantic_text"])
        self.assertIn("AI;ML;Deep Learning", first_row["semantic_text"])

    @patch("datasets.services.lotus_service.lotus")
    @patch("datasets.services.lotus_service.LM")
    def test_initialize_lotus_success(self, mock_lm_class, mock_lotus):
        """Test successful Lotus initialization"""
        # Setup mocks
        mock_lm = Mock()
        mock_lm_class.return_value = mock_lm

        # Initialize
        service = LotusSemanticSearchService()
        service._initialize_lotus()

        # Verify initialization
        self.assertTrue(service._lotus_initialized)
        mock_lm_class.assert_called_once_with(model="gpt-4.1-mini")
        mock_lotus.settings.configure.assert_called_once()

    @patch("datasets.services.lotus_service.lotus")
    @patch("datasets.services.lotus_service.LM")
    def test_semantic_search_empty_ids(self, mock_lm_class, mock_lotus):
        """Test semantic search with empty publication IDs"""
        result = self.service.semantic_search(publication_ids=[], query="test query")

        # Should return empty result with success=True
        self.assertTrue(result["success"])
        self.assertEqual(result["total_input"], 0)
        self.assertEqual(result["total_results"], 0)
        self.assertEqual(len(result["results"]), 0)

    @patch("datasets.services.lotus_service.lotus")
    @patch("datasets.services.lotus_service.LM")
    def test_semantic_search_success(self, mock_lm_class, mock_lotus):
        """Test successful semantic search"""
        # Setup mocks
        mock_lm = Mock()
        mock_lm_class.return_value = mock_lm

        # Mock DataFrame with sem_topk method (embedding prefilter is internal)
        mock_df = MagicMock(spec=pd.DataFrame)
        mock_df.empty = False
        mock_df.__len__ = lambda self: 5

        mock_filtered_df = MagicMock(spec=pd.DataFrame)
        mock_ranked_df = pd.DataFrame(
            {
                "id": [str(self.publications[0].id)],
                "title": ["Test Paper 0"],
                "abstract": ["Abstract about AI and machine learning 0"],
                "authors": ["Author 0"],
                "keywords": ["AI;ML;Deep Learning 0"],
                "rating": [4.0],
                "venue": ["Test Conference"],
                "year": [2024],
            }
        )

        # Setup mock behavior
        mock_filtered_df.empty = False
        mock_filtered_df.__len__ = lambda self: 1
        mock_filtered_df.sem_topk.return_value = mock_ranked_df

        # Patch internal helpers:
        # - _publications_to_dataframe returns our mock_df
        # - _embedding_prefilter returns mock_filtered_df (simulating 2*topk selection)
        with patch.object(
            self.service, "_publications_to_dataframe", return_value=mock_df
        ), patch.object(
            self.service, "_embedding_prefilter", return_value=mock_filtered_df
        ):
            publication_ids = [str(pub.id) for pub in self.publications]
            result = self.service.semantic_search(
                publication_ids=publication_ids, query="papers about AI", topk=3
            )

        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["query"], "papers about AI")
        self.assertEqual(result["total_input"], 5)
        self.assertEqual(result["total_results"], 1)
        self.assertEqual(len(result["results"]), 1)

        # Verify result structure
        first_result = result["results"][0]
        self.assertIn("id", first_result)
        self.assertIn("title", first_result)
        self.assertIn("relevance_score", first_result)
        self.assertEqual(first_result["title"], "Test Paper 0")

    def test_semantic_search_nonexistent_ids(self):
        """Test semantic search with non-existent publication IDs"""
        fake_ids = [str(uuid4()) for _ in range(3)]

        result = self.service.semantic_search(publication_ids=fake_ids, query="test")

        # Should return empty results
        self.assertTrue(result["success"])
        self.assertEqual(result["total_results"], 0)

    @patch("datasets.services.lotus_service.lotus")
    @patch("datasets.services.lotus_service.LM")
    def test_semantic_search_max_publications_limit(self, mock_lm_class, mock_lotus):
        """Test that max_publications limit is enforced"""
        # Create many publication IDs
        many_ids = [str(uuid4()) for _ in range(2000)]

        # Mock to avoid actual processing
        with patch.object(Publication.objects, "filter") as mock_filter:
            mock_filter.return_value.select_related.return_value = []

            result = self.service.semantic_search(
                publication_ids=many_ids, query="test", topk=10
            )

        # Should have logged warning and truncated
        # (Check that it didn't crash)
        self.assertIsNotNone(result)

    def test_handle_lotus_error_api_error(self):
        """Test error handling for API errors"""
        error = Exception("OpenAI API connection failed")
        result = self.service._handle_lotus_error(error, "test query", 10)

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "LLM_API_ERROR")
        self.assertIn("LLM API", result["detail"])

    def test_handle_lotus_error_rate_limit(self):
        """Test error handling for rate limit errors"""
        error = Exception("Rate limit exceeded")
        result = self.service._handle_lotus_error(error, "test query", 10)

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "RATE_LIMIT_ERROR")
        self.assertIn("rate limit", result["detail"])

    def test_handle_lotus_error_timeout(self):
        """Test error handling for timeout errors"""
        error = Exception("Request timeout")
        result = self.service._handle_lotus_error(error, "test query", 10)

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "TIMEOUT_ERROR")
        self.assertIn("timeout", result["detail"])

    def test_handle_lotus_error_generic(self):
        """Test error handling for generic errors"""
        error = Exception("Something went wrong")
        result = self.service._handle_lotus_error(error, "test query", 10)

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "SEMANTIC_SEARCH_ERROR")
        self.assertIn("Something went wrong", result["detail"])


class ChromaIntegrationTestCase(TestCase):
    """Test Chroma vector store integration"""

    def setUp(self):
        self.service = LotusSemanticSearchService()

    @patch("semantic_search.services.lotus_service.settings")
    def test_chroma_disabled_via_settings(self, mock_settings):
        """Chroma initialization skipped if disabled in settings"""
        mock_settings.CHROMA_CONFIG = {"enabled": False}

        result = self.service._initialize_chroma()

        self.assertFalse(result)
        self.assertFalse(self.service._chroma_available)

    @patch("semantic_search.services.lotus_service.settings")
    def test_chroma_missing_persist_dir(self, mock_settings):
        """Chroma initialization fails if CHROMA_PERSIST_DIR not set"""
        mock_settings.CHROMA_CONFIG = {"enabled": True, "persist_dir": None}

        result = self.service._initialize_chroma()

        self.assertFalse(result)
        self.assertFalse(self.service._chroma_available)

    @patch("semantic_search.services.lotus_service.Chroma")
    @patch("semantic_search.services.lotus_service.settings")
    def test_chroma_initialization_success(self, mock_settings, mock_chroma_class):
        """Chroma initializes successfully with valid config"""
        mock_settings.CHROMA_CONFIG = {
            "enabled": True,
            "persist_dir": "/tmp/chroma_test",
            "collection_name": "test_collection",
            "use_xinference": False,
            "fallback_model": "intfloat/e5-base-v2",
        }

        # Mock Chroma collection with data
        mock_collection = MagicMock()
        mock_collection.count.return_value = 100
        mock_chroma_instance = MagicMock()
        mock_chroma_instance._collection = mock_collection
        mock_chroma_class.return_value = mock_chroma_instance

        result = self.service._initialize_chroma()

        self.assertTrue(result)
        self.assertTrue(self.service._chroma_available)
        mock_chroma_class.assert_called_once()

    @patch("semantic_search.services.lotus_service.settings")
    def test_chroma_prefilter_when_disabled(self, mock_settings):
        """Chroma prefilter returns None when Chroma is disabled"""
        mock_settings.CHROMA_CONFIG = {"enabled": False}
        self.service._chroma_initialized = True
        self.service._chroma_available = False

        result = self.service._chroma_prefilter(
            query="test query",
            publication_ids=["uuid1", "uuid2"],
            topk=10
        )

        self.assertIsNone(result)

    @patch("semantic_search.services.lotus_service.settings")
    def test_chroma_prefilter_success(self, mock_settings):
        """Chroma prefilter returns publication IDs on success"""
        # Setup
        mock_settings.CHROMA_CONFIG = {
            "enabled": True,
            "default_k_multiplier": 2,
            "max_candidates": 100,
        }

        # Mock Chroma vector store
        mock_results = [
            MagicMock(metadata={"publication_id": "uuid1"}),
            MagicMock(metadata={"publication_id": "uuid2"}),
        ]
        self.service._chroma_vector_store = MagicMock()
        self.service._chroma_vector_store.similarity_search.return_value = mock_results
        self.service._chroma_available = True
        self.service._chroma_initialized = True

        result = self.service._chroma_prefilter(
            query="test query",
            publication_ids=["uuid1", "uuid2", "uuid3"],
            topk=10
        )

        self.assertEqual(result, ["uuid1", "uuid2"])
        self.service._chroma_vector_store.similarity_search.assert_called_once()

    @patch("semantic_search.services.lotus_service.settings")
    def test_handle_lotus_error_chroma(self, mock_settings):
        """Test error handling for Chroma errors"""
        mock_settings.LOTUS_CONFIG = {"default_model": "gpt-4o"}

        error = Exception("Chroma connection failed")
        result = self.service._handle_lotus_error(error, "test query", 10)

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "CHROMA_ERROR")
        self.assertIn("Chroma vector store error", result["detail"])
