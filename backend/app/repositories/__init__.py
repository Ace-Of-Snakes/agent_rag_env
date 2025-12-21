"""
Repository module for database access patterns.

Repositories provide a clean abstraction over database operations,
encapsulating queries and making them reusable across services.
"""

from app.repositories.base import BaseRepository
from app.repositories.chat import ChatRepository, MessageRepository
from app.repositories.chunk import ChunkRepository
from app.repositories.document import DocumentRepository

__all__ = [
    "BaseRepository",
    "ChatRepository",
    "MessageRepository",
    "ChunkRepository",
    "DocumentRepository",
]
