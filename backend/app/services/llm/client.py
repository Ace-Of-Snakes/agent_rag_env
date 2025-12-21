"""
Ollama client wrapper for LLM operations.
"""

from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.core.constants import LLMConstants
from app.core.exceptions import (
    EmbeddingError,
    GenerationError,
    ModelNotFoundError,
    OllamaConnectionError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class OllamaClient:
    """Async client for Ollama API."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = LLMConstants.GENERATION_TIMEOUT
    ):
        self._settings = get_settings()
        self._base_url = base_url or self._settings.ollama.base_url
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self._timeout),
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    async def health_check(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except httpx.RequestError:
            return False
    
    async def list_models(self) -> List[str]:
        """List available models."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except httpx.RequestError as e:
            raise OllamaConnectionError(self._base_url, str(e))
    
    async def ensure_model(self, model_name: str) -> bool:
        """
        Ensure a model is available.
        
        Returns:
            True if model is available
            
        Raises:
            ModelNotFoundError: If model is not available
        """
        models = await self.list_models()
        # Check for exact match or partial match (e.g., "qwen2-vl:7b" in "qwen2-vl:7b-instruct-q4_K_M")
        for available in models:
            if model_name in available or available in model_name:
                return True
        raise ModelNotFoundError(model_name)
    
    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs: Any
    ) -> str | AsyncGenerator[str, None]:
        """
        Generate text completion.
        
        Args:
            model: Model name
            prompt: User prompt
            system: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters
            
        Returns:
            Generated text or async generator for streaming
        """
        settings = self._settings.ollama
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature or settings.temperature,
                "top_p": settings.top_p,
                "num_predict": max_tokens or settings.max_tokens,
            },
            "keep_alive": settings.keep_alive,
        }
        
        if system:
            payload["system"] = system
        
        payload.update(kwargs)
        
        if stream:
            return self._stream_generate(payload)
        else:
            return await self._sync_generate(payload)
    
    async def _sync_generate(self, payload: Dict[str, Any]) -> str:
        """Synchronous generation."""
        try:
            client = await self._get_client()
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except httpx.RequestError as e:
            raise OllamaConnectionError(self._base_url, str(e))
        except httpx.HTTPStatusError as e:
            raise GenerationError(f"Generation failed: {e.response.text}")
    
    async def _stream_generate(
        self,
        payload: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Streaming generation."""
        try:
            client = await self._get_client()
            async with client.stream("POST", "/api/generate", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done", False):
                            break
        except httpx.RequestError as e:
            raise OllamaConnectionError(self._base_url, str(e))
        except httpx.HTTPStatusError as e:
            raise GenerationError(f"Stream generation failed: {e.response.text}")
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs: Any
    ) -> str | AsyncGenerator[str, None]:
        """
        Chat completion with message history.
        
        Args:
            model: Model name
            messages: List of message dicts with 'role' and 'content'
            system: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters
        """
        settings = self._settings.ollama
        
        # Add system message if provided
        if system:
            messages = [{"role": "system", "content": system}] + messages
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature or settings.temperature,
                "top_p": settings.top_p,
                "num_predict": max_tokens or settings.max_tokens,
            },
            "keep_alive": settings.keep_alive,
        }
        
        payload.update(kwargs)
        
        if stream:
            return self._stream_chat(payload)
        else:
            return await self._sync_chat(payload)
    
    async def _sync_chat(self, payload: Dict[str, Any]) -> str:
        """Synchronous chat."""
        try:
            client = await self._get_client()
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except httpx.RequestError as e:
            raise OllamaConnectionError(self._base_url, str(e))
        except httpx.HTTPStatusError as e:
            raise GenerationError(f"Chat failed: {e.response.text}")
    
    async def _stream_chat(
        self,
        payload: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Streaming chat."""
        try:
            client = await self._get_client()
            async with client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
                        if data.get("done", False):
                            break
        except httpx.RequestError as e:
            raise OllamaConnectionError(self._base_url, str(e))
        except httpx.HTTPStatusError as e:
            raise GenerationError(f"Stream chat failed: {e.response.text}")
    
    async def embed(
        self,
        model: str,
        text: str | List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings for text.
        
        Args:
            model: Embedding model name
            text: Single text or list of texts to embed
            
        Returns:
            List of embedding vectors
        """
        texts = [text] if isinstance(text, str) else text
        
        try:
            client = await self._get_client()
            
            # Ollama's embed endpoint
            payload = {
                "model": model,
                "input": texts,
            }
            
            response = await client.post(
                "/api/embed",
                json=payload,
                timeout=LLMConstants.EMBEDDING_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            return data.get("embeddings", [])
            
        except httpx.RequestError as e:
            raise OllamaConnectionError(self._base_url, str(e))
        except httpx.HTTPStatusError as e:
            raise EmbeddingError(f"Embedding failed: {e.response.text}")
    
    async def embed_batch(
        self,
        model: str,
        texts: List[str],
        batch_size: Optional[int] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for texts in batches.
        
        Args:
            model: Embedding model name
            texts: List of texts to embed
            batch_size: Batch size (defaults to config)
            
        Returns:
            List of embedding vectors
        """
        batch_size = batch_size or self._settings.performance.embedding_batch_size
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = await self.embed(model, batch)
            embeddings.extend(batch_embeddings)
            
            logger.debug(
                "Embedded batch",
                batch_start=i,
                batch_size=len(batch),
                total=len(texts)
            )
        
        return embeddings


# Singleton instance
ollama_client = OllamaClient()