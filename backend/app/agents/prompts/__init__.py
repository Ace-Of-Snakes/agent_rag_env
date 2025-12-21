"""
Agent prompts for system behavior and tool routing.
"""

from app.agents.prompts.system import (
    AGENT_SYSTEM_PROMPT,
    CONVERSATION_SUMMARY_PROMPT,
    FINAL_RESPONSE_PROMPT,
    TOOL_RESULT_PROMPT,
    TOOL_SELECTION_PROMPT,
    build_agent_prompt,
    build_tool_result_prompt,
    format_tool_definitions,
)

__all__ = [
    "AGENT_SYSTEM_PROMPT",
    "TOOL_RESULT_PROMPT",
    "TOOL_SELECTION_PROMPT",
    "FINAL_RESPONSE_PROMPT",
    "CONVERSATION_SUMMARY_PROMPT",
    "format_tool_definitions",
    "build_agent_prompt",
    "build_tool_result_prompt",
]