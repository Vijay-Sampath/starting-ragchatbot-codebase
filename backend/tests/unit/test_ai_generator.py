"""Unit tests for AIGenerator component"""

import pytest
from unittest.mock import Mock, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ai_generator import AIGenerator


class TestAIGeneratorToolExecution:
    """Test cases for AIGenerator tool calling and execution"""

    def test_ai_generator_handles_empty_tool_results(self, mock_anthropic_client, mock_tool_manager):
        """Verify AIGenerator processes empty tool results correctly"""

        generator = AIGenerator(
            api_key="test-key",
            model="claude-sonnet-4-20250514"
        )
        generator.client = mock_anthropic_client

        # Setup mock: Claude requests tool use, tool returns empty
        tool_use_response = Mock()
        tool_use_response.stop_reason = "tool_use"

        # Create a mock content block for tool use
        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.id = "call_123"
        tool_use_block.name = "search_course_content"
        tool_use_block.input = {"query": "lesson content"}

        tool_use_response.content = [tool_use_block]

        # Tool manager returns empty results
        mock_tool_manager.execute_tool = Mock(
            return_value="No relevant content found."
        )

        # Final response from Claude after tool result
        final_response = Mock()
        final_text = Mock()
        final_text.text = "I couldn't find information about that."
        final_response.content = [final_text]

        # Mock Anthropic client to return these responses in sequence
        mock_anthropic_client.messages.create = Mock(
            side_effect=[tool_use_response, final_response]
        )

        # Generate response
        result = generator.generate_response(
            query="What's in lesson 1?",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager
        )

        # Assertions:
        # 1. Tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="lesson content"
        )

        # 2. Two API calls were made (initial + follow-up)
        assert mock_anthropic_client.messages.create.call_count == 2

        # 3. Final response returned
        assert result == "I couldn't find information about that."

    def test_ai_generator_direct_response_without_tools(self, mock_anthropic_client):
        """Verify AIGenerator returns direct response when no tool use occurs"""

        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        # Mock response without tool use
        direct_response = Mock()
        direct_response.stop_reason = "end_turn"
        direct_text = Mock()
        direct_text.text = "Hello! I can help with course questions."
        direct_response.content = [direct_text]

        mock_anthropic_client.messages.create = Mock(return_value=direct_response)

        result = generator.generate_response(query="Hi there")

        # Verify only one API call was made
        assert mock_anthropic_client.messages.create.call_count == 1

        # Verify direct response returned
        assert result == "Hello! I can help with course questions."

    def test_ai_generator_includes_conversation_history(self, mock_anthropic_client):
        """Verify AIGenerator includes conversation history in system prompt"""

        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        direct_response = Mock()
        direct_response.stop_reason = "end_turn"
        direct_text = Mock()
        direct_text.text = "Response"
        direct_response.content = [direct_text]

        mock_anthropic_client.messages.create = Mock(return_value=direct_response)

        conversation_history = "User: Previous question\nAssistant: Previous answer"
        generator.generate_response(
            query="New question",
            conversation_history=conversation_history
        )

        # Verify system prompt includes conversation history
        call_args = mock_anthropic_client.messages.create.call_args
        system_prompt = call_args.kwargs['system']
        assert "Previous conversation:" in system_prompt
        assert conversation_history in system_prompt

    def test_ai_generator_tool_execution_with_multiple_blocks(self, mock_anthropic_client, mock_tool_manager):
        """Verify AIGenerator handles tool results when there are multiple content blocks"""

        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        # Setup tool use response with multiple blocks
        tool_use_response = Mock()
        tool_use_response.stop_reason = "tool_use"

        # Text block + tool use block
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Let me search for that..."

        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.id = "call_456"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "test"}

        tool_use_response.content = [text_block, tool_block]

        # Mock tool execution
        mock_tool_manager.execute_tool = Mock(return_value="Search result")

        # Final response
        final_response = Mock()
        final_text = Mock()
        final_text.text = "Here's what I found"
        final_response.content = [final_text]

        mock_anthropic_client.messages.create = Mock(
            side_effect=[tool_use_response, final_response]
        )

        result = generator.generate_response(
            query="test",
            tools=mock_tool_manager.get_tool_definitions(),
            tool_manager=mock_tool_manager
        )

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once()

        # Verify final response returned
        assert result == "Here's what I found"

    def test_ai_generator_passes_tools_parameter_correctly(self, mock_anthropic_client):
        """Verify AIGenerator includes tools parameter in API call"""

        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        direct_response = Mock()
        direct_response.stop_reason = "end_turn"
        direct_text = Mock()
        direct_text.text = "Response"
        direct_response.content = [direct_text]

        mock_anthropic_client.messages.create = Mock(return_value=direct_response)

        tools = [{"name": "search_course_content", "description": "Search courses"}]
        generator.generate_response(query="test", tools=tools)

        # Verify tools parameter was passed
        call_args = mock_anthropic_client.messages.create.call_args
        assert call_args.kwargs['tools'] == tools
        assert call_args.kwargs['tool_choice'] == {"type": "auto"}

    def test_ai_generator_temperature_and_tokens_config(self, mock_anthropic_client):
        """Verify AIGenerator uses correct temperature and max_tokens"""

        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        direct_response = Mock()
        direct_response.stop_reason = "end_turn"
        direct_text = Mock()
        direct_text.text = "Response"
        direct_response.content = [direct_text]

        mock_anthropic_client.messages.create = Mock(return_value=direct_response)

        generator.generate_response(query="test")

        # Verify temperature and max_tokens
        call_args = mock_anthropic_client.messages.create.call_args
        assert call_args.kwargs['temperature'] == 0
        assert call_args.kwargs['max_tokens'] == 800
        assert call_args.kwargs['model'] == "test-model"


