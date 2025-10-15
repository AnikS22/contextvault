# 🔧 INTEGRATION PROMPT - Wire Up The New Features

## Current Situation

You have these files already created in `/Users/aniksahai/Desktop/contextvault`:

**Services (created but not used):**
- `contextvault/services/mem0_service.py` (517 lines) ✅
- `contextvault/services/memory_maintenance.py` ✅
- `contextvault/services/model_manager.py` ✅
- `contextvault/services/workspace_persistence.py` ✅

**CLI Commands (created but not registered):**
- `contextvault/cli/commands/chat.py` (112 lines) ✅
- `contextvault/cli/commands/feed.py` (166 lines) ✅
- `contextvault/cli/commands/recall.py` (197 lines) ✅
- `contextvault/cli/commands/graph_rag.py` (345 lines) ✅

**Core Features (ready but not integrated):**
- `contextvault/cognitive/workspace.py` (671 lines) ✅

## 🎯 YOUR TASK: Wire Everything Up (15-20 minutes)

Complete these 6 steps to activate all features:

---

### STEP 1: Register Commands in CLI (5 minutes)

**File:** `contextvault/cli/main.py`

**Find this (around line 21):**
```python
from contextvault.cli.commands import (
    system, context, permissions, templates,
    test, demo, diagnose, config, setup, mcp, learning
)
```

**Replace with:**
```python
from contextvault.cli.commands import (
    system, context, permissions, templates,
    test, demo, diagnose, config, setup, mcp, learning,
    chat, feed, recall, graph_rag  # ADD THESE NEW COMMANDS
)
```

**Find this (around line 106-116):**
```python
# Add command groups
cli.add_command(setup.setup)
cli.add_command(system.system_group)
cli.add_command(context.context_group)
cli.add_command(permissions.permissions_group)
cli.add_command(templates.templates)
cli.add_command(test.test_group)
cli.add_command(demo.demo_group)
cli.add_command(diagnose.diagnose_group)
cli.add_command(config.config_group)
cli.add_command(mcp.mcp_group)
cli.add_command(learning.learning_group)
```

**Add after line 116:**
```python
# Add new memory commands
cli.add_command(chat.chat)
cli.add_command(feed.feed_command)
cli.add_command(recall.recall_command)
cli.add_command(graph_rag.graph_rag_group)
```

---

### STEP 2: Rename CLI to ai-memory (2 minutes)

**File:** `pyproject.toml`

**Find this (around line 30-35):**
```toml
[project.scripts]
contextible = "contextvault.cli.main:cli"
```

**Replace with:**
```toml
[project.scripts]
ai-memory = "contextvault.cli.main:cli"
contextible = "contextvault.cli.main:cli"  # Keep for backward compatibility
```

**File:** `contextvault/cli/main.py`

**Find the docstring (around line 75-89):**
```python
def cli(ctx, no_banner):
    """
    ✨ Contextible - AI Memory for Local AI Models ✨

    Transform your local AI models from generic chatbots into personal
    assistants that actually remember you!
    ...
    """
```

**Replace with:**
```python
def cli(ctx, no_banner):
    """
    ✨ AI Memory - Universal Memory for Local AI Models ✨

    Transform any local AI into a persistent, context-aware assistant.
    Works with Ollama, LMStudio, LocalAI, and more.

    Features:
    • 🧠 Persistent memory with Mem0
    • 🔍 Semantic search with relationship graphs
    • 📚 3-layer cognitive workspace (8K/64K/256K)
    • 🕸️ NetworkX knowledge graphs
    • 🤖 Multi-model support
    • 💬 Interactive chat mode
    • 🎨 Beautiful CLI with rich output
    • 🔒 100% local and private

    Get started: ai-memory setup
    """
```

---

### STEP 3: Integrate Cognitive Workspace in Proxy (5 minutes)

**File:** `scripts/ollama_proxy.py`

**Add import at the top (around line 20-30):**
```python
from contextvault.cognitive import cognitive_workspace
```

**Find the context injection code (around line 160-180):**
```python
# Current simple injection:
context_text = "\n\n".join([entry.content for entry in relevant_entries])

modified_prompt = f"""=== RELEVANT CONTEXT ===
{context_text}

USER QUERY: {prompt}
"""
```

**Replace with:**
```python
# Use Cognitive Workspace for hierarchical memory management
try:
    formatted_context, workspace_stats = cognitive_workspace.load_query_context(
        query=prompt,
        relevant_memories=[{
            "id": entry.id,
            "content": entry.content,
            "metadata": entry.entry_metadata or {},
            "relevance_score": getattr(entry, 'relevance_score', 0.5)
        } for entry in relevant_entries]
    )
    
    logger.info(f"Cognitive Workspace stats: {workspace_stats}")
    modified_prompt = formatted_context
    
except Exception as e:
    logger.warning(f"Cognitive Workspace failed, using fallback: {e}")
    # Fallback to simple injection
    context_text = "\n\n".join([entry.content for entry in relevant_entries])
    modified_prompt = f"""=== RELEVANT CONTEXT ===
{context_text}

USER QUERY: {prompt}
"""
```

---

### STEP 4: Update Config for New Features (3 minutes)

**File:** `contextvault/config.py`

