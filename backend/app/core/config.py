"""
Application configuration using Pydantic Settings.
All configuration is loaded from environment variables.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import (
    DatabaseConstants,
    DocumentConstants,
    LLMConstants,
    RedisConstants,
    SearchConstants,
)


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration."""
    
    model_config = SettingsConfigDict(env_prefix="POSTGRES_")
    
    host: str = "localhost"
    port: int = 5432
    user: str = "ragent"
    password: str = "ragent_secret"
    db: str = "ragent"
    
    pool_size: int = DatabaseConstants.POOL_SIZE
    max_overflow: int = DatabaseConstants.MAX_OVERFLOW
    pool_timeout: int = DatabaseConstants.POOL_TIMEOUT_SECONDS
    pool_recycle: int = DatabaseConstants.POOL_RECYCLE_SECONDS
    
    @property
    def async_url(self) -> str:
        """Async database URL for asyncpg."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db}"
        )
    
    @property
    def sync_url(self) -> str:
        """Sync database URL for Alembic migrations."""
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db}"
        )


class RedisSettings(BaseSettings):
    """Redis configuration."""
    
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    
    session_ttl: int = Field(
        default=RedisConstants.DEFAULT_SESSION_TTL,
        alias="SESSION_TTL_SECONDS"
    )
    chat_history_ttl: int = Field(
        default=RedisConstants.DEFAULT_CHAT_HISTORY_TTL,
        alias="CHAT_HISTORY_TTL_SECONDS"
    )
    processing_job_ttl: int = Field(
        default=RedisConstants.DEFAULT_PROCESSING_JOB_TTL,
        alias="PROCESSING_JOB_TTL_SECONDS"
    )
    
    @property
    def url(self) -> str:
        """Redis connection URL."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class OllamaSettings(BaseSettings):
    """Ollama LLM configuration."""
    
    model_config = SettingsConfigDict(env_prefix="OLLAMA_")
    
    base_url: str = "http://localhost:11434"
    vision_model: str = LLMConstants.DEFAULT_VISION_MODEL
    text_model: str = LLMConstants.DEFAULT_TEXT_MODEL
    embedding_model: str = LLMConstants.DEFAULT_EMBEDDING_MODEL
    keep_alive: str = LLMConstants.DEFAULT_KEEP_ALIVE
    
    # Generation parameters
    temperature: float = LLMConstants.DEFAULT_TEMPERATURE
    top_p: float = LLMConstants.DEFAULT_TOP_P
    max_tokens: int = LLMConstants.DEFAULT_MAX_TOKENS


class PerformanceSettings(BaseSettings):
    """Performance tuning configuration."""
    
    # Embedding batching
    embedding_batch_size: int = Field(
        default=LLMConstants.DEFAULT_EMBEDDING_BATCH_SIZE,
        alias="EMBEDDING_BATCH_SIZE"
    )
    
    # Vision gating
    vision_gating_enabled: bool = Field(default=True, alias="VISION_GATING_ENABLED")
    vision_gating_min_image_ratio: float = Field(
        default=DocumentConstants.DEFAULT_MIN_IMAGE_AREA_RATIO,
        alias="VISION_GATING_MIN_IMAGE_RATIO"
    )
    
    # Response caching
    response_cache_enabled: bool = Field(default=True, alias="RESPONSE_CACHE_ENABLED")
    response_cache_ttl: int = Field(
        default=RedisConstants.DEFAULT_RESPONSE_CACHE_TTL,
        alias="RESPONSE_CACHE_TTL_SECONDS"
    )
    
    # Context management
    max_history_tokens: int = Field(
        default=LLMConstants.DEFAULT_MAX_HISTORY_TOKENS,
        alias="MAX_HISTORY_TOKENS"
    )
    summarize_after_messages: int = Field(
        default=LLMConstants.DEFAULT_SUMMARIZE_AFTER_MESSAGES,
        alias="SUMMARIZE_AFTER_MESSAGES"
    )


class DocumentSettings(BaseSettings):
    """Document processing configuration."""
    
    # Add model_config to enable reading environment variables
    model_config = SettingsConfigDict(
        env_prefix="",  # No prefix, use aliases directly
        extra="ignore"
    )
    
    chunk_size: int = Field(
        default=DocumentConstants.DEFAULT_CHUNK_SIZE,
        alias="CHUNK_SIZE"
    )
    chunk_overlap: int = Field(
        default=DocumentConstants.DEFAULT_CHUNK_OVERLAP,
        alias="CHUNK_OVERLAP"
    )
    max_upload_size_mb: int = Field(
        default=DocumentConstants.DEFAULT_MAX_UPLOAD_SIZE_MB,
        alias="MAX_UPLOAD_SIZE_MB"
    )
    
    @property
    def max_upload_size_bytes(self) -> int:
        """Maximum upload size in bytes."""
        return self.max_upload_size_mb * DocumentConstants.BYTES_PER_MB
    
    @field_validator("chunk_size")
    @classmethod
    def validate_chunk_size(cls, v: int) -> int:
        """Validate chunk size is within acceptable range."""
        if v < DocumentConstants.MIN_CHUNK_SIZE:
            raise ValueError(
                f"chunk_size must be at least {DocumentConstants.MIN_CHUNK_SIZE}"
            )
        if v > DocumentConstants.MAX_CHUNK_SIZE:
            raise ValueError(
                f"chunk_size must be at most {DocumentConstants.MAX_CHUNK_SIZE}"
            )
        return v


class SearchSettings(BaseSettings):
    """Search configuration."""
    
    default_top_k: int = SearchConstants.DEFAULT_TOP_K
    max_top_k: int = SearchConstants.MAX_TOP_K
    min_similarity_threshold: float = SearchConstants.MIN_SIMILARITY_THRESHOLD
    vector_weight: float = SearchConstants.VECTOR_WEIGHT
    keyword_weight: float = SearchConstants.KEYWORD_WEIGHT


class APISettings(BaseSettings):
    """API server configuration."""
    
    model_config = SettingsConfigDict(env_prefix="API_")
    
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"]
    )
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from JSON string or list."""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v


class Settings(BaseSettings):
    """Main application settings aggregating all sub-settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    performance: PerformanceSettings = Field(default_factory=PerformanceSettings)
    document: DocumentSettings = Field(default_factory=DocumentSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    api: APISettings = Field(default_factory=APISettings)
    
    # Application info
    app_name: str = "RAGent"
    app_version: str = "0.1.0"
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.
    Uses LRU cache to ensure settings are only loaded once.
    """
    return Settings()
