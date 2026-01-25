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

# API testing imports
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional


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


# ============================================================================
# API Testing Fixtures
# ============================================================================

# Pydantic models for API tests (mirrors app.py models)
class QueryRequest(BaseModel):
    """Request model for course queries"""
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for course queries"""
    answer: str
    sources: List[str]
    session_id: str


class CourseStats(BaseModel):
    """Response model for course statistics"""
    total_courses: int
    course_titles: List[str]


@pytest.fixture
def mock_rag_system():
    """Mock RAGSystem for API testing"""
    mock_system = Mock(spec=RAGSystem)

    # Mock session manager
    mock_session_manager = Mock()
    mock_session_manager.create_session = Mock(return_value="test-session-123")
    mock_system.session_manager = mock_session_manager

    # Mock query method
    mock_system.query = Mock(return_value=("Test answer from RAG system", ["Source 1", "Source 2"]))

    # Mock get_course_analytics
    mock_system.get_course_analytics = Mock(return_value={
        "total_courses": 3,
        "course_titles": ["Course A", "Course B", "Course C"]
    })

    return mock_system


@pytest.fixture
def test_app(mock_rag_system):
    """
    Create a test FastAPI app without static file mounting.

    This fixture creates a minimal app that mirrors the API endpoints
    from app.py but avoids the static files mount that causes issues
    in test environments where the frontend directory doesn't exist.
    """
    app = FastAPI(title="Course Materials RAG System - Test")

    # Store mock RAG system in app state
    app.state.rag_system = mock_rag_system

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        """Process a query and return response with sources"""
        try:
            rag_system = app.state.rag_system

            # Create session if not provided
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()

            # Process query using RAG system
            answer, sources = rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        """Get course analytics and statistics"""
        try:
            rag_system = app.state.rag_system
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        """Root endpoint for health check"""
        return {"status": "ok", "message": "RAG System API"}

    return app


@pytest.fixture
def test_client(test_app):
    """Create a test client for API testing"""
    return TestClient(test_app)


@pytest.fixture
def mock_rag_system_error():
    """Mock RAGSystem that raises exceptions for error testing"""
    mock_system = Mock(spec=RAGSystem)

    # Mock session manager
    mock_session_manager = Mock()
    mock_session_manager.create_session = Mock(return_value="error-session")
    mock_system.session_manager = mock_session_manager

    # Mock query to raise an exception
    mock_system.query = Mock(side_effect=Exception("Database connection failed"))

    # Mock get_course_analytics to raise an exception
    mock_system.get_course_analytics = Mock(side_effect=Exception("Analytics service unavailable"))

    return mock_system


@pytest.fixture
def test_app_with_errors(mock_rag_system_error):
    """Create a test app configured to simulate errors"""
    app = FastAPI(title="Course Materials RAG System - Error Test")
    app.state.rag_system = mock_rag_system_error

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            rag_system = app.state.rag_system
            session_id = request.session_id or rag_system.session_manager.create_session()
            answer, sources = rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            rag_system = app.state.rag_system
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


@pytest.fixture
def test_client_with_errors(test_app_with_errors):
    """Create a test client for error scenario testing"""
    return TestClient(test_app_with_errors)
