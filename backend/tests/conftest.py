"""Shared pytest fixtures for RAG chatbot tests"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path so we can import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vector_store import VectorStore, SearchResults
from search_tools import Tool, CourseSearchTool, CourseOutlineTool, ToolManager
from ai_generator import AIGenerator
from rag_system import RAGSystem
from config import Config


@pytest.fixture
def mock_chroma_client():
    """Mock ChromaDB client and collections"""
    with patch('vector_store.chromadb') as mock_chroma:
        # Create mock collections
        mock_course_catalog = Mock()
        mock_course_content = Mock()

        # Setup client to return appropriate collection based on name
        mock_client = Mock()
        def get_or_create_collection(name, **kwargs):
            if name == "course_catalog":
                return mock_course_catalog
            else:  # course_content
                return mock_course_content

        mock_client.get_or_create_collection = Mock(side_effect=get_or_create_collection)

        mock_chroma.PersistentClient.return_value = mock_client
        mock_chroma.Settings = Mock()

        # Mock embedding function
        mock_embedding = Mock()
        mock_chroma.utils.embedding_functions.SentenceTransformerEmbeddingFunction.return_value = mock_embedding

        yield {
            'client': mock_client,
            'course_catalog': mock_course_catalog,
            'course_content': mock_course_content,
            'embedding': mock_embedding
        }


@pytest.fixture
def mock_vector_store():
    """Mock VectorStore instance with max_results=0"""
    store = Mock(spec=VectorStore)
    store.max_results = 0
    store.search = Mock()
    store.get_lesson_link = Mock(return_value=None)
    store.get_course_link = Mock(return_value=None)
    store.get_course_outline = Mock(return_value=None)
    store.course_content = Mock()
    store.course_catalog = Mock()
    return store


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client"""
    with patch('ai_generator.anthropic') as mock_anthropic:
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_tool_manager():
    """Mock ToolManager"""
    manager = Mock(spec=ToolManager)
    manager.execute_tool = Mock(return_value="No relevant content found.")
    manager.get_last_sources = Mock(return_value=[])
    manager.reset_sources = Mock()
    manager.get_tool_definitions = Mock(return_value=[
        {"name": "search_course_content"},
        {"name": "get_course_outline"}
    ])
    return manager


@pytest.fixture
def config_max_results_zero():
    """Configuration with MAX_RESULTS=0 for testing"""
    config = Mock(spec=Config)
    config.MAX_RESULTS = 0
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_HISTORY = 2
    config.ANTHROPIC_API_KEY = "test-key-12345"
    config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.CHROMA_PATH = "./test_chroma_db"
    return config


@pytest.fixture
def sample_search_results_empty():
    """Empty SearchResults for testing"""
    return SearchResults(
        documents=[],
        metadata=[],
        distances=[],
        error=None
    )


@pytest.fixture
def sample_search_results_with_content():
    """SearchResults with sample content for testing"""
    return SearchResults(
        documents=[
            "This is lesson 1 content about MCP servers.",
            "This is lesson 2 content about tool schemas."
        ],
        metadata=[
            {"course_title": "MCP Course", "lesson_number": 1, "chunk_index": 0},
            {"course_title": "MCP Course", "lesson_number": 2, "chunk_index": 1}
        ],
        distances=[0.1, 0.15]
    )


@pytest.fixture
def sample_course_outline():
    """Sample course outline for testing"""
    return {
        "course_title": "MCP: Build Rich-Context AI Apps with Anthropic",
        "course_link": "https://example.com/mcp-course",
        "instructor": "Test Instructor",
        "lessons": [
            {"lesson_number": 0, "lesson_title": "Introduction", "lesson_link": "https://example.com/lesson0"},
            {"lesson_number": 1, "lesson_title": "Getting Started", "lesson_link": "https://example.com/lesson1"},
            {"lesson_number": 2, "lesson_title": "Tool Schemas", "lesson_link": "https://example.com/lesson2"}
        ]
    }
