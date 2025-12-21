"""
Text LLM service for summarization and chat.
"""

from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm.client import ollama_client

logger = get_logger(__name__)

# System prompts
SUMMARIZATION_SYSTEM_PROMPT = """You are an expert at summarizing documents.
Create concise but comprehensive summaries that capture:
- Main topics and themes
- Key findings or arguments
- Important details and data points
- Overall purpose of the document

Your summaries should be useful for searching and understanding the document's content."""

CHAT_SYSTEM_PROMPT = """You are a helpful AI assistant with access to a knowledge base of documents.
When answering questions:
- Draw on relevant information from the provided context
- Be accurate and cite sources when possible
- Acknowledge when you don't have enough information
- Be conversational but informative"""


class TextService:
    """Service for text model operations."""
    
    def __init__(self):
        self._settings = get_settings()
    
    @property
    def model(self) -> str:
        """Get the text model name."""
        return self._settings.ollama.text_model
    
    async def summarize(
        self,
        text: str,
        max_length: Optional[int] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Summarize a piece of text.
        
        Args:
            text: Text to summarize
            max_length: Target summary length in words
            context: Additional context about the text
            
        Returns:
            Summary of the text
        """
        prompt = "Summarize the following text:\n\n"
        
        if context:
            prompt = f"Context: {context}\n\n{prompt}"
        
        prompt += text
        
        if max_length:
            prompt += f"\n\nKeep the summary under {max_length} words."
        
        response = await ollama_client.generate(
            model=self.model,
            prompt=prompt,
            system=SUMMARIZATION_SYSTEM_PROMPT,
            temperature=0.3,
        )
        
        logger.debug("Text summarized", input_length=len(text), output_length=len(response))
        return response
    
    async def summarize_document(
        self,
        chunks: List[str],
        filename: str
    ) -> str:
        """
        Create a document-level summary from chunks.
        
        Args:
            chunks: List of document chunks
            filename: Document filename for context
            
        Returns:
            Document summary
        """
        # Combine chunks with separators
        combined = "\n\n---\n\n".join(chunks[:10])  # Limit to first 10 chunks
        
        prompt = f"""Create a comprehensive summary of this document: "{filename}"

Document content:
{combined}

Provide a summary that covers:
1. The main topic and purpose
2. Key points and findings
3. Notable details or data

The summary should be useful for searching and understanding what this document contains."""
        
        response = await ollama_client.generate(
            model=self.model,
            prompt=prompt,
            system=SUMMARIZATION_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=500,
        )
        
        return response
    
    async def summarize_conversation(
        self,
        messages: List[Dict[str, str]]
    ) -> str:
        """
        Summarize a conversation for context management.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Conversation summary
        """
        conversation_text = "\n".join(
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in messages
        )
        
        prompt = f"""Summarize this conversation, preserving key information and context:

{conversation_text}

Provide a concise summary that captures:
- Main topics discussed
- Key decisions or conclusions
- Important details the user mentioned
- Any pending questions or tasks"""
        
        response = await ollama_client.generate(
            model=self.model,
            prompt=prompt,
            system="You are a conversation summarizer. Create concise summaries that preserve important context.",
            temperature=0.3,
            max_tokens=300,
        )
        
        return response
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        stream: bool = False
    ) -> str | AsyncGenerator[str, None]:
        """
        Generate a chat response.
        
        Args:
            messages: Conversation history
            system_prompt: Custom system prompt
            context: Additional context (e.g., RAG results)
            stream: Whether to stream the response
            
        Returns:
            Response text or async generator for streaming
        """
        system = system_prompt or CHAT_SYSTEM_PROMPT
        
        if context:
            system += f"\n\nRelevant context:\n{context}"
        
        return await ollama_client.chat(
            model=self.model,
            messages=messages,
            system=system,
            stream=stream,
        )
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat response.
        
        Args:
            messages: Conversation history
            system_prompt: Custom system prompt
            context: Additional context
            
        Yields:
            Response tokens
        """
        response = await self.chat(
            messages=messages,
            system_prompt=system_prompt,
            context=context,
            stream=True,
        )
        
        async for token in response:
            yield token
    
    async def generate_title(
        self,
        first_message: str
    ) -> str:
        """
        Generate a title for a conversation.
        
        Args:
            first_message: First user message
            
        Returns:
            Short title for the conversation
        """
        prompt = f"""Generate a very short title (3-6 words) for a conversation that starts with this message:

"{first_message}"

Respond with only the title, nothing else."""
        
        response = await ollama_client.generate(
            model=self.model,
            prompt=prompt,
            temperature=0.7,
            max_tokens=20,
        )
        
        # Clean up the response
        title = response.strip().strip('"').strip("'")
        return title[:100]  # Limit length


# Singleton instance
text_service = TextService()