**Add these settings to the Settings class (around line 30-50):**
```python
    # Mem0 Configuration
    use_mem0: bool = False  # Set to True to enable Mem0
    mem0_api_key: Optional[str] = None
    
    # Qdrant Configuration
    use_qdrant: bool = False  # Set to True to use Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "ai_memory"
    
    # Background Maintenance
    enable_maintenance: bool = True
    maintenance_interval_hours: int = 24
    
    # Cognitive Workspace
    enable_cognitive_workspace: bool = True
    scratchpad_tokens: int = 8000
    task_buffer_tokens: int = 64000
    episodic_cache_tokens: int = 256000
    
    # Model Support
    supported_models: Dict[str, str] = {
        "ollama": "http://localhost:11434",
        "lmstudio": "http://localhost:1234",
        "localai": "http://localhost:8080"
    }
    default_model: str = "ollama:llama3.1"
```

---

### STEP 5: Reinstall Package (2 minutes)

**Run in terminal:**
```bash
cd /Users/aniksahai/Desktop/contextvault
pip install -e . --force-reinstall --no-deps
```

This makes the `ai-memory` command available.

---

### STEP 6: Test Everything Works (3 minutes)

**Run these commands to verify:**

```bash
# Test new CLI name
ai-memory --help

# Test chat command (should show help)
ai-memory chat --help

# Test feed command
ai-memory feed --help

# Test recall command
ai-memory recall --help

# Test graph-rag commands
contextible graph-rag --help

# Verify system still works
contextible system status

# Test that Cognitive Workspace is active (check logs)
contextible start
# Look for "Cognitive Workspace stats" in logs
```

---

## ✅ VERIFICATION CHECKLIST

After completing steps 1-6, verify:

- [ ] `ai-memory --help` works and shows new commands
- [ ] `ai-memory chat --help` shows chat options
- [ ] `ai-memory feed --help` shows feed options
- [ ] `ai-memory recall --help` shows recall options
- [ ] `contextible graph-rag --help` works
- [ ] `contextible system status` still works (backward compat)
- [ ] Logs show "Cognitive Workspace stats" when proxy runs
- [ ] Old commands still work: `contextible context list`

---

## 📋 EXACT FILE CHANGES NEEDED

### Change 1: `contextvault/cli/main.py`

**Line 21-24, change:**
```python
from contextvault.cli.commands import (
    system, context, permissions, templates,
    test, demo, diagnose, config, setup, mcp, learning
)
```

**To:**
```python
from contextvault.cli.commands import (
    system, context, permissions, templates,
    test, demo, diagnose, config, setup, mcp, learning,
    chat, feed, recall, graph_rag
)
```

**After line 116, add:**
```python
cli.add_command(chat.chat)
cli.add_command(feed.feed_command)
cli.add_command(recall.recall_command)
cli.add_command(graph_rag.graph_rag_group)
```

### Change 2: `pyproject.toml`

**Around line 32, change:**
```toml
[project.scripts]
contextible = "contextvault.cli.main:cli"
```

**To:**
```toml
[project.scripts]
ai-memory = "contextvault.cli.main:cli"
contextible = "contextvault.cli.main:cli"
```

### Change 3: `scripts/ollama_proxy.py`

**Add at top (line ~25):**
```python
from contextvault.cognitive import cognitive_workspace
```

**Around line 160-180, replace:**
```python
context_text = "\n\n".join([entry.content for entry in relevant_entries])
```

**With:**
```python
try:
    formatted_context, workspace_stats = cognitive_workspace.load_query_context(
        query=prompt,
        relevant_memories=[{
            "id": entry.id,
            "content": entry.content,
            "metadata": entry.entry_metadata or {},
            "relevance_score": getattr(entry, 'relevance_score', 0.5)
        } for entry in relevant_entries]
    )
    logger.info(f"Cognitive Workspace: {workspace_stats}")
    context_text = formatted_context
except Exception as e:
    logger.warning(f"Workspace fallback: {e}")
    context_text = "\n\n".join([entry.content for entry in relevant_entries])
```

### Change 4: `contextvault/config.py`

**Add to Settings class:**
```python
use_mem0: bool = False
enable_cognitive_workspace: bool = True
enable_maintenance: bool = True
```

---

## 🚀 AFTER MAKING CHANGES

**Reinstall:**
```bash
cd /Users/aniksahai/Desktop/contextvault
pip install -e . --force-reinstall --no-deps
```

**Test:**
```bash
ai-memory --help
ai-memory chat --help
contextible system status
```

**Restart proxy:**
```bash
contextible stop
contextible start
# Check logs for "Cognitive Workspace stats"
```

---

## ⏱️ TIME ESTIMATE

- Step 1: 5 minutes (edit main.py)
- Step 2: 2 minutes (edit pyproject.toml)
- Step 3: 5 minutes (edit ollama_proxy.py)
- Step 4: 3 minutes (edit config.py)
- Step 5: 2 minutes (reinstall)
- Step 6: 3 minutes (test)

**Total: 20 minutes**

---

## 🎯 SUCCESS CRITERIA

You'll know it works when:

1. `ai-memory --help` shows these commands:
   - chat
   - feed
   - recall
   - graph-rag
   
2. `ai-memory chat` starts interactive mode

3. Proxy logs show:
   ```
   INFO: Cognitive Workspace stats: {'total_tokens': 12450, ...}
   ```

4. All old commands still work:
   ```bash
   contextible context list
   contextible permissions list
   ```

---

## 📝 NOTES

- **Backward Compatible**: `contextible` command still works
- **Graceful Degradation**: If Mem0/Qdrant not installed, falls back to SQLite
- **Optional Features**: Graph RAG requires Neo4j (shows helpful message if not available)
- **No Breaking Changes**: All existing functionality preserved

---

**Copy this prompt and execute the 6 steps manually, or paste into Claude to do it automatically.**

