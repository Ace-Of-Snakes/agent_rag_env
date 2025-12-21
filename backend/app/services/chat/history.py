"""
Chat history manager for context window management.
"""

from typing import Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm.text import text_service

logger = get_logger(__name__)


class HistoryManager:
    """
    Manages conversation history for LLM context.
    
    Handles:
    - Token counting and limiting
    - Conversation summarization
    - Rolling context windows
    """
    
    def __init__(self):
        self._settings = get_settings()
    
    @property
    def max_history_tokens(self) -> int:
        """Maximum tokens for history context."""
        return self._settings.performance.max_history_tokens
    
    @property
    def summarize_threshold(self) -> int:
        """Number of messages after which to summarize."""
        return self._settings.performance.summarize_after_messages
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: ~4 chars per token)."""
        return len(text) // 4
    
    def estimate_history_tokens(self, history: List[Dict[str, str]]) -> int:
        """Estimate total tokens in conversation history."""
        return sum(
            self.estimate_tokens(msg.get("content", ""))
            for msg in history
        )
    
    async def prepare_context(
        self,
        history: List[Dict[str, str]],
        system_context: Optional[str] = None
    ) -> tuple[List[Dict[str, str]], bool, Optional[str]]:
        """
        Prepare conversation history for LLM context.
        
        Args:
            history: Full conversation history
            system_context: Additional context (e.g., RAG results)
            
        Returns:
            Tuple of (prepared_history, was_truncated, summary_if_used)
        """
        # Estimate current token count
        total_tokens = self.estimate_history_tokens(history)
        
        if system_context:
            total_tokens += self.estimate_tokens(system_context)
        
        # If within limits, return as-is
        if total_tokens <= self.max_history_tokens:
            return history, False, None
        
        # If history is long, summarize older messages
        if len(history) > self.summarize_threshold:
            return await self._summarize_and_truncate(history, system_context)
        
        # Otherwise, just truncate from the beginning
        return self._truncate_history(history, system_context), True, None
    
    async def _summarize_and_truncate(
        self,
        history: List[Dict[str, str]],
        system_context: Optional[str] = None
    ) -> tuple[List[Dict[str, str]], bool, str]:
        """Summarize older messages and keep recent ones."""
        # Keep last N messages intact
        keep_count = self.summarize_threshold // 2
        
        old_messages = history[:-keep_count]
        recent_messages = history[-keep_count:]
        
        # Summarize old messages
        summary = await text_service.summarize_conversation(old_messages)
        
        # Create summary message
        summary_message = {
            "role": "system",
            "content": f"[Previous conversation summary: {summary}]"
        }
        
        # Build new history
        new_history = [summary_message] + recent_messages
        
        # Check if still too long
        total_tokens = self.estimate_history_tokens(new_history)
        if system_context:
            total_tokens += self.estimate_tokens(system_context)
        
        if total_tokens > self.max_history_tokens:
            # Further truncate recent messages
            new_history = self._truncate_history(new_history, system_context)
        
        logger.info(
            "History summarized",
            original_count=len(history),
            new_count=len(new_history),
            summary_length=len(summary)
        )
        
        return new_history, True, summary
    
    def _truncate_history(
        self,
        history: List[Dict[str, str]],
        system_context: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Truncate history to fit within token limit."""
        system_tokens = self.estimate_tokens(system_context) if system_context else 0
        available_tokens = self.max_history_tokens - system_tokens
        
        # Work backwards from most recent
        truncated = []
        current_tokens = 0
        
        for msg in reversed(history):
            msg_tokens = self.estimate_tokens(msg.get("content", ""))
            
            if current_tokens + msg_tokens > available_tokens:
                break
            
            truncated.insert(0, msg)
            current_tokens += msg_tokens
        
        logger.debug(
            "History truncated",
            original_count=len(history),
            truncated_count=len(truncated),
            tokens=current_tokens
        )
        
        return truncated
    
    def format_rag_context(
        self,
        results: List[dict],
        max_tokens: int = 1500
    ) -> str:
        """
        Format RAG search results as context.
        
        Args:
            results: Search results with content and metadata
            max_tokens: Maximum tokens for context
            
        Returns:
            Formatted context string
        """
        if not results:
            return ""
        
        context_parts = ["Relevant information from documents:\n"]
        current_tokens = self.estimate_tokens(context_parts[0])
        
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            filename = result.get("document_filename", "Unknown")
            page = result.get("page_number")
            
            # Format citation
            citation = f"[{filename}"
            if page:
                citation += f", p.{page}"
            citation += "]"
            
            chunk_text = f"\n{i}. {citation}\n{content}\n"
            chunk_tokens = self.estimate_tokens(chunk_text)
            
            if current_tokens + chunk_tokens > max_tokens:
                break
            
            context_parts.append(chunk_text)
            current_tokens += chunk_tokens
        
        return "".join(context_parts)


# Singleton instance
history_manager = HistoryManager()
