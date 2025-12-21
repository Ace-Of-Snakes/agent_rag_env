"""
Agent orchestrator that manages tool execution and response generation.
"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.config import get_settings
from app.core.constants import AgentConstants, APIConstants
from app.core.exceptions import MaxIterationsExceededError, ToolExecutionError
from app.core.logging import get_logger
from app.agents.prompts import build_agent_prompt, build_tool_result_prompt
from app.agents.tools import tool_registry
from app.agents.tools.base import ToolResult
from app.services.chat.history import history_manager
from app.services.llm.text import text_service

logger = get_logger(__name__)


@dataclass
class AgentThought:
    """A single thought/action step from the agent."""
    
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    response: Optional[str] = None


@dataclass
class StreamEvent:
    """Event emitted during agent execution."""
    
    event: str  # thought, tool_start, tool_end, token, done, error
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Complete response from agent execution."""
    
    response: str
    thoughts: List[AgentThought] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    total_iterations: int = 0
    execution_time_ms: float = 0


class AgentOrchestrator:
    """
    Orchestrates the agent's reasoning and tool execution loop.
    
    Flow:
    1. Receive user message and conversation history
    2. Build context with RAG results if relevant
    3. Enter think-act loop:
       a. LLM decides next action
       b. Execute tool if needed
       c. Feed result back to LLM
       d. Repeat until response or max iterations
    4. Return final response with sources
    """
    
    def __init__(self):
        self._settings = get_settings()
        self._max_iterations = AgentConstants.MAX_TOOL_ITERATIONS
    
    async def process_message(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        attached_files: Optional[List[Dict[str, Any]]] = None
    ) -> AgentResponse:
        """
        Process a user message and return the agent's response.
        
        Args:
            user_message: The user's message
            conversation_history: Previous messages in the conversation
            attached_files: Any files attached to the message
            
        Returns:
            AgentResponse with final response and metadata
        """
        start_time = time.time()
        
        # Get available tools
        tools = tool_registry.get_all_definitions()
        
        # Build system prompt with tools
        system_prompt = build_agent_prompt([t.__dict__ for t in tools])
        
        # Prepare context (may truncate or summarize history)
        prepared_history, _, _ = await history_manager.prepare_context(
            conversation_history
        )
        
        # Add user message
        messages = prepared_history + [{"role": "user", "content": user_message}]
        
        thoughts = []
        tool_results = []
        sources = []
        
        # Think-act loop
        for iteration in range(self._max_iterations):
            logger.debug(
                "Agent iteration",
                iteration=iteration + 1,
                max=self._max_iterations
            )
            
            # Get LLM response
            response_text = await text_service.chat(
                messages=messages,
                system_prompt=system_prompt
            )
            
            # Parse the response
            thought = self._parse_response(response_text)
            thoughts.append(thought)
            
            # Check if agent wants to respond directly
            if thought.action == "respond" or thought.response:
                final_response = thought.response or response_text
                
                execution_time = (time.time() - start_time) * 1000
                
                return AgentResponse(
                    response=final_response,
                    thoughts=thoughts,
                    tool_results=tool_results,
                    sources=sources,
                    total_iterations=iteration + 1,
                    execution_time_ms=execution_time
                )
            
            # Execute tool if specified
            if thought.action and thought.action != "respond":
                try:
                    result = await self._execute_tool(
                        thought.action,
                        thought.action_input or {}
                    )
                    
                    tool_results.append({
                        "tool": thought.action,
                        "input": thought.action_input,
                        "result": result.result if result.success else result.error,
                        "success": result.success
                    })
                    
                    # Collect sources from RAG results
                    if thought.action == AgentConstants.TOOL_RAG_SEARCH and result.success:
                        sources.extend(self._extract_sources(result.result))
                    
                    # Add tool result to conversation
                    tool_message = build_tool_result_prompt(
                        thought.action,
                        json.dumps(result.result) if result.success else result.error
                    )
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({"role": "user", "content": tool_message})
                    
                except Exception as e:
                    logger.error(
                        "Tool execution failed",
                        tool=thought.action,
                        error=str(e)
                    )
                    # Continue with error message
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({
                        "role": "user",
                        "content": f"Tool '{thought.action}' failed: {str(e)}. Please try a different approach or respond without the tool."
                    })
        
        # Max iterations reached
        raise MaxIterationsExceededError(self._max_iterations)
    
    async def process_message_stream(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        attached_files: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Process a message with streaming events.
        
        Yields:
            StreamEvent objects for each step
        """
        start_time = time.time()
        
        tools = tool_registry.get_all_definitions()
        system_prompt = build_agent_prompt([t.__dict__ for t in tools])
        
        prepared_history, _, _ = await history_manager.prepare_context(
            conversation_history
        )
        messages = prepared_history + [{"role": "user", "content": user_message}]
        
        sources = []
        
        for iteration in range(self._max_iterations):
            # Get streaming response
            response_chunks = []
            
            async for token in text_service.chat_stream(
                messages=messages,
                system_prompt=system_prompt
            ):
                response_chunks.append(token)
                yield StreamEvent(
                    event=APIConstants.SSE_EVENT_MESSAGE,
                    data={"token": token, "iteration": iteration}
                )
            
            response_text = "".join(response_chunks)
            thought = self._parse_response(response_text)
            
            yield StreamEvent(
                event="thought",
                data={"thought": thought.thought, "action": thought.action}
            )
            
            # Direct response
            if thought.action == "respond" or thought.response:
                yield StreamEvent(
                    event=APIConstants.SSE_EVENT_DONE,
                    data={
                        "response": thought.response or response_text,
                        "sources": sources,
                        "iterations": iteration + 1,
                        "execution_time_ms": (time.time() - start_time) * 1000
                    }
                )
                return
            
            # Execute tool
            if thought.action:
                yield StreamEvent(
                    event=APIConstants.SSE_EVENT_TOOL_START,
                    data={"tool": thought.action, "input": thought.action_input}
                )
                
                try:
                    result = await self._execute_tool(
                        thought.action,
                        thought.action_input or {}
                    )
                    
                    yield StreamEvent(
                        event=APIConstants.SSE_EVENT_TOOL_END,
                        data={
                            "tool": thought.action,
                            "success": result.success,
                            "result_preview": str(result.result)[:200] if result.success else result.error
                        }
                    )
                    
                    if thought.action == AgentConstants.TOOL_RAG_SEARCH and result.success:
                        sources.extend(self._extract_sources(result.result))
                    
                    tool_message = build_tool_result_prompt(
                        thought.action,
                        json.dumps(result.result) if result.success else result.error
                    )
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({"role": "user", "content": tool_message})
                    
                except Exception as e:
                    yield StreamEvent(
                        event=APIConstants.SSE_EVENT_ERROR,
                        data={"tool": thought.action, "error": str(e)}
                    )
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({
                        "role": "user",
                        "content": f"Tool failed: {str(e)}. Try another approach."
                    })
        
        yield StreamEvent(
            event=APIConstants.SSE_EVENT_ERROR,
            data={"error": "Maximum iterations exceeded"}
        )
    
    async def _execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> ToolResult:
        """Execute a tool by name."""
        tool = tool_registry.get_tool(tool_name)
        
        start_time = time.time()
        result = await tool.execute(params)
        result.execution_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            "Tool executed",
            tool=tool_name,
            success=result.success,
            execution_time_ms=result.execution_time_ms
        )
        
        return result
    
    def _parse_response(self, response_text: str) -> AgentThought:
        """
        Parse LLM response to extract thought and action.
        
        Handles:
        - JSON formatted responses
        - Plain text responses
        - Malformed responses
        """
        # Try to find JSON in response
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return AgentThought(
                    thought=data.get("thought", ""),
                    action=data.get("action"),
                    action_input=data.get("action_input"),
                    response=data.get("response")
                )
            except json.JSONDecodeError:
                pass
        
        # Try parsing as plain JSON
        try:
            data = json.loads(response_text)
            return AgentThought(
                thought=data.get("thought", ""),
                action=data.get("action"),
                action_input=data.get("action_input"),
                response=data.get("response")
            )
        except json.JSONDecodeError:
            pass
        
        # Treat as direct response
        return AgentThought(
            thought="Responding directly",
            action="respond",
            response=response_text
        )
    
    def _extract_sources(self, rag_result: Any) -> List[Dict[str, Any]]:
        """Extract source citations from RAG results."""
        sources = []
        
        if isinstance(rag_result, dict) and "results" in rag_result:
            for r in rag_result["results"]:
                sources.append({
                    "document": r.get("document_filename", "Unknown"),
                    "page": r.get("page_number"),
                    "content_preview": r.get("content", "")[:100]
                })
        
        return sources


# Singleton instance
agent_orchestrator = AgentOrchestrator()
