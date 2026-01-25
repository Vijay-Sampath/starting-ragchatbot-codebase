"""Unit tests for SearchTools components (CourseSearchTool, CourseOutlineTool, ToolManager)"""

import pytest
from unittest.mock import Mock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchTool:
    """Test cases for CourseSearchTool"""

    def test_course_search_tool_execute_respects_max_results(self, mock_vector_store):
        """Verify CourseSearchTool passes no limit parameter, relying on VectorStore's max_results"""

        # Setup mock vector store configured with max_results=0
        mock_vector_store.max_results = 0
        mock_search_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        mock_vector_store.search = Mock(return_value=mock_search_results)

        # Create tool with mocked vector store
        tool = CourseSearchTool(mock_vector_store)

        # Execute search
        result = tool.execute(query="What is in lesson 1?")

        # Assertions:
        # 1. Verify VectorStore.search was called
        mock_vector_store.search.assert_called_once()

        # 2. Verify NO limit parameter was passed (should use configured max_results)
        call_args = mock_vector_store.search.call_args
        assert call_args.kwargs.get('limit') is None, "Should not pass limit parameter"

        # 3. Verify result indicates no content found
        assert "No relevant content found" in result

    def test_course_search_tool_formats_empty_results(self, mock_vector_store):
        """Verify CourseSearchTool handles empty SearchResults correctly"""

        empty_results = SearchResults(documents=[], metadata=[], distances=[])
        mock_vector_store.search = Mock(return_value=empty_results)

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test")

        assert result == "No relevant content found."
        assert tool.last_sources == []  # No sources tracked

    def test_course_search_tool_formats_results_with_content(self, mock_vector_store):
        """Verify CourseSearchTool correctly formats non-empty results"""

        results = SearchResults(
            documents=["Lesson content here"],
            metadata=[{"course_title": "MCP Course", "lesson_number": 1, "chunk_index": 0}],
            distances=[0.1]
        )
        mock_vector_store.search = Mock(return_value=results)
        mock_vector_store.get_lesson_link = Mock(return_value="http://example.com/lesson1")

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test")

        # Verify formatting
        assert "[MCP Course - Lesson 1]" in result
        assert "Lesson content here" in result
        assert len(tool.last_sources) == 1

    def test_course_search_tool_with_course_filter(self, mock_vector_store):
        """Verify CourseSearchTool passes course_name parameter correctly"""

        empty_results = SearchResults(documents=[], metadata=[], distances=[])
        mock_vector_store.search = Mock(return_value=empty_results)

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test content", course_name="MCP Course")

        # Verify search was called with course_name parameter
        call_args = mock_vector_store.search.call_args
        assert call_args.kwargs['course_name'] == "MCP Course"

    def test_course_search_tool_with_lesson_filter(self, mock_vector_store):
        """Verify CourseSearchTool passes lesson_number parameter correctly"""

        empty_results = SearchResults(documents=[], metadata=[], distances=[])
        mock_vector_store.search = Mock(return_value=empty_results)

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test content", lesson_number=2)

        # Verify search was called with lesson_number parameter
        call_args = mock_vector_store.search.call_args
        assert call_args.kwargs['lesson_number'] == 2

    def test_course_search_tool_handles_search_error(self, mock_vector_store):
        """Verify CourseSearchTool handles search errors correctly"""

        error_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="Search error: Database connection failed"
        )
        mock_vector_store.search = Mock(return_value=error_results)

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test")

        # Verify error message is returned
        assert "Search error: Database connection failed" in result

    def test_course_search_tool_tracks_sources_with_links(self, mock_vector_store):
        """Verify CourseSearchTool tracks sources as markdown links when available"""

        results = SearchResults(
            documents=["Content 1", "Content 2"],
            metadata=[
                {"course_title": "MCP Course", "lesson_number": 1, "chunk_index": 0},
                {"course_title": "MCP Course", "lesson_number": 2, "chunk_index": 1}
            ],
            distances=[0.1, 0.15]
        )
        mock_vector_store.search = Mock(return_value=results)
        mock_vector_store.get_lesson_link = Mock(side_effect=[
            "http://example.com/lesson1",
            "http://example.com/lesson2"
        ])

        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test")

        # Verify sources are tracked as markdown links
        assert len(tool.last_sources) == 2
        assert "[MCP Course - Lesson 1](http://example.com/lesson1)" in tool.last_sources
        assert "[MCP Course - Lesson 2](http://example.com/lesson2)" in tool.last_sources


