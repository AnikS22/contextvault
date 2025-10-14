# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ContextVault is a local-first context management layer for AI models. It acts as a proxy between users and local AI models (Ollama), automatically injecting relevant context into conversations to transform generic chatbots into personalized assistants.

**Core Value Proposition**: The system intercepts AI requests, retrieves relevant stored context using semantic/keyword search, and injects it into prompts using configurable templates. This gives AI models "memory" of user preferences, personal details, projects, and historical information.

**The Goal**:Build infrastructure that removes artificial limitations from local AI models, making them significantly more capable through dynamic reasoning allocation, multi-model coordination, and intelligent resource management.

## Architecture

### Request Flow
1. User → ContextVault Proxy (port 11435) → Ollama (port 11434)
2. ContextVault intercepts request → retrieves relevant context → injects into prompt → forwards to Ollama
3. Response flows back unchanged

### Core Components

**Database Layer** (`database.py`, `models/`):
- SQLAlchemy with SQLite (default) or PostgreSQL
- Models: `ContextEntry`, `ModelPermission`, `Session`, `MCPConnection`, `MCPProvider`
- All models inherit from `Base` in `database.py`
- Use `get_db_context()` for context manager, `get_db_session()` for FastAPI dependency injection

**Services Layer** (`services/`):
- `vault.py`: CRUD operations for context entries
- `context_retrieval.py`: Smart retrieval with relevance scoring, permission filtering, and deduplication
- `semantic_search.py`: Sentence transformers for semantic search (with keyword fallback)
- `permissions.py`: Model-level access control to context types
- `templates.py`: Template management for context injection formatting
- `conversation_learning.py`: Extract and learn from AI conversations

**Integration Layer** (`integrations/`):
- `ollama.py`: Main Ollama integration, handles prompt extraction and context injection
- `mcp/`: Model Context Protocol integration for external data sources (Calendar, Gmail, etc.)
  - `client.py`: MCP client implementation
  - `manager.py`: Orchestrates multiple MCP connections
  - `providers.py`: Provider-specific implementations (Calendar, Gmail, Filesystem)

**API Layer** (`api/`):
- FastAPI application in `main.py`
- Routers: `context.py`, `permissions.py`, `health.py`, `mcp.py`
- Proxy functionality for Ollama requests with context injection

**CLI Layer** (`cli/`):
- Click-based CLI in `cli/__main__.py`
- Commands organized in `cli/commands/`: context, permissions, system, mcp, templates, learning, etc.

### Key Service Patterns

**Context Retrieval Flow**:
1. Check model permissions (`PermissionService.validate_model_access()`)
2. Use semantic search if available, fallback to keyword search
3. Score and rank entries by relevance (access count, recency, content match, semantic similarity)
4. Apply permission filters
5. Format using template system

**Template System**:
- Templates stored in `templates.yaml` with strength ratings (1-10)
- Higher strength = more forceful instruction to AI
- `direct_instruction`, `assistant_roleplay`, `subtle_hint`, etc.
- Templates accessed via `template_manager` singleton

**Semantic Search**:
- Uses sentence-transformers with `all-MiniLM-L6-v2` model
- Stores embeddings in `ContextEntry.embedding_vector` field
- Hybrid scoring: combines semantic similarity + keyword match + access count + recency
- Graceful fallback to keyword search if models unavailable

## Common Development Tasks

### Running the System

```bash
# Start the proxy server (development)
python -m contextvault.cli start

# Or run FastAPI directly
python -m contextvault.main

# Or with uvicorn for debugging
uvicorn contextvault.main:app --host 127.0.0.1 --port 11435 --reload
```

### Database Operations

```bash
# Initialize database
python scripts/init_db.py

# Run migrations (if using alembic)
alembic upgrade head

# Or initialize via CLI
python -m contextvault.cli setup
```

### Testing

