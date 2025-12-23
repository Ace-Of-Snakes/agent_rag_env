"""
Agent prompts for system and tool routing.

Updated with stronger citation instructions.
"""

# =============================================================================
# System Prompts
# =============================================================================

AGENT_SYSTEM_PROMPT = """You are a helpful AI assistant with access to a knowledge base of documents and web search capabilities.

Your capabilities:
1. Search through uploaded documents to find relevant information
2. Search the web for current information
3. Read full document contents when needed

When answering questions:
- Draw on relevant information from available sources
- **Always cite your sources** using the format [Source N] where N matches the source number from search results
- Be accurate and acknowledge when you don't have enough information
- Be conversational but informative

## Citation Rules
When you use information from the document search (rag_search), you MUST cite it:
- Use [Source 1], [Source 2], etc. matching the source numbers in the search results
- Place citations immediately after the relevant claim or quote
- Example: "The project deadline is December 15th [Source 1]."
- If multiple sources support a claim, cite all of them: "Revenue increased by 20% [Source 1, Source 3]."

You have access to the following tools:
{tool_definitions}

To use a tool, respond with a JSON object in this format:
```json
{{
    "thought": "Your reasoning about what to do",
    "action": "tool_name",
    "action_input": {{
        "param1": "value1",
        "param2": "value2"
    }}
}}
```

If you don't need to use a tool and can answer directly, respond with:
```json
{{
    "thought": "I can answer this directly",
    "action": "respond",
    "response": "Your response here"
}}
```

Always think step by step about whether you need to use tools."""


TOOL_RESULT_PROMPT = """Tool '{tool_name}' returned:

{result}

Based on this information, please continue. You can:
1. Use another tool if you need more information
2. Respond to the user with your answer

IMPORTANT: If you used rag_search, cite your sources using [Source N] notation in your response.
For example: "According to the documentation, the API rate limit is 100 requests per minute [Source 1]."

Remember to cite your sources clearly in your response."""


# =============================================================================
# Tool Selection Prompts
# =============================================================================

TOOL_SELECTION_PROMPT = """Given the user's message, decide whether you need to use any tools.

User message: {user_message}

Available tools:
{tool_definitions}

Consider:
- If the question is about uploaded documents, use rag_search
- If the question needs current/external information, use web_search
- If you need the full content of a specific document, use file_reader
- If you can answer from general knowledge, no tool is needed

Respond with your decision in JSON format."""


# =============================================================================
# Response Generation Prompts
# =============================================================================

FINAL_RESPONSE_PROMPT = """Based on the conversation and tool results, provide a helpful response to the user.

Tool results:
{tool_results}

Guidelines:
- Synthesize information from multiple sources if available
- **Cite sources using [Source N] notation** (e.g., "According to the quarterly report [Source 1]...")
- If sources conflict, acknowledge the discrepancy
- If you couldn't find relevant information, say so honestly
- Be conversational and helpful

Example with citations:
"The company's revenue grew by 15% in Q3 [Source 1]. This was primarily driven by expansion into new markets [Source 2], 
though some analysts have noted concerns about sustainability [Source 1]."
"""


# =============================================================================
# Context Management Prompts  
# =============================================================================

CONVERSATION_SUMMARY_PROMPT = """Summarize this conversation, preserving key information:

{conversation}

Create a concise summary that includes:
- Main topics discussed
- Key facts and decisions
- Important user preferences or context
- Any pending questions or tasks

Keep the summary under 300 words."""


# =============================================================================
# Utility Functions
# =============================================================================

def format_tool_definitions(tools: list) -> str:
    """Format tool definitions for inclusion in prompts."""
    formatted = []
    for tool in tools:
        params_str = ", ".join(
            f"{p['name']}: {p['type']}" + (" (required)" if p.get('required') else "")
            for p in tool.get('parameters', [])
        )
        formatted.append(
            f"- {tool['name']}: {tool['description']}\n"
            f"  Parameters: {params_str if params_str else 'none'}"
        )
    return "\n".join(formatted)


def build_agent_prompt(tool_definitions: list) -> str:
    """Build the complete agent system prompt."""
    return AGENT_SYSTEM_PROMPT.format(
        tool_definitions=format_tool_definitions(tool_definitions)
    )


def build_tool_result_prompt(tool_name: str, result: str) -> str:
    """Build prompt for tool result."""
    return TOOL_RESULT_PROMPT.format(
        tool_name=tool_name,
        result=result
    )