class TestCourseOutlineTool:
    """Test cases for CourseOutlineTool"""

    def test_course_outline_tool_execute(self, mock_vector_store, sample_course_outline):
        """Verify CourseOutlineTool retrieves and formats course outline"""

        mock_vector_store.get_course_outline = Mock(return_value=sample_course_outline)

        tool = CourseOutlineTool(mock_vector_store)
        result = tool.execute(course_name="MCP")

        # Verify outline contains expected information
        assert "MCP: Build Rich-Context AI Apps with Anthropic" in result
        assert "Test Instructor" in result
        assert "Lesson 0: Introduction" in result
        assert "Lesson 1: Getting Started" in result
        assert "(3 total)" in result  # 3 lessons

    def test_course_outline_tool_nonexistent_course(self, mock_vector_store):
        """Verify CourseOutlineTool handles nonexistent course"""

        mock_vector_store.get_course_outline = Mock(return_value=None)

        tool = CourseOutlineTool(mock_vector_store)
        result = tool.execute(course_name="NonexistentCourse")

        assert "No course found matching 'NonexistentCourse'" in result

    def test_course_outline_tool_tracks_sources(self, mock_vector_store, sample_course_outline):
        """Verify CourseOutlineTool tracks course as source"""

        mock_vector_store.get_course_outline = Mock(return_value=sample_course_outline)

        tool = CourseOutlineTool(mock_vector_store)
        tool.execute(course_name="MCP")

        # Verify source is tracked
        assert len(tool.last_sources) == 1
        assert "[MCP: Build Rich-Context AI Apps with Anthropic](https://example.com/mcp-course)" in tool.last_sources[0]


class TestToolManager:
    """Test cases for ToolManager"""

    def test_tool_manager_register_tool(self, mock_vector_store):
        """Verify ToolManager registers tools correctly"""

        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)

        manager.register_tool(tool)

        # Verify tool is registered
        assert "search_course_content" in manager.tools

    def test_tool_manager_execute_tool(self, mock_vector_store):
        """Verify ToolManager executes registered tools"""

        manager = ToolManager()

        # Mock tool
        mock_vector_store.search = Mock(return_value=SearchResults([], [], []))
        tool = CourseSearchTool(mock_vector_store)

        manager.register_tool(tool)

        # Execute tool
        result = manager.execute_tool("search_course_content", query="test")

        # Verify tool was executed
        assert "No relevant content found" in result

    def test_tool_manager_execute_nonexistent_tool(self):
        """Verify ToolManager handles nonexistent tool gracefully"""

        manager = ToolManager()

        result = manager.execute_tool("nonexistent_tool", query="test")

        assert "Tool 'nonexistent_tool' not found" in result

    def test_tool_manager_get_last_sources(self, mock_vector_store, sample_course_outline):
        """Verify ToolManager retrieves sources from last tool execution"""

        manager = ToolManager()

        # Register outline tool
        mock_vector_store.get_course_outline = Mock(return_value=sample_course_outline)
        outline_tool = CourseOutlineTool(mock_vector_store)
        manager.register_tool(outline_tool)

        # Execute tool
        manager.execute_tool("get_course_outline", course_name="MCP")

        # Retrieve sources
        sources = manager.get_last_sources()

        assert len(sources) == 1
        assert "MCP: Build Rich-Context AI Apps" in sources[0]

    def test_tool_manager_reset_sources(self, mock_vector_store):
        """Verify ToolManager resets sources correctly"""

        manager = ToolManager()

        # Register search tool
        results = SearchResults(
            documents=["content"],
            metadata=[{"course_title": "Test", "lesson_number": 1}],
            distances=[0.1]
        )
        mock_vector_store.search = Mock(return_value=results)
        mock_vector_store.get_lesson_link = Mock(return_value="http://test.com")

        search_tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(search_tool)

        # Execute tool and verify sources exist
        manager.execute_tool("search_course_content", query="test")
        sources_before = manager.get_last_sources()
        assert len(sources_before) > 0

        # Reset sources
        manager.reset_sources()

        # Verify sources are cleared
        sources_after = manager.get_last_sources()
        assert len(sources_after) == 0

    def test_tool_manager_get_tool_definitions(self, mock_vector_store):
        """Verify ToolManager returns tool definitions for Anthropic API"""

        manager = ToolManager()

        search_tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(search_tool)

        definitions = manager.get_tool_definitions()

        assert len(definitions) == 1
        assert definitions[0]["name"] == "search_course_content"
        assert "description" in definitions[0]
        assert "input_schema" in definitions[0]
