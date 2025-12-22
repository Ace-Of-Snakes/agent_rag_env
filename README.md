# RAGent

A local RAG (Retrieval-Augmented Generation) system with multi-modal PDF processing, agent capabilities, and a React UI.

## Features

- **Multi-Modal PDF Processing**: Extract text and analyze images from PDFs using vision models
- **Semantic Search**: Vector similarity search with pgvector for accurate document retrieval
- **Agent System**: Extensible tool registry with RAG search, web search, and file reading
- **Conversation Branching**: Create branches in conversations to explore different paths
- **Streaming Responses**: Real-time SSE streaming for agent responses
- **Local-First**: All processing happens locally using Ollama

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React UI      │────▶│   FastAPI       │────▶│   PostgreSQL    │
│   (TypeScript)  │     │   Backend       │     │   + pgvector    │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                        ┌────────┴────────┐
                        │                 │
                   ┌────▼────┐      ┌─────▼─────┐
                   │  Redis  │      │  Ollama   │
                   │ (Cache) │      │  (LLMs)   │
                   └─────────┘      └───────────┘
```

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, asyncpg
- **Database**: PostgreSQL with pgvector extension
- **Cache**: Redis for session and response caching
- **LLMs**: Ollama (Qwen2.5, Qwen2-VL, nomic-embed-text)
- **Frontend**: React, TypeScript, Vite, SCSS

## Prerequisites

- Docker and Docker Compose
- NVIDIA GPU with 9+ GB VRAM (for running models)
- 16+ GB RAM recommended

## Quick Start
0. **Possible Pre-Requisites**
   - Make sure Docker has access to your GPU (NVIDIA Container Toolkit) -> https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
   - Install Ollama on your host machine: https://ollama.com/download
   - Pull needed models with ollama pull model_name

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ragent.git
   cd ragent
   ```

2. **Configure environment**
   ```bash
   cp backend/.env.example backend/.env
   # Edit .env as needed
   ```

3. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Pull required Ollama models**
   ```bash
   docker exec ragent-ollama ollama pull qwen2.5:7b-instruct-q4_K_M
   docker exec ragent-ollama ollama pull qwen2-vl:7b-instruct-q4_K_M
   docker exec ragent-ollama ollama pull nomic-embed-text
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

### Documents
- `POST /api/v1/documents` - Upload a document
- `GET /api/v1/documents` - List documents
- `GET /api/v1/documents/{id}` - Get document details
- `DELETE /api/v1/documents/{id}` - Delete a document
- `POST /api/v1/documents/search` - Search documents

### Chats
- `POST /api/v1/chats` - Create a new chat
- `GET /api/v1/chats` - List chats
- `GET /api/v1/chats/{id}` - Get chat with messages
- `DELETE /api/v1/chats/{id}` - Delete a chat
- `POST /api/v1/chats/{id}/messages` - Send a message
- `POST /api/v1/chats/{id}/messages/stream` - Send message with streaming (SSE)
- `POST /api/v1/chats/{id}/branches` - Create a branch
- `POST /api/v1/chats/{id}/branches/switch` - Switch branch

### Health
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed health with service status

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `REDIS_HOST` | Redis host | `localhost` |
| `OLLAMA_BASE_URL` | Ollama API URL | `http://localhost:11434` |
| `OLLAMA_TEXT_MODEL` | Text generation model | `qwen2.5:7b-instruct-q4_K_M` |
| `OLLAMA_VISION_MODEL` | Vision model | `qwen2-vl:7b-instruct-q4_K_M` |
| `CHUNK_SIZE` | Document chunk size | `1000` |
| `CHUNK_OVERLAP` | Chunk overlap | `200` |
| `MAX_UPLOAD_SIZE_MB` | Max file upload size | `50` |

See `backend/.env.example` for all options.

## Project Structure

```
ragent/
├── backend/
│   ├── app/
│   │   ├── agents/        # Agent orchestrator and tools
│   │   ├── api/           # FastAPI routes and middleware
│   │   ├── core/          # Config, constants, logging
│   │   ├── db/            # Database connections
│   │   ├── models/        # SQLAlchemy models and Pydantic schemas
│   │   ├── repositories/  # Data access layer
│   │   └── services/      # Business logic services
│   ├── alembic/           # Database migrations
│   └── tests/             # Test suite
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom hooks
│   │   ├── services/      # API services
│   │   ├── styles/        # SCSS styles
│   │   └── types/         # TypeScript types
│   └── public/            # Static assets
└── docker/                # Docker configuration
```

## License

MIT