class TestAIGeneratorToolResultHandling:
    """Test cases for how AIGenerator handles different tool result scenarios"""

    def test_ai_generator_second_call_includes_tools(self, mock_anthropic_client, mock_tool_manager):
        """Verify second API call (after tool execution) DOES include tools parameter for multi-round support"""

        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        # First call with tool use
        tool_use_response = Mock()
        tool_use_response.stop_reason = "tool_use"

        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.id = "call_789"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "test"}

        tool_use_response.content = [tool_block]

        # Mock tool execution
        mock_tool_manager.execute_tool = Mock(return_value="Tool result")

        # Second call response (end turn - no more tool use)
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_text = Mock()
        final_text.text = "Final answer"
        final_response.content = [final_text]

        mock_anthropic_client.messages.create = Mock(
            side_effect=[tool_use_response, final_response]
        )

        generator.generate_response(
            query="test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Verify second call DOES include tools parameter (to allow for multi-round tool use)
        second_call_args = mock_anthropic_client.messages.create.call_args_list[1]
        assert 'tools' in second_call_args.kwargs
        assert second_call_args.kwargs['tools'] == [{"name": "search_course_content"}]

    def test_ai_generator_builds_message_history_correctly(self, mock_anthropic_client, mock_tool_manager):
        """Verify AIGenerator builds correct message history for tool execution"""

        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        # First call with tool use
        tool_use_response = Mock()
        tool_use_response.stop_reason = "tool_use"

        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.id = "call_abc"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "test"}

        tool_use_response.content = [tool_block]

        # Mock tool execution
        mock_tool_manager.execute_tool = Mock(return_value="Tool result text")

        # Second call response
        final_response = Mock()
        final_text = Mock()
        final_text.text = "Final answer"
        final_response.content = [final_text]

        mock_anthropic_client.messages.create = Mock(
            side_effect=[tool_use_response, final_response]
        )

        generator.generate_response(
            query="What is in the course?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Verify second call message structure
        second_call_args = mock_anthropic_client.messages.create.call_args_list[1]
        messages = second_call_args.kwargs['messages']

        # Should have 3 messages: user query, assistant tool use, user tool result
        assert len(messages) == 3

        # First message: user query
        assert messages[0]['role'] == 'user'

        # Second message: assistant's tool use decision
        assert messages[1]['role'] == 'assistant'

        # Third message: user providing tool results
        assert messages[2]['role'] == 'user'


class TestAIGeneratorMultiRoundToolExecution:
    """Test cases for 2-round sequential tool calling"""

    def test_two_rounds_of_tool_execution(self, mock_anthropic_client, mock_tool_manager):
        """Verify two sequential rounds of tool execution"""
        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        # Round 1: Tool use response
        round1_response = Mock()
        round1_response.stop_reason = "tool_use"

        tool_block_1 = Mock()
        tool_block_1.type = "tool_use"
        tool_block_1.id = "call_1"
        tool_block_1.name = "get_course_outline"
        tool_block_1.input = {"course_name": "MCP"}

        round1_response.content = [tool_block_1]

        # Round 2: Another tool use response
        round2_response = Mock()
        round2_response.stop_reason = "tool_use"

        tool_block_2 = Mock()
        tool_block_2.type = "tool_use"
        tool_block_2.id = "call_2"
        tool_block_2.name = "search_course_content"
        tool_block_2.input = {"query": "lesson 2"}

        round2_response.content = [tool_block_2]

        # Final response (no tool use)
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_text = Mock()
        final_text.text = "Lesson 1 covers basic and advanced concepts..."
        final_response.content = [final_text]

        # Setup mock to return responses in sequence
        mock_anthropic_client.messages.create = Mock(
            side_effect=[round1_response, round2_response, final_response]
        )

        # Setup tool manager
        mock_tool_manager.execute_tool = Mock(
            side_effect=["Course outline...", "Lesson 2 content..."]
        )

        # Execute
        result = generator.generate_response(
            query="What's in lesson 2 of MCP course?",
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Assertions:
        # 1. Three API calls made (Round 1, Round 2, Final)
        assert mock_anthropic_client.messages.create.call_count == 3

        # 2. Two tool executions
        assert mock_tool_manager.execute_tool.call_count == 2

        # 3. Correct tool names called
        calls = mock_tool_manager.execute_tool.call_args_list
        assert calls[0].kwargs.get("course_name") == "MCP"  # First tool: get_course_outline
        assert calls[1].kwargs.get("query") == "lesson 2"  # Second tool: search_course_content

        # 4. Message history built correctly
        # Check second API call has 3 messages (user, assistant, tool_result)
        second_call_messages = mock_anthropic_client.messages.create.call_args_list[1].kwargs['messages']
        assert len(second_call_messages) == 3

        # Check third API call has 5 messages (user, asst, tool_result, asst, tool_result)
        third_call_messages = mock_anthropic_client.messages.create.call_args_list[2].kwargs['messages']
        assert len(third_call_messages) == 5

        # 5. Final response returned
        assert result == "Lesson 1 covers basic and advanced concepts..."

    def test_stop_after_first_round_end_turn(self, mock_anthropic_client, mock_tool_manager):
        """Verify loop stops after first round if no tool use in response"""
        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        # Round 1: Tool use
        round1_response = Mock()
        round1_response.stop_reason = "tool_use"

        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.id = "call_1"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "lesson details"}

        round1_response.content = [tool_block]

        # Round 2: end_turn (no tool use)
        round2_response = Mock()
        round2_response.stop_reason = "end_turn"

        text_block = Mock()
        text_block.text = "Based on the search, here's the answer..."
        round2_response.content = [text_block]

        mock_anthropic_client.messages.create = Mock(
            side_effect=[round1_response, round2_response]
        )

        mock_tool_manager.execute_tool = Mock(return_value="Search results...")

        # Execute
        result = generator.generate_response(
            query="Test question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Assertions:
        # 1. Two API calls (Round 1 + Round 2 final)
        assert mock_anthropic_client.messages.create.call_count == 2

        # 2. One tool execution
        assert mock_tool_manager.execute_tool.call_count == 1

        # 3. Correct final response
        assert result == "Based on the search, here's the answer..."

    def test_max_rounds_limit_enforced(self, mock_anthropic_client, mock_tool_manager):
        """Verify max_rounds=2 limit is enforced"""
        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        # Round 1: Tool use
        round1_response = Mock()
        round1_response.stop_reason = "tool_use"

        tool_block_1 = Mock()
        tool_block_1.type = "tool_use"
        tool_block_1.id = "call_1"
        tool_block_1.name = "search_course_content"
        tool_block_1.input = {"query": "basic"}

        round1_response.content = [tool_block_1]

        # Round 2: Tool use again (would continue but we're at limit)
        round2_response = Mock()
        round2_response.stop_reason = "tool_use"

        tool_block_2 = Mock()
        tool_block_2.type = "tool_use"
        tool_block_2.id = "call_2"
        tool_block_2.name = "search_course_content"
        tool_block_2.input = {"query": "advanced"}

        round2_response.content = [tool_block_2]

        # Final response (made without tools after max rounds)
        final_response = Mock()
        final_response.stop_reason = "end_turn"

        final_text = Mock()
        final_text.text = "Here's my synthesis of the information..."
        final_response.content = [final_text]

        mock_anthropic_client.messages.create = Mock(
            side_effect=[round1_response, round2_response, final_response]
        )

        mock_tool_manager.execute_tool = Mock(
            side_effect=["Result 1", "Result 2"]
        )

        # Execute
        result = generator.generate_response(
            query="test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
            max_tool_rounds=2
        )

        # Assertions:
        # 1. Three API calls (Round 1, Round 2, Final without tools)
        assert mock_anthropic_client.messages.create.call_count == 3

        # 2. Two tool executions (one per round)
        assert mock_tool_manager.execute_tool.call_count == 2

        # 3. Final call should NOT have tools parameter
        final_call_args = mock_anthropic_client.messages.create.call_args_list[2]
        assert 'tools' not in final_call_args.kwargs

        # 4. Response returned
        assert result == "Here's my synthesis of the information..."

    def test_tool_execution_error_stops_loop(self, mock_anthropic_client, mock_tool_manager):
        """Verify tool execution error prevents further rounds"""
        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        # Round 1: Tool use
        round1_response = Mock()
        round1_response.stop_reason = "tool_use"

        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.id = "call_1"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "test"}

        # Add text content so _extract_response_text works
        text_block = Mock()
        text_block.text = "Let me search for that..."

        round1_response.content = [text_block, tool_block]

        mock_anthropic_client.messages.create = Mock(return_value=round1_response)

        # Tool execution raises exception
        mock_tool_manager.execute_tool = Mock(
            side_effect=Exception("Database connection failed")
        )

        # Execute
        result = generator.generate_response(
            query="test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Assertions:
        # 1. Only one API call (error stops the loop)
        assert mock_anthropic_client.messages.create.call_count == 1

        # 2. Tool execution was attempted
        assert mock_tool_manager.execute_tool.call_count == 1

        # 3. Response is from the first round (extracted text)
        assert result == "Let me search for that..."

    def test_no_tool_use_direct_response(self, mock_anthropic_client):
        """Verify direct response when Claude doesn't use tools"""
        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        direct_response = Mock()
        direct_response.stop_reason = "end_turn"

        text_block = Mock()
        text_block.text = "I can answer that directly..."
        direct_response.content = [text_block]

        mock_anthropic_client.messages.create = Mock(return_value=direct_response)

        result = generator.generate_response(
            query="Simple question",
            tools=[{"name": "search_course_content"}],
            tool_manager=Mock()
        )

        # Assertions:
        # 1. Single API call
        assert mock_anthropic_client.messages.create.call_count == 1

        # 2. Response returned
        assert result == "I can answer that directly..."

    def test_message_history_accumulates_correctly(self, mock_anthropic_client, mock_tool_manager):
        """Verify message history grows correctly across rounds"""
        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        # Setup same as test_two_rounds_of_tool_execution
        round1_response = Mock()
        round1_response.stop_reason = "tool_use"
        tool_block_1 = Mock()
        tool_block_1.type = "tool_use"
        tool_block_1.id = "call_1"
        tool_block_1.name = "search_course_content"
        tool_block_1.input = {"query": "test1"}
        round1_response.content = [tool_block_1]

        round2_response = Mock()
        round2_response.stop_reason = "tool_use"
        tool_block_2 = Mock()
        tool_block_2.type = "tool_use"
        tool_block_2.id = "call_2"
        tool_block_2.name = "search_course_content"
        tool_block_2.input = {"query": "test2"}
        round2_response.content = [tool_block_2]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_text = Mock()
        final_text.text = "Final answer"
        final_response.content = [final_text]

        mock_anthropic_client.messages.create = Mock(
            side_effect=[round1_response, round2_response, final_response]
        )

        mock_tool_manager.execute_tool = Mock(
            side_effect=["Result 1", "Result 2"]
        )

        # Execute
        generator.generate_response(
            query="Test question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Check message counts at each call
        first_call_msgs = mock_anthropic_client.messages.create.call_args_list[0].kwargs['messages']
        assert len(first_call_msgs) == 1
        assert first_call_msgs[0]['role'] == 'user'

        second_call_msgs = mock_anthropic_client.messages.create.call_args_list[1].kwargs['messages']
        assert len(second_call_msgs) == 3
        assert second_call_msgs[0]['role'] == 'user'
        assert second_call_msgs[1]['role'] == 'assistant'
        assert second_call_msgs[2]['role'] == 'user'

        third_call_msgs = mock_anthropic_client.messages.create.call_args_list[2].kwargs['messages']
        assert len(third_call_msgs) == 5
        assert third_call_msgs[0]['role'] == 'user'
        assert third_call_msgs[1]['role'] == 'assistant'
        assert third_call_msgs[2]['role'] == 'user'
        assert third_call_msgs[3]['role'] == 'assistant'
        assert third_call_msgs[4]['role'] == 'user'

    def test_tools_parameter_included_in_all_rounds(self, mock_anthropic_client, mock_tool_manager):
        """Verify tools are available in both Round 1 and Round 2"""
        generator = AIGenerator(api_key="test-key", model="test-model")
        generator.client = mock_anthropic_client

        round1_response = Mock()
        round1_response.stop_reason = "tool_use"
        tool_block_1 = Mock()
        tool_block_1.type = "tool_use"
        tool_block_1.id = "call_1"
        tool_block_1.name = "search_course_content"
        tool_block_1.input = {"query": "test"}
        round1_response.content = [tool_block_1]

        round2_response = Mock()
        round2_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.text = "Answer"
        round2_response.content = [text_block]

        mock_anthropic_client.messages.create = Mock(
            side_effect=[round1_response, round2_response]
        )

        mock_tool_manager.execute_tool = Mock(return_value="Result")

        tools = [{"name": "search_course_content"}]
        generator.generate_response(
            query="test",
            tools=tools,
            tool_manager=mock_tool_manager
        )

        # Both Round 1 and Round 2 should have tools parameter
        for i in range(2):
            call_kwargs = mock_anthropic_client.messages.create.call_args_list[i].kwargs
            assert 'tools' in call_kwargs
            assert call_kwargs['tool_choice'] == {"type": "auto"}
