# ContextVault Documentation Index

## 🚀 Getting Started

### For New Users
1. **[README](../README.md)** - Project overview and quick introduction
2. **[QUICKSTART](../QUICKSTART.md)** - Get up and running in 5 minutes
3. **[INSTALL](../INSTALL.md)** - Detailed installation instructions
4. **[HOW_TO_USE](../HOW_TO_USE.md)** - Step-by-step usage guide

### Quick References
- **[QUICK_DEMO_COMMANDS](../QUICK_DEMO_COMMANDS.md)** - Copy-paste command examples
- **[COMPLETE_USAGE_GUIDE](../COMPLETE_USAGE_GUIDE.md)** - Comprehensive feature guide

## 🧠 Extended Thinking System

### Core Documentation
1. **[EXTENDED_THINKING_EXPLANATION](./EXTENDED_THINKING_EXPLANATION.md)** - How it works (architecture, data flow, technical details)
2. **[EXTENDED_THINKING_STATUS](./EXTENDED_THINKING_STATUS.md)** - Implementation status and usage examples

### Key Concepts
- **Autonomous AI Reasoning** - Let AI think for minutes/hours instead of instant responses
- **Stream of Consciousness** - Full thought history tracked in database
- **Question-Driven Exploration** - AI generates and explores sub-questions
- **Confidence Evolution** - Track how certainty changes over time
- **Pause/Resume** - Interrupt and continue thinking sessions

### API Endpoints
```
POST   /api/thinking/start              # Start new session
GET    /api/thinking/{session_id}       # Get session status
GET    /api/thinking/{session_id}/stream    # View thoughts
GET    /api/thinking/{session_id}/questions # View sub-questions
GET    /api/thinking/{session_id}/syntheses # View syntheses
GET    /api/thinking/{session_id}/stats     # Get statistics
POST   /api/thinking/{session_id}/pause     # Pause thinking
POST   /api/thinking/{session_id}/resume    # Resume thinking
GET    /api/thinking/                   # List sessions
GET    /api/thinking/{session_id}/export    # Export session
```

## 🔧 Development

### For Contributors
- **[CLAUDE.md](../CLAUDE.md)** - Documentation for AI assistants (architecture, patterns, commands)
- **[PHASE_1_STATUS](./PHASE_1_STATUS.md)** - Multi-model routing implementation status

### Architecture
```
contextvault/
├── models/          # Database models (SQLAlchemy)
│   ├── context.py
│   ├── thinking.py
│   ├── routing.py
│   └── ...
├── api/             # REST API endpoints (FastAPI)
│   ├── thinking.py
│   ├── context.py
│   └── ...
├── thinking/        # Extended thinking system
│   ├── thinking_engine.py
│   ├── question_generator.py
│   └── session_manager.py
├── routing/         # Multi-model routing
│   ├── model_router.py
│   └── model_profiles.py
└── integrations/    # External integrations
    └── ollama.py
```

### Database Schema
```
thinking_sessions (1) ─┬─→ (N) thoughts
                       ├─→ (N) sub_questions
                       └─→ (N) thinking_syntheses
```

## 🔌 Integrations

### MCP (Model Context Protocol)
- **[MCP_INTEGRATION_SUMMARY](./MCP_INTEGRATION_SUMMARY.md)** - Overview of MCP integration
- **[MCP_GOOGLE_CALENDAR_SETUP](./MCP_GOOGLE_CALENDAR_SETUP.md)** - Google Calendar integration guide

### Ollama
- Local AI model integration
- Automatic context injection
- Session tracking and analytics

## 📦 Distribution

### For Package Maintainers
- **[GITHUB_SETUP](../GITHUB_SETUP.md)** - Publishing to GitHub
- **[REDDIT_POST_DRAFT](../REDDIT_POST_DRAFT.md)** - Community announcement template
- **[DEMO_VIDEO_SCRIPT](../DEMO_VIDEO_SCRIPT.md)** - Demo script for videos

## 🧪 Testing

### Test Files
Located in `tests/`:
- `test_thinking_system.py` - Extended thinking system tests
- `test_api.py` - API endpoint tests
- `test_context_effectiveness.py` - Context injection tests
- `test_integrations.py` - Integration tests
- `test_vault.py` - Core functionality tests

### Running Tests
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_thinking_system.py

# Run with coverage
pytest --cov=contextvault tests/
```

## 📊 Status

### ✅ Completed
- Core context management system
- Ollama proxy integration
- Semantic search (with fallback to keyword search)
- Extended thinking system (ALPHA)
- Multi-model routing (ALPHA)
- Database migrations via Alembic

### 🚧 In Progress
- Real-world testing with Ollama models
- Performance optimization
- Error handling improvements

### 📋 Planned
- Authentication and authorization
- Rate limiting
- Distributed thinking (multiple models)
- Cross-session learning
- Web UI

## 🆘 Support

### Troubleshooting
1. Check `/health` endpoint for system status
2. Review logs in console output
3. Verify Ollama is running: `curl http://localhost:11434/api/tags`
4. Check database connection: `sqlite3 contextvault.db .tables`

### Common Issues
- **Ollama not responding**: Start Ollama with `ollama serve`
- **Database errors**: Run migrations with `alembic upgrade head`
- **Import errors**: Install dependencies with `pip install -r requirements.txt`

## 📚 External Resources

- **[Ollama Documentation](https://ollama.ai/docs)** - AI model management
- **[FastAPI Documentation](https://fastapi.tiangolo.com/)** - Web framework
- **[SQLAlchemy Documentation](https://docs.sqlalchemy.org/)** - ORM and database
- **[Alembic Documentation](https://alembic.sqlalchemy.org/)** - Database migrations

## 📝 License

MIT License - See [LICENSE](../LICENSE) for details

---

**Last Updated**: 2025-10-06
**Version**: 0.1.0 (Alpha)
