"""
Services module providing business logic layer.
"""

from app.services.chat import ChatService, HistoryManager, chat_service, history_manager
from app.services.document import (
    DocumentProcessor,
    PDFExtractor,
    TextChunker,
    get_document_processor,
)
from app.services.embedding import EmbeddingService, embedding_service
from app.services.llm import OllamaClient, TextService, VisionService, ollama_client, text_service, vision_service
from app.services.search import (
    SearchResponse,
    SearchResult,
    VectorSearchService,
    WebResult,
    WebSearchResponse,
    WebSearchService,
    vector_search_service,
    web_search_service,
)

__all__ = [
    # Chat
    "ChatService",
    "chat_service",
    "HistoryManager",
    "history_manager",
    # Document
    "DocumentProcessor",
    "get_document_processor",
    "PDFExtractor",
    "TextChunker",
    # Embedding
    "EmbeddingService",
    "embedding_service",
    # LLM
    "OllamaClient",
    "ollama_client",
    "TextService",
    "text_service",
    "VisionService",
    "vision_service",
    # Search
    "VectorSearchService",
    "vector_search_service",
    "SearchResult",
    "SearchResponse",
    "WebSearchService",
    "web_search_service",
    "WebResult",
    "WebSearchResponse",
]
