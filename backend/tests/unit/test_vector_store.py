"""Unit tests for VectorStore component"""

import pytest
from unittest.mock import Mock, patch, call
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from vector_store import VectorStore, SearchResults


class TestVectorStoreMaxResults:
    """Test cases for MAX_RESULTS configuration"""

    def test_vector_store_respects_max_results_zero(self, mock_chroma_client):
        """Verify VectorStore passes n_results=0 to ChromaDB when max_results=0"""
        store = VectorStore(
            chroma_path="./test_db",
            embedding_model="test-model",
            max_results=0
        )

        # Mock the course_content collection's query method
        mock_results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        store.course_content.query = Mock(return_value=mock_results)

        # Call search without limit parameter (should use configured max_results)
        results = store.search("test query")

        # Assertions:
        # 1. Verify ChromaDB was called with n_results=0
        store.course_content.query.assert_called_once()
        call_args = store.course_content.query.call_args
        assert call_args.kwargs['n_results'] == 0, "Should pass n_results=0 to ChromaDB"

        # 2. Verify results are empty
        assert results.is_empty(), "SearchResults should be empty when n_results=0"
        assert len(results.documents) == 0

    def test_vector_store_limit_override(self, mock_chroma_client):
        """Verify explicit limit parameter overrides MAX_RESULTS config"""
        store = VectorStore(
            chroma_path="./test_db",
            embedding_model="test-model",
            max_results=0
        )

        mock_results = {
            "documents": [["doc1"]],
            "metadatas": [[{"course_title": "test"}]],
            "distances": [[0.1]]
        }
        store.course_content.query = Mock(return_value=mock_results)

        # Call search WITH explicit limit (should override max_results=0)
        results = store.search("test query", limit=5)

        # Verify n_results=5 was passed, not 0
        call_args = store.course_content.query.call_args
        assert call_args.kwargs['n_results'] == 5, "Explicit limit should override configured max_results"

    @pytest.mark.parametrize("max_results_config", [0, 1, 3, 5, 10])
    def test_vector_store_max_results_parameter(self, max_results_config, mock_chroma_client):
        """Parametrized test: Verify n_results matches configured MAX_RESULTS"""
        store = VectorStore(
            chroma_path="./test_db",
            embedding_model="test-model",
            max_results=max_results_config
        )

        mock_results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        store.course_content.query = Mock(return_value=mock_results)

        store.search("test query")

        call_args = store.course_content.query.call_args
        assert call_args.kwargs['n_results'] == max_results_config

    def test_vector_store_stores_max_results_value(self, mock_chroma_client):
        """Verify VectorStore correctly stores max_results in instance variable"""
        store_zero = VectorStore("./test_db", "test-model", max_results=0)
        assert store_zero.max_results == 0

        store_five = VectorStore("./test_db", "test-model", max_results=5)
        assert store_five.max_results == 5


class TestSearchResults:
    """Test cases for SearchResults dataclass"""

    def test_search_results_empty_detection(self):
        """Verify SearchResults correctly identifies empty results"""
        empty_results = SearchResults(documents=[], metadata=[], distances=[])
        assert empty_results.is_empty(), "Empty results should be detected"

        non_empty = SearchResults(
            documents=["doc1"],
            metadata=[{"key": "value"}],
            distances=[0.1]
        )
        assert not non_empty.is_empty(), "Non-empty results should be detected"

    def test_search_results_from_chroma(self):
        """Test SearchResults.from_chroma() creation"""
        chroma_results = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"key1": "val1"}, {"key2": "val2"}]],
            "distances": [[0.1, 0.2]]
        }

        results = SearchResults.from_chroma(chroma_results)

        assert len(results.documents) == 2
        assert results.documents == ["doc1", "doc2"]
        assert len(results.metadata) == 2
        assert results.metadata[0]["key1"] == "val1"

    def test_search_results_empty_factory(self):
        """Test SearchResults.empty() factory method"""
        results = SearchResults.empty("Test error message")

        assert results.is_empty()
        assert results.error == "Test error message"
        assert len(results.documents) == 0


class TestVectorStoreSearchBehavior:
    """Test cases for search behavior with filters and course name resolution"""

    def test_search_with_course_name_resolution(self, mock_chroma_client):
        """Verify search resolves course name before searching content"""
        store = VectorStore("./test_db", "test-model", max_results=5)

        # Mock course catalog query (for name resolution)
        catalog_results = {
            "documents": [["MCP Course"]],
            "metadatas": [[{"title": "MCP: Build Rich-Context AI Apps"}]],
            "distances": [[0.1]]
        }
        store.course_catalog.query = Mock(return_value=catalog_results)

        # Mock content query
        content_results = {
            "documents": [["Content"]],
            "metadatas": [[{"course_title": "MCP: Build Rich-Context AI Apps"}]],
            "distances": [[0.1]]
        }
        store.course_content.query = Mock(return_value=content_results)

        # Search with partial course name
        results = store.search("test query", course_name="MCP")

        # Verify course catalog was queried for name resolution
        store.course_catalog.query.assert_called_once()
        catalog_call = store.course_catalog.query.call_args
        assert catalog_call.kwargs['query_texts'] == ["MCP"]

        # Verify content was searched with resolved course title in filter
        store.course_content.query.assert_called_once()
        content_call = store.course_content.query.call_args
        assert content_call.kwargs['where']['course_title'] == "MCP: Build Rich-Context AI Apps"

    def test_search_with_nonexistent_course(self, mock_chroma_client):
        """Verify search returns error when course name doesn't resolve"""
        store = VectorStore("./test_db", "test-model", max_results=5)

        # Mock empty catalog results
        store.course_catalog.query = Mock(return_value={
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        })

        results = store.search("test query", course_name="NonexistentCourse")

        # Verify error is returned
        assert results.error is not None
        assert "No course found" in results.error
        assert "NonexistentCourse" in results.error

    def test_search_builds_correct_filter_for_lesson_number(self, mock_chroma_client):
        """Verify search builds correct filter when lesson_number is provided"""
        store = VectorStore("./test_db", "test-model", max_results=5)

        mock_results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        store.course_content.query = Mock(return_value=mock_results)

        # Search with lesson number only (no course name)
        store.search("test query", lesson_number=2)

        call_args = store.course_content.query.call_args
        assert call_args.kwargs['where']['lesson_number'] == 2
