# Tool Chat

An intelligent conversational AI application powered by LangGraph with advanced features including streaming responses, conversation memory, web search capabilities, user authentication, and real-time feedback collection.

## Table of Contents
<!-- TOC -->

- [Tool Chat](#tool-chat)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Technologies](#technologies)
    - [Core Framework & AI](#core-framework--ai)
    - [Backend](#backend)
    - [Frontend](#frontend)
    - [Database & Storage](#database--storage)
    - [Caching & Rate Limiting](#caching--rate-limiting)
    - [Authentication & Security](#authentication--security)
    - [Search & Tools](#search--tools)
    - [Configuration & Development](#configuration--development)
    - [DevOps & Infrastructure](#devops--infrastructure)
  - [Features](#features)
    - [Core Capabilities](#core-capabilities)
    - [Memory & Persistence](#memory--persistence)
    - [Authentication & Authorization](#authentication--authorization)
    - [Advanced Features](#advanced-features)
    - [User Experience](#user-experience)
    - [Developer Experience](#developer-experience)
  - [Architecture](#architecture)
    - [System Architecture](#system-architecture)
    - [Graph Workflow](#graph-workflow)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Running the Application](#running-the-application)
      - [Option 1: Run both services simultaneously requires tmux](#option-1-run-both-services-simultaneously-requires-tmux)
      - [Option 2: Run services separately](#option-2-run-services-separately)
    - [Available Commands](#available-commands)
  - [API Documentation](#api-documentation)
    - [Key Endpoints](#key-endpoints)
      - [Authentication](#authentication)
      - [Chat](#chat)
      - [Feedback](#feedback)
      - [Admin](#admin)
      - [Health](#health)
  - [Potential Improvements](#potential-improvements)
    - [Development Guidelines](#development-guidelines)
  - [License](#license)
  - [Contact](#contact)

<!-- /TOC -->

## Overview

Tool Chat is a production-ready conversational AI system that combines the power of LangGraph for orchestrating complex agent workflows with a modern web stack. It features a FastAPI backend for efficient API handling and a Streamlit frontend for an intuitive user experience. The application includes persistent conversation memory, real-time web search integration, and comprehensive user management.

## Technologies

### Core Framework & AI

- **[LangGraph](https://github.com/langchain-ai/langgraph)** - Agent orchestration and state management
- **[LangChain](https://github.com/langchain-ai/langchain)** - LLM framework and tooling
- **[LangChain OpenAI](https://github.com/langchain-ai/langchain)** - OpenAI integration
- **[Instructor](https://github.com/jxnl/instructor)** - Structured output generation

### Backend

- **[FastAPI](https://fastapi.tiangolo.com/)** - High-performance async web framework
- **[Uvicorn](https://www.uvicorn.org/)** - ASGI server
- **[Pydantic](https://docs.pydantic.dev/)** - Data validation
- **[SQLAlchemy](https://www.sqlalchemy.org/)** - ORM and database management
- **[Alembic](https://alembic.sqlalchemy.org/)** - Database migrations

### Frontend

- **[Streamlit](https://streamlit.io/)** - Interactive web interface
- **[Plotly](https://plotly.com/)** - Data visualization and charts
- **[HTTPX](https://www.python-httpx.org/)** - Async HTTP client

### Database & Storage

- **[PostgreSQL](https://www.postgresql.org/)** - Primary database
- **[LangGraph Checkpoint Postgres](https://github.com/langchain-ai/langgraph)** - Conversation state persistence
- **[Psycopg](https://www.psycopg.org/)** - PostgreSQL adapter

### Caching & Rate Limiting

- **[Redis](https://redis.io/)** - Caching layer
- **[aiocache](https://github.com/aio-libs/aiocache)** - Async caching library
- **[SlowAPI](https://github.com/laurentS/slowapi)** - Rate limiting middleware

### Authentication & Security

- **[python-jose](https://github.com/mpdavis/python-jose)** - JWT token handling
- **[Passlib](https://passlib.readthedocs.io/)** - Password hashing
- **[Bcrypt](https://github.com/pyca/bcrypt)** - Secure password hashing

### Search & Tools

- **[Tavily](https://tavily.com/)** - Web search API
- **[DuckDuckGo Search](https://github.com/deedy5/ddgs)** - Alternative search provider

### Configuration & Development

- **[OmegaConf](https://omegaconf.readthedocs.io/)** - Configuration management
- **[Rich](https://rich.readthedocs.io/)** - Terminal formatting
- **[Ruff](https://github.com/astral-sh/ruff)** - Fast Python linter/formatter
- **[pytest](https://docs.pytest.org/)** - Testing framework

### DevOps & Infrastructure

- **[Docker](https://www.docker.com/)** & **Docker Compose** - Containerization
- **[uv](https://github.com/astral-sh/uv)** - Fast Python package manager
- **[Jupyter](https://jupyter.org/)** - Interactive notebooks for experimentation

## Features

### Core Capabilities

- **Intelligent Conversational AI**: Context-aware responses using LangGraph state management
- **Real-time Streaming**: Server-Sent Events (SSE) for immediate response streaming
- **Web Search Integration**: Live web search using Tavily API for up-to-date information
- **Date & Time Tools**: Built-in tools for temporal queries and calendar information

### Memory & Persistence

- **Conversation Checkpointing**: Persistent conversation history using PostgreSQL
- **Long-term Memory Store**: Dedicated memory store for context retention across sessions
- **Session Management**: Thread-based conversation tracking with unique session IDs
- **Memory Summarization**: Automatic conversation summarization for context management

### Authentication & Authorization

- **JWT-based Authentication**: Secure token-based authentication system
- **Role-Based Access Control (RBAC)**: Multi-role support (admin, user)
- **User Registration & Login**: Complete user management system
- **Protected Endpoints**: Role-specific route protection

### Advanced Features

- **Feedback System**: Real-time user feedback collection (positive/negative)
- **Chat History**: Full conversation history retrieval and analysis
- **Feedback Analytics**: Visual feedback analysis with charts and statistics
- **Response Caching**: Redis-based caching for improved performance
- **Rate Limiting**: Concurrent stream limiting and request throttling

### User Experience

- **Simple UI**: Clean Streamlit interface with intuitive design
- **User Authentication UI**: Login/registration forms with session management
- **Message Formatting**: Clean markdown rendering with source citation
- **Feedback Buttons**: Easy one-click feedback on assistant responses
- **Visual Analytics**: Plotly charts for feedback distribution

### Developer Experience

- **Type Safety**: Full Pydantic schema validation
- **Async/Await**: Fully asynchronous codebase for optimal performance
- **Database Migrations**: Alembic for version-controlled schema changes
- **Comprehensive Testing**: pytest suite with fixtures and mocks
- **Makefile Commands**: Simple commands for common tasks
- **Docker Support**: Complete containerization for easy deployment

## Architecture

### System Architecture

```txt
┌─────────────────┐
│   Streamlit     │
│    Frontend     │
└────────┬────────┘
         │ HTTP/SSE
         ▼
┌─────────────────┐
│   FastAPI       │
│   Backend       │
└────────┬────────┘
         │
    ┌────┴─────┬──────────┬──────────┐
    ▼          ▼          ▼          ▼
┌────────┐ ┌───────┐ ┌────────┐ ┌─────────┐
│ Redis  │ │ Auth  │ │ Cache  │ │ Rate    │
│        │ │ JWT   │ │        │ │ Limiter │
└────────┘ └───────┘ └────────┘ └─────────┘
    │
    ▼
┌─────────────────┐
│   LangGraph     │
│   Engine        │
└────────┬────────┘
         │
    ┌────┴─────┬──────────┬──────────┐
    ▼          ▼          ▼          ▼
┌────────┐ ┌───────┐ ┌────────┐ ┌──────────┐
│ LLM    │ │Tools  │ │Memory  │ │ Context  │
│ Node   │ │ Node  │ │ Store  │ │Summarize │
└────────┘ └───────┘ └────────┘ └──────────┘
    │
    ▼
┌─────────────────┐
│   PostgreSQL    │
│ • Checkpoints   │
│ • User Data     │
│ • Feedback      │
└─────────────────┘
```

### Graph Workflow

The LangGraph workflow consists of:

1. **LLM Call Node**: Processes user input and determines tool usage
2. **Tool Node**: Executes tools (search, date/time) when needed
3. **Summarization Node**: Condenses long conversations
4. **Memory Update Node**: Maintains conversation context
5. **Conditional Edges**: Routes based on tool calls and summarization needs

## Getting Started

### Prerequisites

- Python 3.13+
- uv (uv package manager) — used by Makefile for dependency management and running modules (`uv sync` / `uv run`)
- Docker & Docker Compose
- OpenAI API key
- Tavily API key (for web search)
- Note: pyproject.toml currently lists both `psycopg-binary` and `psycopg2-binary`; prefer keeping only one adapter to avoid confusion or accidental mismatched drivers.

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/chineidu/tool-chat.git
cd tool-chat
```

1. **Install dependencies**

```bash
make install
# or
uv sync
```

1. **Set up environment variables**

```bash
cp .env.example .env
# Edit .env with your API keys and configuration
# NOTE: Settings load is strict (populate_by_name=True, strict=True). Missing/invalid env vars can raise errors — fill .env before starting services.
```

1. **Start infrastructure services**

```bash
make up
# Starts PostgreSQL and Redis via Docker Compose
# The Postgres container runs ./docker/init-databases.sh which creates a separate API DB (API_DB_NAME, default "user_feedback_db").
# Ensure POSTGRES_USER/POSTGRES_PASSWORD (and API_DB_NAME if changed) are set in .env so the init script can create the DB as expected.
```

1. **Run database migrations**

```bash
uv run alembic upgrade head
```

1. **Create admin user (optional)**

```bash
uv run -m scripts.create_admin --username admin --email admin@example.com --password mypassword
```

### Running the Application

#### Option 1: Run both services simultaneously (requires tmux)

```bash
make src
```

#### Option 2: Run services separately

Terminal 1 - API Server:

```bash
make api-run
# Available at http://localhost:8080
```

Terminal 2 - Frontend:

```bash
make frontend
# Available at http://localhost:8501
```

### Available Commands

```bash
make help          # Show all available commands
make install       # Install dependencies
make test          # Run tests
make test-verbose  # Run tests with verbose output
make lint          # Run linter
make format        # Format code
make up            # Start Docker services
make down          # Stop Docker services
make restart       # Restart services
make logs          # View logs
make clean-cache   # Clean cache files
make clean-all     # Clean everything including volumes
```

## API Documentation

Once the API server is running, access:

- **Swagger UI**: <http://localhost:8080/docs>
- **ReDoc**: <http://localhost:8080/redoc>

### Key Endpoints

#### Authentication

- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/token` - Login and get JWT token
- `GET /api/v1/auth/users/me` - Get current user info

#### Chat

- `POST /api/v1/chat_stream` - Stream chat responses (SSE)
- `GET /api/v1/chat_history` - Retrieve conversation history

#### Feedback

- `POST /api/v1/feedback` - Submit user feedback
- `GET /api/v1/feedback/user/{user_id}` - Get user's feedback

#### Admin

- `GET /api/v1/admin/roles` - List all roles (admin only)
- `POST /api/v1/admin/roles` - Create a new role (admin only)
- `POST /api/v1/admin/users/{username}/roles/{role_name}` - Assign a role to a user (admin only)
- `DELETE /api/v1/admin/users/{username}/roles/{role_name}` - Remove a role from a user (admin only)

#### Health

- `GET /api/v1/health` - Health check endpoint

## Potential Improvements

- [ ] **CI/CD Pipeline**: Automated testing and deployment with GitHub Actions
- [ ] **Document Upload**: Enable file uploads for context-aware conversations
- [ ] **Background Task Queue**: Add Celery for async processing of feedback and analytics
- [ ] **Logging & Monitoring**: Integrate with ELK stack or Datadog
- [ ] **Conversation Branching**: Allow users to fork conversations at any point
- [ ] **Export Functionality**: Export conversations as PDF, Markdown, or JSON
- [ ] **A/B Testing Framework**: Test different prompts and models
- [ ] **Content Moderation**: Implement content filtering and safety checks
- [ ] **Kubernetes Deployment**: Helm charts for K8s deployment

### Development Guidelines

- Follow PEP 8 style guide
- Write tests for new features
- Update documentation as needed
- Use type hints for better code clarity
- Run `make lint` and `make format` before committing
- Note: pre-commit is configured to run `ruff` with `--fix` and `mypy` (see `.pre-commit-config.yaml`); mypy is configured to ignore missing imports and excludes `tests/` and `alembic/`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

**Repository**: [https://github.com/chineidu/tool-chat](https://github.com/chineidu/tool-chat)

---

**Built with:** LangGraph, FastAPI, and Streamlit
