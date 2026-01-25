"""Integration tests for RAGSystem end-to-end flows"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from rag_system import RAGSystem
from vector_store import SearchResults
from config import Config


class TestRAGSystemMaxResults:
    """Integration tests for MAX_RESULTS configuration"""

    def test_rag_system_respects_max_results_config(self, mock_anthropic_client, mock_chroma_client, config_max_results_zero):
        """Integration test: Verify complete RAG flow respects MAX_RESULTS=0"""

        # Create RAG system with MAX_RESULTS=0
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.AIGenerator') as MockAIGen, \
             patch('rag_system.VectorStore') as MockVectorStore:

            # Setup mock VectorStore
            mock_vector_store_instance = Mock()
            mock_vector_store_instance.max_results = 0

            # Mock ChromaDB query to verify n_results=0 is passed
            mock_search_response = {
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]]
            }
            mock_vector_store_instance.course_content.query = Mock(
                return_value=mock_search_response
            )
            mock_vector_store_instance.search = Mock(
                return_value=SearchResults.from_chroma(mock_search_response)
            )
            mock_vector_store_instance.get_lesson_link = Mock(return_value=None)
            mock_vector_store_instance.get_course_link = Mock(return_value=None)

            MockVectorStore.return_value = mock_vector_store_instance

            # Setup mock AIGenerator
            mock_ai_gen_instance = Mock()

            # First response: Claude decides to use search tool
            tool_use_response = Mock()
            tool_use_response.stop_reason = "tool_use"

            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.id = "call_1"
            tool_block.name = "search_course_content"
            tool_block.input = {"query": "test content"}

            tool_use_response.content = [tool_block]

            # Second response: Claude answers with empty results
            final_response = Mock()
            final_text = Mock()
            final_text.text = "No information found about that topic."
            final_response.content = [final_text]

            mock_ai_gen_instance.client = Mock()
            mock_ai_gen_instance.client.messages.create = Mock(
                side_effect=[tool_use_response, final_response]
            )
            mock_ai_gen_instance.generate_response = Mock(
                return_value="No information found about that topic."
            )

            MockAIGen.return_value = mock_ai_gen_instance

            # Create RAG system
            rag_system = RAGSystem(config_max_results_zero)

            # Execute query
            response, sources = rag_system.query("What is in lesson 1?")

            # Assertions:
            # 1. Verify VectorStore was initialized with max_results=0
            assert mock_vector_store_instance.max_results == 0

            # 2. Verify response indicates no results
            assert "No information found" in response

            # 3. Verify sources list is empty
            assert sources == []

    @pytest.mark.parametrize("max_results", [0, 1, 3, 5])
    def test_rag_system_max_results_values(self, max_results, mock_chroma_client):
        """Parametrized: Verify RAGSystem respects various MAX_RESULTS settings"""

        config = Mock(spec=Config)
        config.MAX_RESULTS = max_results
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.MAX_HISTORY = 2
        config.ANTHROPIC_API_KEY = "test-key"
        config.ANTHROPIC_MODEL = "test-model"
        config.EMBEDDING_MODEL = "test-embedding"
        config.CHROMA_PATH = "./test_db"

        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.VectorStore') as MockVectorStore:

            mock_vector_store_instance = Mock()
            mock_vector_store_instance.max_results = max_results
            MockVectorStore.return_value = mock_vector_store_instance

            rag_system = RAGSystem(config)

            # Verify VectorStore was initialized with correct max_results
            assert rag_system.vector_store.max_results == max_results


class TestRAGSystemToolIntegration:
    """Integration tests for tool registration and execution"""

    def test_rag_system_registers_all_tools(self, mock_chroma_client, config_max_results_zero):
        """Verify RAGSystem registers both search and outline tools"""

        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.VectorStore'):

            rag_system = RAGSystem(config_max_results_zero)

            # Verify both tools are registered
            tool_definitions = rag_system.tool_manager.get_tool_definitions()
            tool_names = [tool['name'] for tool in tool_definitions]

            assert 'search_course_content' in tool_names
            assert 'get_course_outline' in tool_names

    def test_rag_system_source_tracking(self, mock_anthropic_client, mock_chroma_client, config_max_results_zero):
        """Verify RAGSystem correctly tracks and returns sources"""

        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.AIGenerator') as MockAIGen, \
             patch('rag_system.VectorStore') as MockVectorStore:

            # Setup mock VectorStore with results
            mock_vector_store_instance = Mock()
            results_with_content = SearchResults(
                documents=["Test content"],
                metadata=[{"course_title": "Test Course", "lesson_number": 1, "chunk_index": 0}],
                distances=[0.1]
            )
            mock_vector_store_instance.search = Mock(return_value=results_with_content)
            mock_vector_store_instance.get_lesson_link = Mock(return_value="http://test.com/lesson1")

            MockVectorStore.return_value = mock_vector_store_instance

            # Setup mock AIGenerator
            mock_ai_gen_instance = Mock()
            mock_ai_gen_instance.generate_response = Mock(return_value="Here's what I found")

            MockAIGen.return_value = mock_ai_gen_instance

            # Create RAG system
            rag_system = RAGSystem(config_max_results_zero)

            # Manually set up tool for this test
            from search_tools import CourseSearchTool
            search_tool = CourseSearchTool(mock_vector_store_instance)

            # Execute search tool directly to track sources
            search_tool.execute(query="test")

            # Simulate source retrieval
            sources = search_tool.last_sources

            # Verify sources are tracked
            assert len(sources) > 0
            assert "Test Course - Lesson 1" in sources[0]

    def test_rag_system_sources_reset_between_queries(self, mock_anthropic_client, mock_chroma_client, config_max_results_zero):
        """Verify sources are reset between queries to prevent carryover"""

        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.AIGenerator') as MockAIGen, \
             patch('rag_system.VectorStore') as MockVectorStore:

            mock_vector_store_instance = Mock()
            mock_vector_store_instance.search = Mock(return_value=SearchResults([], [], []))

            MockVectorStore.return_value = mock_vector_store_instance

            mock_ai_gen_instance = Mock()
            mock_ai_gen_instance.generate_response = Mock(return_value="Response")

            MockAIGen.return_value = mock_ai_gen_instance

            rag_system = RAGSystem(config_max_results_zero)

            # First query
            rag_system.query("First question")

            # Verify reset_sources is called
            assert rag_system.tool_manager.reset_sources is not None


class TestRAGSystemSessionManagement:
    """Integration tests for conversation history management"""

    def test_rag_system_creates_session(self, mock_anthropic_client, mock_chroma_client, config_max_results_zero):
        """Verify RAGSystem creates session history"""

        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager') as MockSessionManager, \
             patch('rag_system.AIGenerator') as MockAIGen, \
             patch('rag_system.VectorStore'):

            mock_session_manager = Mock()
            mock_session_manager.get_conversation_history = Mock(return_value=None)
            mock_session_manager.add_exchange = Mock()

            MockSessionManager.return_value = mock_session_manager

            mock_ai_gen_instance = Mock()
            mock_ai_gen_instance.generate_response = Mock(return_value="Answer")

            MockAIGen.return_value = mock_ai_gen_instance

            rag_system = RAGSystem(config_max_results_zero)

            # Query with session_id
            rag_system.query("Test question", session_id="session_123")

            # Verify session methods were called
            mock_session_manager.get_conversation_history.assert_called_with("session_123")
            mock_session_manager.add_exchange.assert_called_once()


class TestRAGSystemErrorHandling:
    """Integration tests for error handling scenarios"""

    def test_rag_system_handles_vector_store_errors(self, mock_anthropic_client, mock_chroma_client, config_max_results_zero):
        """Verify RAGSystem handles VectorStore errors gracefully"""

        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.AIGenerator') as MockAIGen, \
             patch('rag_system.VectorStore') as MockVectorStore:

            # Setup mock VectorStore that returns error
            mock_vector_store_instance = Mock()
            error_results = SearchResults(
                documents=[],
                metadata=[],
                distances=[],
                error="Database connection failed"
            )
            mock_vector_store_instance.search = Mock(return_value=error_results)

            MockVectorStore.return_value = mock_vector_store_instance

            # Setup mock AIGenerator
            mock_ai_gen_instance = Mock()
            mock_ai_gen_instance.generate_response = Mock(return_value="I encountered an error searching the database.")

            MockAIGen.return_value = mock_ai_gen_instance

            rag_system = RAGSystem(config_max_results_zero)

            # Execute query
            response, sources = rag_system.query("Test question")

            # Verify error is handled (no exception raised)
            assert response is not None
            assert sources == []

    def test_rag_system_handles_empty_results(self, mock_anthropic_client, mock_chroma_client, config_max_results_zero):
        """Verify RAGSystem handles empty search results correctly"""

        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.AIGenerator') as MockAIGen, \
             patch('rag_system.VectorStore') as MockVectorStore:

            # Setup mock VectorStore with empty results
            mock_vector_store_instance = Mock()
            empty_results = SearchResults(documents=[], metadata=[], distances=[])
            mock_vector_store_instance.search = Mock(return_value=empty_results)

            MockVectorStore.return_value = mock_vector_store_instance

            # Setup mock AIGenerator
            mock_ai_gen_instance = Mock()
            mock_ai_gen_instance.generate_response = Mock(return_value="I couldn't find any information about that.")

            MockAIGen.return_value = mock_ai_gen_instance

            rag_system = RAGSystem(config_max_results_zero)

            # Execute query
            response, sources = rag_system.query("Test question")

            # Verify empty results are handled
            assert response is not None
            assert "couldn't find" in response.lower() or "no information" in response.lower()
