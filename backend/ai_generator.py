import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Available Tools:
1. **get_course_outline**: Use for questions about course structure, outline, or what lessons/topics are covered in a course
   - Returns: Course title, course link, instructor, and complete list of lessons with their numbers and titles
   - Use when asked about: "What is the outline?", "What lessons are in X?", "What topics are covered?", "Course structure"

2. **search_course_content**: Use for questions about specific course content or detailed educational materials
   - Returns: Relevant content chunks from course materials
   - Use when asked about: Specific concepts, detailed explanations, lesson content, what is taught in a particular lesson

Tool Usage Guidelines:
- **Up to two sequential tool calls are supported** - You can call tools twice per query if needed
- **Each tool call is a separate step**: After your first tool call, you'll receive the results. You can then decide if a second search is needed
- **Reasoning between calls**: Use the results from the first search to refine your second search query if needed
- **Use sequentially, not in parallel**: Make one tool call at a time; after receiving results, make another if needed
- **Combine results**: Synthesize results from both rounds (if used) into a cohesive answer
- **Stop when you have enough information**: Don't call tools if you already have sufficient information from the first call
- Choose the most appropriate tool based on the question type
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course outline/structure questions**: Use get_course_outline tool first, then answer
- **Course content questions**: Use search_course_content tool first, then answer
- **Multi-part questions**: Use first search for initial information, second search for details if needed
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the outline tool"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None,
                         max_tool_rounds: int = 2) -> str:
        """
        Generate AI response with up to 2 sequential tool calling rounds.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_tool_rounds: Maximum number of sequential tool rounds (default: 2)

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Prepare initial API call parameters
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Execute with tool loop (supports up to max_tool_rounds)
        if tools and tool_manager:
            return self._execute_with_tool_loop(api_params, tool_manager, max_tool_rounds)

        # No tools available - make single API call
        response = self.client.messages.create(**api_params)
        return self._extract_response_text(response)

    def _execute_with_tool_loop(self, api_params: Dict[str, Any], tool_manager, max_rounds: int) -> str:
        """
        Execute query with iterative tool calling up to max_rounds times.

        Args:
            api_params: Initial API parameters with messages, system, tools
            tool_manager: Manager to execute tools
            max_rounds: Maximum number of tool rounds (default: 2)

        Returns:
            Final response text after all rounds complete or termination condition met
        """
        messages = api_params["messages"].copy()
        round_count = 0

        while round_count < max_rounds:
            # Prepare params for this round
            current_params = {
                **api_params,
                "messages": messages
            }

            # API call for this round
            response = self.client.messages.create(**current_params)
            round_count += 1

            # Check if Claude wants to use tools
            if response.stop_reason != "tool_use":
                # No tool use - return response directly
                return self._extract_response_text(response)

            # Execute tools for this round
            tool_results = self._execute_tools_from_response(response, tool_manager)

            if not tool_results:
                # Tool execution failed or no tools found
                return self._extract_response_text(response)

            # Build message history for next round
            messages = self._build_message_for_next_round(messages, response, tool_results)

            # If we've hit max rounds after this tool execution, make final call
            if round_count >= max_rounds:
                final_params = {
                    **self.base_params,
                    "messages": messages,
                    "system": api_params["system"]
                }
                final_response = self.client.messages.create(**final_params)
                return self._extract_response_text(final_response)

        # This shouldn't be reached, but return empty string as fallback
        return ""

    def _should_continue_tool_loop(self, response, round_count: int, max_rounds: int) -> bool:
        """
        Determine if tool loop should continue to next round.

        Args:
            response: API response from current round
            round_count: Current round number (1-indexed)
            max_rounds: Maximum rounds allowed

        Returns:
            True if loop should continue, False to terminate
        """
        # Check if we've hit max rounds
        if round_count >= max_rounds:
            return False

        # Check if Claude requested tool use
        if response.stop_reason != "tool_use":
            return False

        # Check if response has tool_use blocks
        has_tool_use = any(
            hasattr(block, 'type') and block.type == "tool_use"
            for block in response.content
        )

        return has_tool_use

    def _execute_tools_from_response(self, response, tool_manager) -> List[Dict]:
        """
        Execute all tool calls from response.

        Args:
            response: API response containing tool use requests
            tool_manager: Manager to execute tools

        Returns:
            List of tool_result dicts, or empty list if error/no tools
        """
        tool_results = []

        for content_block in response.content:
            if not hasattr(content_block, 'type'):
                continue

            if content_block.type != "tool_use":
                continue

            try:
                # Execute the tool
                tool_result = tool_manager.execute_tool(
                    content_block.name,
                    **content_block.input
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })

            except Exception as e:
                # Log error and return empty (signals termination)
                import logging
                logging.getLogger(__name__).error(
                    f"Failed to execute tool '{content_block.name}': {str(e)}",
                    exc_info=True
                )
                return []

        return tool_results

    def _build_message_for_next_round(self, current_messages: List[Dict],
                                      assistant_response,
                                      tool_results: List[Dict]) -> List[Dict]:
        """
        Build message history for the next round.

        Args:
            current_messages: Messages from before this round
            assistant_response: The assistant's response with tool use
            tool_results: Executed tool results

        Returns:
            New messages list for next API call
        """
        new_messages = current_messages.copy()

        # Add assistant's tool use decision
        new_messages.append({
            "role": "assistant",
            "content": assistant_response.content
        })

        # Add tool results as user message
        if tool_results:
            new_messages.append({
                "role": "user",
                "content": tool_results
            })

        return new_messages

    def _extract_response_text(self, response) -> str:
        """
        Safely extract text from response.

        Args:
            response: API response object

        Returns:
            Extracted text or empty string if not found
        """
        try:
            for content_block in response.content:
                if hasattr(content_block, 'text'):
                    return content_block.text

            # Fallback: try first content block
            if hasattr(response.content[0], 'text'):
                return response.content[0].text

            return ""

        except (IndexError, AttributeError):
            return ""

    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        DEPRECATED: Handle execution of tool calls and get follow-up response.

        This method is kept for backward compatibility but is no longer used.
        Use _execute_with_tool_loop() instead for multi-round tool calling support.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})
        
        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name, 
                    **content_block.input
                )
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })
        
        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        
        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }
        
        # Get final response
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text