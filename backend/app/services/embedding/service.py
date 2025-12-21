"""
Embedding service for generating vector embeddings.
"""

import hashlib
from typing import List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.llm.client import ollama_client

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(self):
        self._settings = get_settings()
    
    @property
    def model(self) -> str:
        """Get the embedding model name."""
        return self._settings.ollama.embedding_model
    
    @property
    def batch_size(self) -> int:
        """Get the embedding batch size."""
        return self._settings.performance.embedding_batch_size
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        embeddings = await ollama_client.embed(self.model, text)
        return embeddings[0] if embeddings else []
    
    async def embed_texts(
        self,
        texts: List[str],
        batch_size: Optional[int] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with batching.
        
        Args:
            texts: List of texts to embed
            batch_size: Override batch size
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        batch_size = batch_size or self.batch_size
        
        logger.info(
            "Generating embeddings",
            num_texts=len(texts),
            batch_size=batch_size
        )
        
        return await ollama_client.embed_batch(
            self.model,
            texts,
            batch_size=batch_size
        )
    
    async def embed_chunks(
        self,
        chunks: List[dict],
        content_key: str = "content"
    ) -> List[dict]:
        """
        Add embeddings to chunk dictionaries.
        
        Args:
            chunks: List of chunk dicts
            content_key: Key for the content field
            
        Returns:
            Chunks with embeddings added
        """
        texts = [chunk[content_key] for chunk in chunks]
        embeddings = await self.embed_texts(texts)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding
        
        return chunks
    
    def compute_query_hash(self, query: str, chunks: List[str]) -> str:
        """
        Compute hash for caching query results.
        
        Args:
            query: Search query
            chunks: Retrieved chunk IDs
            
        Returns:
            Hash string
        """
        content = query + "".join(sorted(chunks))
        return hashlib.sha256(content.encode()).hexdigest()[:16]


# Singleton instance
embedding_service = EmbeddingService()