```bash
# Quick system test
python -m contextvault.cli test

# Run full test suite
pytest tests/

# Specific test file
pytest tests/test_vault.py -v

# Demo the system
python -m contextvault.cli demo

# Validate effectiveness
python scripts/validate_effectiveness.py
```

### CLI Usage Patterns

Most CLI commands follow this pattern:
```bash
python -m contextvault.cli <command> <subcommand> [options]
```

Common commands:
- `start/stop/status` - System control
- `context add/list/search/delete` - Context management
- `permissions grant/revoke/list` - Permission management
- `templates list/set` - Template management
- `mcp add/enable/search` - MCP integration
- `diagnose/fix/logs` - Troubleshooting

### Adding New Context Types

1. Add to `ContextType` enum in `models/context.py`
2. Update `get_allowed_context_types()` in `config.py`
3. Add type-specific formatting in `ContextRetrievalService._format_context_entry()`
4. Update permission scopes in `models/permissions.py` if needed

### Adding New Templates

1. Add template definition to `templates.yaml`
2. Include: `name`, `strength` (1-10), `template` (with `{context}` and `{prompt}` placeholders)
3. Templates loaded automatically via `TemplateManager` in `services/templates.py`

### Adding New MCP Providers

1. Create provider class inheriting from `BaseMCPProvider` in `integrations/mcp/providers.py`
2. Implement: `get_recent_activity()`, `get_scheduled_events()`, `search()`, `format_context()`
3. Register in `MCPManager._provider_types` dict in `integrations/mcp/manager.py`

## Configuration

**Environment Variables** (`.env` or direct export):
- `DATABASE_URL`: Database connection (default: `sqlite:///./contextvault.db`)
- `OLLAMA_HOST`/`OLLAMA_PORT`: Ollama connection (default: 127.0.0.1:11434)
- `PROXY_PORT`: ContextVault proxy port (default: 11435)
- `LOG_LEVEL`: Logging verbosity (INFO/DEBUG/WARNING)
- `MAX_CONTEXT_ENTRIES`: Max entries to inject (default: 100)
- `MAX_CONTEXT_LENGTH`: Max character limit (default: 10000)

**Config Files**:
- `config.yaml`: Main configuration (if exists)
- `templates.yaml`: Context injection templates

All settings managed via Pydantic `Settings` class in `config.py`.

## Important Patterns

**Session Management for Database Operations**:
- Services can accept optional `db_session` parameter
- If provided, caller manages commits/rollbacks
- If not provided, service creates its own session context
- Example in `VaultService.save_context()` and `ContextRetrievalService.__init__()`

**Error Handling**:
- Services raise `ValueError` for validation errors, `RuntimeError` for operational failures
- FastAPI exception handlers in `main.py` convert to appropriate HTTP responses
- Always log errors with context using structured logging (structlog)

**Logging**:
- Use `structlog.get_logger(__name__)` in all modules
- Structured logging with context: `logger.info("message", key=value, ...)`
- Debug logs for sensitive data only when `LOG_LEVEL=DEBUG`

**Async/Await**:
- Ollama integration methods are async
- FastAPI endpoints use async def
- Database operations are synchronous (SQLAlchemy)
- Use `asyncio.run()` or `await` for async integration methods

## Project Structure Notes

- `contextvault/` is the main package (not to be confused with root directory)
- `scripts/` contains standalone utilities and demos
- `tests/` contains pytest tests
- Old CLI at `cli/` (root level) is deprecated, use `contextvault/cli/`
- MCP integration temporarily disabled in main app (see `main.py:18,229`)

## Dependencies

Core dependencies:
- FastAPI + Uvicorn (API server)
- SQLAlchemy 2.0+ (ORM)
- Sentence-transformers (semantic search)
- Click + Rich (CLI)
- Pydantic v2 (validation)
- HTTPx (async HTTP client)

Install: `pip install -r requirements.txt`

Embedding models auto-download on first use to `~/.cache/torch/sentence_transformers/`
