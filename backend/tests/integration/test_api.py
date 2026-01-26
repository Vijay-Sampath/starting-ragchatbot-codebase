"""API endpoint tests for the RAG System FastAPI application"""

import pytest
from unittest.mock import Mock


class TestQueryEndpoint:
    """Test cases for POST /api/query endpoint"""

    @pytest.mark.api
    def test_query_endpoint_success(self, test_client):
        """Test successful query with valid input"""
        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["answer"] == "Test answer from RAG system"
        assert data["sources"] == ["Source 1", "Source 2"]

    @pytest.mark.api
    def test_query_endpoint_with_session_id(self, test_client, test_app):
        """Test query with provided session_id"""
        response = test_client.post(
            "/api/query",
            json={"query": "What is lesson 2 about?", "session_id": "my-session-456"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "my-session-456"

        # Verify RAG system was called with the provided session_id
        test_app.state.rag_system.query.assert_called_with(
            "What is lesson 2 about?",
            "my-session-456"
        )

    @pytest.mark.api
    def test_query_endpoint_creates_session_when_missing(self, test_client, test_app):
        """Test that session is created when not provided"""
        response = test_client.post(
            "/api/query",
            json={"query": "Tell me about tools"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"

        # Verify session manager was called to create session
        test_app.state.rag_system.session_manager.create_session.assert_called_once()

    @pytest.mark.api
    def test_query_endpoint_empty_query(self, test_client):
        """Test query with empty string"""
        response = test_client.post(
            "/api/query",
            json={"query": ""}
        )

        # Empty query should still be processed (validation at RAG level)
        assert response.status_code == 200

    @pytest.mark.api
    def test_query_endpoint_missing_query_field(self, test_client):
        """Test request with missing query field"""
        response = test_client.post(
            "/api/query",
            json={}
        )

        # FastAPI should return 422 for validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.api
    def test_query_endpoint_invalid_json(self, test_client):
        """Test request with invalid JSON"""
        response = test_client.post(
            "/api/query",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    @pytest.mark.api
    def test_query_endpoint_handles_rag_error(self, test_client_with_errors):
        """Test error handling when RAG system fails"""
        response = test_client_with_errors.post(
            "/api/query",
            json={"query": "This will fail"}
        )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Database connection failed" in data["detail"]


class TestCoursesEndpoint:
    """Test cases for GET /api/courses endpoint"""

    @pytest.mark.api
    def test_courses_endpoint_success(self, test_client):
        """Test successful retrieval of course statistics"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data
        assert data["total_courses"] == 3
        assert len(data["course_titles"]) == 3
        assert "Course A" in data["course_titles"]

    @pytest.mark.api
    def test_courses_endpoint_response_model(self, test_client):
        """Test that response matches CourseStats model"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Verify structure matches expected model
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        for title in data["course_titles"]:
            assert isinstance(title, str)

    @pytest.mark.api
    def test_courses_endpoint_handles_error(self, test_client_with_errors):
        """Test error handling when analytics service fails"""
        response = test_client_with_errors.get("/api/courses")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Analytics service unavailable" in data["detail"]


class TestRootEndpoint:
    """Test cases for GET / endpoint"""

    @pytest.mark.api
    def test_root_endpoint_success(self, test_client):
        """Test root endpoint returns health status"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"


class TestAPIIntegration:
    """Integration tests for API workflow scenarios"""

    @pytest.mark.api
    @pytest.mark.integration
    def test_query_flow_with_sources(self, test_client, test_app):
        """Test complete query flow returns sources correctly"""
        # Configure mock to return specific sources
        test_app.state.rag_system.query.return_value = (
            "The MCP course covers building AI applications.",
            ["[MCP Course - Lesson 1](https://example.com/lesson1)"]
        )

        response = test_client.post(
            "/api/query",
            json={"query": "What does the MCP course cover?"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) == 1
        assert "MCP Course" in data["sources"][0]

    @pytest.mark.api
    @pytest.mark.integration
    def test_query_flow_no_sources(self, test_client, test_app):
        """Test query flow when no sources are found"""
        # Configure mock to return empty sources
        test_app.state.rag_system.query.return_value = (
            "I don't have information about that topic.",
            []
        )

        response = test_client.post(
            "/api/query",
            json={"query": "Tell me about quantum computing"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sources"] == []

    @pytest.mark.api
    @pytest.mark.integration
    def test_multiple_queries_same_session(self, test_client, test_app):
        """Test multiple queries using the same session ID"""
        session_id = "persistent-session"

        # First query
        response1 = test_client.post(
            "/api/query",
            json={"query": "What is lesson 1?", "session_id": session_id}
        )
        assert response1.status_code == 200
        assert response1.json()["session_id"] == session_id

        # Second query
        response2 = test_client.post(
            "/api/query",
            json={"query": "What is lesson 2?", "session_id": session_id}
        )
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

        # Verify both queries used the same session
        calls = test_app.state.rag_system.query.call_args_list
        assert len(calls) == 2
        assert calls[0][0][1] == session_id
        assert calls[1][0][1] == session_id

    @pytest.mark.api
    @pytest.mark.integration
    def test_courses_then_query_workflow(self, test_client, test_app):
        """Test typical workflow: check courses then query"""
        # First, get available courses
        courses_response = test_client.get("/api/courses")
        assert courses_response.status_code == 200
        courses = courses_response.json()["course_titles"]

        # Then query about a specific course
        test_app.state.rag_system.query.return_value = (
            f"Course A covers advanced topics.",
            ["Course A - Lesson 1"]
        )

        query_response = test_client.post(
            "/api/query",
            json={"query": f"What does {courses[0]} cover?"}
        )

        assert query_response.status_code == 200
        assert "Course A" in query_response.json()["answer"]


class TestAPIEdgeCases:
    """Edge case tests for API endpoints"""

    @pytest.mark.api
    def test_query_with_special_characters(self, test_client):
        """Test query containing special characters"""
        response = test_client.post(
            "/api/query",
            json={"query": "What about <script>alert('xss')</script>?"}
        )

        # Should process without error (sanitization at RAG level)
        assert response.status_code == 200

    @pytest.mark.api
    def test_query_with_unicode(self, test_client):
        """Test query containing unicode characters"""
        response = test_client.post(
            "/api/query",
            json={"query": "What is 日本語 and émojis 🎉?"}
        )

        assert response.status_code == 200

    @pytest.mark.api
    def test_query_with_very_long_input(self, test_client):
        """Test query with very long input string"""
        long_query = "What is " + "a" * 10000 + "?"

        response = test_client.post(
            "/api/query",
            json={"query": long_query}
        )

        # Should process (length limits handled by RAG/Claude)
        assert response.status_code == 200

    @pytest.mark.api
    def test_concurrent_queries_different_sessions(self, test_client, test_app):
        """Test handling multiple concurrent queries with different sessions"""
        import threading
        import queue

        results = queue.Queue()

        def make_query(session_id, query):
            response = test_client.post(
                "/api/query",
                json={"query": query, "session_id": session_id}
            )
            results.put((session_id, response.status_code))

        threads = [
            threading.Thread(target=make_query, args=(f"session-{i}", f"Query {i}"))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify all queries succeeded
        while not results.empty():
            session_id, status_code = results.get()
            assert status_code == 200


class TestFrontendUI:
    """Test cases for frontend UI elements (reads HTML file directly)"""

    @pytest.fixture
    def html_content(self):
        """Read the index.html file directly from the frontend directory"""
        import os
        # Navigate from backend/tests/integration to frontend
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        html_path = os.path.join(base_dir, "frontend", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()

    @pytest.mark.frontend
    def test_index_html_exists(self, html_content):
        """Test that index.html exists and is readable"""
        assert html_content is not None
        assert len(html_content) > 0
        assert "<!doctype html>" in html_content.lower() or "<!DOCTYPE html>" in html_content

    @pytest.mark.frontend
    def test_header_displays_course_compass(self, html_content):
        """Test that the header shows 'Course Compass' title"""
        assert "<h1>Course Compass</h1>" in html_content

    @pytest.mark.frontend
    def test_subheader_displays_tagline(self, html_content):
        """Test that the subheader shows the AI-powered tagline"""
        assert "Your AI-powered learning companion" in html_content
        assert 'class="subtitle"' in html_content

    @pytest.mark.frontend
    def test_page_title_is_course_compass(self, html_content):
        """Test that the page title is set to Course Compass"""
        assert "<title>Course Compass</title>" in html_content

    @pytest.mark.frontend
    def test_theme_toggle_button_exists(self, html_content):
        """Test that the theme toggle button is present"""
        assert 'id="themeToggle"' in html_content
        assert 'class="theme-toggle"' in html_content

    @pytest.mark.frontend
    def test_new_chat_button_exists(self, html_content):
        """Test that the new chat button is present"""
        assert 'id="newChatButton"' in html_content
        assert "+ NEW CHAT" in html_content

    @pytest.mark.frontend
    def test_css_version_is_current(self, html_content):
        """Test that CSS has cache-busting version parameter"""
        assert "style.css?v=" in html_content

    @pytest.mark.frontend
    def test_js_version_is_current(self, html_content):
        """Test that JS has cache-busting version parameter"""
        assert "script.js?v=" in html_content
