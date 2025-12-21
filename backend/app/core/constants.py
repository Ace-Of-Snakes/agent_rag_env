"""
Centralized constants for the RAGent application.
All magic strings and numbers are defined here.
"""

# =============================================================================
# Database Constants
# =============================================================================

class DatabaseConstants:
    """Database-related constants."""
    
    # Connection pool settings
    POOL_SIZE = 5
    MAX_OVERFLOW = 10
    POOL_TIMEOUT_SECONDS = 30
    POOL_RECYCLE_SECONDS = 1800
    
    # Vector dimensions for pgvector
    EMBEDDING_DIMENSIONS = 768  # nomic-embed-text dimension
    
    # Full-text search configuration
    TSVECTOR_CONFIG = "english"


class RedisConstants:
    """Redis key patterns and TTL defaults."""
    
    # Key patterns (use format strings)
    SESSION_KEY = "session:{session_id}"
    CHAT_HISTORY_KEY = "chat:{chat_id}:history"
    PROCESSING_JOB_KEY = "processing:{job_id}"
    RATE_LIMIT_KEY = "rate_limit:{identifier}"
    RESPONSE_CACHE_KEY = "cache:response:{query_hash}"
    
    # Default TTLs in seconds
    DEFAULT_SESSION_TTL = 1800  # 30 minutes
    DEFAULT_CHAT_HISTORY_TTL = 86400  # 24 hours
    DEFAULT_PROCESSING_JOB_TTL = 3600  # 1 hour
    DEFAULT_RATE_LIMIT_TTL = 60  # 1 minute
    DEFAULT_RESPONSE_CACHE_TTL = 3600  # 1 hour


# =============================================================================
# Document Processing Constants
# =============================================================================

class DocumentConstants:
    """Document processing constants."""
    
    # Supported file types
    SUPPORTED_EXTENSIONS = frozenset([".pdf"])
    SUPPORTED_MIME_TYPES = frozenset(["application/pdf"])
    
    # Chunking defaults
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_CHUNK_OVERLAP = 200
    MIN_CHUNK_SIZE = 100
    MAX_CHUNK_SIZE = 4000
    
    # File size limits
    DEFAULT_MAX_UPLOAD_SIZE_MB = 50
    BYTES_PER_MB = 1024 * 1024
    
    # PDF processing
    PDF_DPI = 150  # Resolution for page rendering
    PDF_IMAGE_FORMAT = "png"
    
    # Vision gating thresholds
    DEFAULT_MIN_IMAGE_AREA_RATIO = 0.05


class ChunkingStrategy:
    """Available chunking strategies."""
    
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    PARAGRAPH = "paragraph"


# =============================================================================
# LLM Constants
# =============================================================================

class LLMConstants:
    """LLM-related constants."""
    
    # Default model names (can be overridden by config)
    DEFAULT_VISION_MODEL = "qwen2-vl:7b-instruct-q4_K_M"
    DEFAULT_TEXT_MODEL = "qwen2.5:7b-instruct-q4_K_M"
    DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
    
    # Generation parameters
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_TOP_P = 0.9
    DEFAULT_MAX_TOKENS = 2048
    
    # Context management
    DEFAULT_MAX_HISTORY_TOKENS = 2048
    DEFAULT_SUMMARIZE_AFTER_MESSAGES = 10
    
    # Embedding
    DEFAULT_EMBEDDING_BATCH_SIZE = 16
    
    # Ollama keep-alive
    DEFAULT_KEEP_ALIVE = "60m"
    
    # Timeouts in seconds
    GENERATION_TIMEOUT = 300
    EMBEDDING_TIMEOUT = 60


# =============================================================================
# API Constants
# =============================================================================

class APIConstants:
    """API-related constants."""
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # SSE event types
    SSE_EVENT_MESSAGE = "message"
    SSE_EVENT_TOOL_START = "tool_start"
    SSE_EVENT_TOOL_END = "tool_end"
    SSE_EVENT_ERROR = "error"
    SSE_EVENT_DONE = "done"
    SSE_EVENT_PROGRESS = "progress"
    
    # Rate limiting
    DEFAULT_RATE_LIMIT_REQUESTS = 100
    DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60


class HTTPStatus:
    """HTTP status codes."""
    
    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


# =============================================================================
# Agent Constants
# =============================================================================

class AgentConstants:
    """Agent and tool constants."""
    
    # Tool names
    TOOL_RAG_SEARCH = "rag_search"
    TOOL_WEB_SEARCH = "web_search"
    TOOL_FILE_READER = "file_reader"
    
    # Max tool iterations per request
    MAX_TOOL_ITERATIONS = 5
    
    # Web search
    DUCKDUCKGO_MAX_RESULTS = 5
    WEB_SEARCH_TIMEOUT_SECONDS = 10


# =============================================================================
# Search Constants
# =============================================================================

class SearchConstants:
    """Search-related constants."""
    
    # Vector search
    DEFAULT_TOP_K = 5
    MAX_TOP_K = 20
    
    # Similarity thresholds
    MIN_SIMILARITY_THRESHOLD = 0.3
    
    # Hybrid search weights
    VECTOR_WEIGHT = 0.7
    KEYWORD_WEIGHT = 0.3


# =============================================================================
# Chat Constants
# =============================================================================

class ChatConstants:
    """Chat-related constants."""
    
    # Message roles
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_SYSTEM = "system"
    ROLE_TOOL = "tool"
    
    # Message types
    TYPE_TEXT = "text"
    TYPE_FILE = "file"
    TYPE_TOOL_CALL = "tool_call"
    TYPE_TOOL_RESULT = "tool_result"
    
    # Branch handling
    DEFAULT_BRANCH_NAME = "main"
