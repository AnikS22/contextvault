# Transformation Roadmap: ContextVault → Universal AI Memory CLI

## 🎯 **YOUR VISION vs CURRENT REALITY**

### **What You Want:**
Universal AI Memory CLI that:
- Works with ANY local model (Ollama, LMStudio, LocalAI, llamafile)
- Cognitive Workspace with 3-layer buffers (8K/64K/256K)
- Mem0 + Qdrant + NetworkX knowledge graphs
- Background memory consolidation
- Metacognitive attention management
- Session state restoration
- Simple commands: `ai-memory chat`, `ai-memory feed`, `ai-memory recall`

### **What You Have:**
ContextVault - Traditional RAG system that:
- ✅ Works with Ollama only
- ⚠️ Has Cognitive Workspace code (not integrated)
- ❌ Uses custom VaultService (not Mem0)
- ⚠️ Has NetworkX installed (no knowledge graphs built)
- ⚠️ Has Graph RAG code (not integrated)
- ❌ No background consolidation
- ⚠️ Has attention manager code (not active)
- ❌ Different CLI structure (`contextible` not `ai-memory`)

---

## 📋 **WHAT NEEDS TO CHANGE**

### **CRITICAL CHANGES (Make It Match Your Vision):**

#### 1. **Universal Model Support** ❌ MISSING
**Current:** Only Ollama proxy
**Need:** Universal wrapper for all models

**Changes Required:**
```python
# Create: contextvault/models/universal_wrapper.py

class UniversalModelWrapper:
    def __init__(self, model_type: str, endpoint: str):
        if model_type == "ollama":
            self.client = OllamaClient(endpoint)
        elif model_type == "lmstudio":
            self.client = LMStudioClient(endpoint)
        elif model_type == "localai":
            self.client = LocalAIClient(endpoint)
        elif model_type == "llamafile":
            self.client = LlamafileClient(endpoint)
    
    async def generate(self, prompt: str, **kwargs):
        # Unified interface
        return await self.client.generate(prompt, **kwargs)
```

**Files to Create:**
- `contextvault/models/universal_wrapper.py`
- `contextvault/models/lmstudio_client.py`
- `contextvault/models/localai_client.py`
- `contextvault/models/llamafile_client.py`

**Effort:** 8-12 hours

---

#### 2. **Integrate Cognitive Workspace** ⚠️ EXISTS, NOT ACTIVE
**Current:** Code exists in `contextvault/cognitive/workspace.py` (671 lines)
**Need:** Actually use it in production

**Changes Required:**

**File:** `scripts/ollama_proxy.py` (or new universal proxy)

```python
# CURRENT (line ~160):
context_text = "\n\n".join([entry.content for entry in relevant_entries])
modified_prompt = f"Context: {context_text}\n\nUser: {prompt}"

# CHANGE TO:
from contextvault.cognitive import cognitive_workspace

formatted_context, stats = cognitive_workspace.load_query_context(
    query=prompt,
    relevant_memories=[{
        "id": e.id,
        "content": e.content,
        "metadata": e.entry_metadata,
        "relevance_score": getattr(e, 'relevance_score', 0.5)
    } for e in relevant_entries]
)

modified_prompt = formatted_context  # Already formatted by workspace
```

**Result:** Activates 3-layer buffers + attention management

**Effort:** 15 minutes

---

#### 3. **Replace VaultService with Mem0** ❌ NOT IMPLEMENTED
**Current:** Custom `VaultService` with SQLite
**Need:** Mem0 universal memory layer

**Changes Required:**

**Install:**
```bash
pip install mem0ai qdrant-client
```

**Create:** `contextvault/services/mem0_service.py`

```python
from mem0 import Memory

class Mem0Service:
    def __init__(self):
        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "host": "localhost",
                    "port": 6333,
                }
            },
            "llm": {
                "provider": "ollama",
                "config": {
                    "model": "llama3.1:latest",
                }
            }
        }
        self.memory = Memory.from_config(config)
    
    def add(self, content: str, user_id: str = "default"):
        return self.memory.add(content, user_id=user_id)
    
    def search(self, query: str, user_id: str = "default", limit: int = 10):
        return self.memory.search(query, user_id=user_id, limit=limit)
    
    def get_all(self, user_id: str = "default"):
        return self.memory.get_all(user_id=user_id)
```

**Migration Strategy:**
- Keep VaultService for backward compatibility
- Add Mem0Service as optional backend
- Config flag: `use_mem0: true/false`

**Effort:** 4-6 hours

---

#### 4. **Build Knowledge Graphs** ⚠️ CODE EXISTS, NOT INTEGRATED
**Current:** Graph RAG code exists, not used
**Need:** Active knowledge graph with NetworkX

**You Already Have:**
- `contextvault/storage/graph_db.py` (689 lines) - Neo4j integration
- NetworkX installed

**Changes Required:**

**File:** `contextvault/services/knowledge_graph.py`

```python
import networkx as nx
from typing import List, Dict, Any

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.MultiDiGraph()
    
    def add_entity(self, entity: str, entity_type: str, metadata: Dict):
        self.graph.add_node(entity, type=entity_type, **metadata)
    
    def add_relationship(self, source: str, target: str, relation: str):
        self.graph.add_edge(source, target, relation=relation)
    
    def find_related(self, entity: str, depth: int = 2) -> List[Dict]:
        # Multi-hop traversal
        return list(nx.ego_graph(self.graph, entity, radius=depth))
    
    def get_context_path(self, entity1: str, entity2: str) -> List:
        # Find shortest path
        return nx.shortest_path(self.graph, entity1, entity2)
```

**Integration:**
- Hook into document ingestion
- Extract entities with spaCy (you have it)
- Build graph automatically
- Use in context retrieval

**Effort:** 6-8 hours

---

#### 5. **Background Memory Consolidation** ❌ NOT IMPLEMENTED
**Current:** Manual memory addition only
**Need:** Automatic consolidation, pattern detection, forgetting

**Changes Required:**

**Create:** `contextvault/services/consolidation.py`

```python
import asyncio
from datetime import datetime, timedelta

class MemoryConsolidator:
    def __init__(self, memory_service, interval_hours: int = 24):
        self.memory_service = memory_service
        self.interval_hours = interval_hours
    
    async def start_background_consolidation(self):
        """Run consolidation in background"""
        while True:
            await asyncio.sleep(self.interval_hours * 3600)
            await self.consolidate()
    
    async def consolidate(self):
        """Consolidate memories"""
        # 1. Detect patterns
        patterns = self.detect_patterns()
        
        # 2. Merge similar memories
        self.merge_similar_entries()
        
        # 3. Apply forgetting curves
        self.apply_forgetting_curve()
        
        # 4. Update knowledge graph
        self.update_knowledge_graph()
    
    def detect_patterns(self):
        """Find frequently co-occurring context"""
        # Cluster analysis on embeddings
        pass
    
    def merge_similar_entries(self):
        """Deduplicate similar memories"""
        # Cosine similarity > 0.95 → merge
        pass
    
    def apply_forgetting_curve(self):
        """Archive/remove old memories"""
        # Ebbinghaus forgetting curve
        cutoff = datetime.now() - timedelta(days=90)
        # Reduce access weight for old entries
        pass
```

**Start in background:**
```python
# In main.py
consolidator = MemoryConsolidator(memory_service)
asyncio.create_task(consolidator.start_background_consolidation())
```

**Effort:** 8-10 hours

---

#### 6. **Session State Management** ⚠️ BASIC, NEEDS ENHANCEMENT
**Current:** Session tracking exists, no state restoration
**Need:** Full workspace state save/restore

**Changes Required:**

**File:** `contextvault/services/session_manager.py`

```python
class SessionManager:
    def __init__(self, workspace: CognitiveWorkspace):
        self.workspace = workspace
    
    def save_session(self, session_id: str):
        """Save complete workspace state"""
        state = {
            "session_id": session_id,
            "timestamp": datetime.now(),
            "scratchpad": self.workspace.scratchpad.items,
            "task_buffer": self.workspace.task_buffer.items,
            "episodic_cache": self.workspace.episodic_cache.items,
            "attention_history": list(self.workspace.attention_manager.attention_history)
        }
        # Save to SQLite sessions table
        self._persist_state(state)
    
    def restore_session(self, session_id: str):
        """Restore workspace from saved state"""
        state = self._load_state(session_id)
        
        # Restore buffers
        self.workspace.scratchpad.items = state["scratchpad"]
        self.workspace.task_buffer.items = state["task_buffer"]
        self.workspace.episodic_cache.items = state["episodic_cache"]
        
        # Restore attention
        self.workspace.attention_manager.attention_history = deque(
            state["attention_history"], maxlen=100
        )
```

**Usage:**
```python
# Save after each interaction
session_manager.save_session("alignment_research")

# Restore next day
session_manager.restore_session("alignment_research")
```

**Effort:** 3-4 hours

---

#### 7. **Rename CLI to `ai-memory`** ⚠️ COSMETIC CHANGE
**Current:** `contextible`
**Need:** `ai-memory`

**Changes Required:**

**File:** `pyproject.toml`

```toml
# CURRENT:
[project.scripts]
contextible = "contextvault.cli.main:cli"

# CHANGE TO:
[project.scripts]
ai-memory = "contextvault.cli.main:cli"
contextible = "contextvault.cli.main:cli"  # Keep for backward compat
```

**File:** `contextvault/cli/main.py`

```python
# Update help text
@click.group()
def cli():
    """
    ✨ AI Memory - Universal Memory for Local AI Models ✨
    
    Transform any local AI into a context-aware assistant that never forgets.
    """
```

**Effort:** 15 minutes

---

#### 8. **Restructure CLI Commands** ⚠️ NEEDS REORGANIZATION
**Current:** `contextible context add`, `contextible start`
**Need:** `ai-memory chat`, `ai-memory feed`, `ai-memory recall`

**Changes Required:**

**File:** `contextvault/cli/main.py`

```python
# ADD NEW COMMANDS:

@cli.command()
@click.argument('query', required=False)
@click.option('--session', help='Session name for persistent conversations')
@click.option('--model', default='ollama:llama3.1', help='Model to use')
def chat(query, session, model):
    """Chat with AI using persistent memory."""
    # Interactive mode if no query
    if not query:
        interactive_chat_loop(session, model)
    else:
        single_query(query, session, model)

@cli.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True))
def feed(files):
    """Add documents to AI memory."""
    for file_path in files:
        ingest_document(file_path)
        console.print(f"✅ Added {file_path} to memory")

@cli.command()
@click.argument('query')
@click.option('--limit', default=10)
def recall(query, limit):
    """Search memory directly without AI."""
    results = memory_service.search(query, limit=limit)
    display_results(results)
```

**Keep existing commands for compatibility**

**Effort:** 2-3 hours

---

#### 9. **Add Model Selection** ❌ NOT IMPLEMENTED
**Current:** Hardcoded Ollama
**Need:** `--model` flag for any model

**Changes Required:**

**File:** `contextvault/config.py`

```python
class Settings(BaseSettings):
    # CURRENT:
    ollama_host: str = "127.0.0.1"
    ollama_port: int = 11434
    
    # ADD:
    active_model: str = "ollama:llama3.1:latest"  # Format: provider:model:tag
    
    model_endpoints: Dict[str, str] = {
        "ollama": "http://localhost:11434",
        "lmstudio": "http://localhost:1234",
        "localai": "http://localhost:8080",
        "llamafile": "/path/to/llamafile"
    }
```

**Usage:**
```bash
ai-memory chat --model ollama:llama3.1
ai-memory chat --model lmstudio:mistral:latest
ai-memory chat --model llamafile:/path/to/model.llamafile
```

**Effort:** 3-4 hours

---

#### 10. **Add Qdrant/FAISS Vector Store** ⚠️ PARTIALLY EXISTS
**Current:** Chroma exists but not used, sentence-transformers in-memory
**Need:** Qdrant or FAISS for production

**Changes Required:**

**Install:**
```bash
pip install qdrant-client
# OR
pip install faiss-cpu
```

**File:** `contextvault/services/vector_store.py`

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

class QdrantVectorStore:
    def __init__(self):
        self.client = QdrantClient("localhost", port=6333)
        self.collection_name = "ai_memory"
        self._init_collection()
    
    def _init_collection(self):
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
    
    def add(self, vectors, payloads, ids):
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                {"id": id_, "vector": vector, "payload": payload}
                for id_, vector, payload in zip(ids, vectors, payloads)
            ]
        )
    
    def search(self, query_vector, limit=10):
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit
        )
```

**OR use FAISS (no server needed):**

```python
import faiss
import numpy as np

class FAISSVectorStore:
    def __init__(self, dimension=384):
        self.index = faiss.IndexFlatL2(dimension)
        self.id_map = []
    
    def add(self, vectors, ids):
        self.index.add(np.array(vectors))
        self.id_map.extend(ids)
    
    def search(self, query_vector, limit=10):
        D, I = self.index.search(np.array([query_vector]), limit)
        return [(self.id_map[i], D[0][idx]) for idx, i in enumerate(I[0])]
```

**Effort:** 2-3 hours

---

## 📊 **PRIORITY MATRIX**

### **Phase 1: Activate Existing Code (2-3 hours)**
1. ✅ Integrate Cognitive Workspace (15 min)
2. ✅ Register feed/recall commands (30 min)
3. ✅ Rename to `ai-memory` (15 min)
4. ✅ Update CLI structure (2 hours)

**Result:** Your vision 60% complete

---

### **Phase 2: Core Architecture (10-15 hours)**
5. ✅ Add Mem0 integration (4-6 hours)
6. ✅ Build universal model wrapper (8-12 hours)
7. ✅ Add Qdrant/FAISS (2-3 hours)

**Result:** Your vision 85% complete

---

### **Phase 3: Advanced Features (15-20 hours)**
8. ✅ Session state management (3-4 hours)
9. ✅ Knowledge graph integration (6-8 hours)
10. ✅ Background consolidation (8-10 hours)

**Result:** Your vision 100% complete

---

## 🎯 **QUICK WIN PATH (Get 60% There in 3 Hours)**

If you want to activate what you have NOW:

### **Step 1: Integrate Cognitive Workspace (15 min)**
```python
# Edit: scripts/ollama_proxy.py or create new universal_proxy.py
from contextvault.cognitive import cognitive_workspace

# Replace line ~160 with workspace integration
formatted_context, stats = cognitive_workspace.load_query_context(
    query=prompt,
    relevant_memories=memories
)
```

### **Step 2: Register Commands (30 min)**
```python
# Edit: contextvault/cli/main.py
from contextvault.cli.commands import feed, recall, graph_rag

cli.add_command(feed.feed_command)
cli.add_command(recall.recall_command)
cli.add_command(graph_rag.graph_rag_group)
```

### **Step 3: Rename CLI (15 min)**
```python
# Edit: pyproject.toml
[project.scripts]
ai-memory = "contextvault.cli.main:cli"
```

### **Step 4: Add Chat Command (2 hours)**
```python
# Create: contextvault/cli/commands/chat.py
@click.command()
@click.argument('query', required=False)
@click.option('--session')
def chat(query, session):
    """Interactive chat with memory."""
    # Implement chat loop
```

**Reinstall:**
```bash
pip install -e .
ai-memory --help  # Works!
```

---

## 🚀 **RECOMMENDED APPROACH**

### **Option A: Incremental (Safe)**
1. Activate existing features (3 hours)
2. Test with users
3. Add Mem0 (4-6 hours)
4. Test with users
5. Add universal models (8-12 hours)
6. Add advanced features (15-20 hours)

**Total: 30-41 hours over 2-3 weeks**

### **Option B: Big Bang (Fast)**
1. Build everything at once
2. Test comprehensively
3. Release complete system

**Total: 30-41 hours over 1 week**

---

## 📋 **CHECKLIST: Transform ContextVault → Universal AI Memory**

### **Architecture:**
- [ ] Integrate Cognitive Workspace (you have it!)
- [ ] Add Mem0 memory layer
- [ ] Add Qdrant or FAISS vector store
- [ ] Build universal model wrapper
- [ ] Integrate knowledge graphs (you have code!)
- [ ] Add background consolidation
- [ ] Enhance session management

### **CLI:**
- [ ] Rename to `ai-memory`
- [ ] Add `chat` command (interactive)
- [ ] Activate `feed` command (you have it!)
- [ ] Activate `recall` command (you have it!)
- [ ] Add `status` command
- [ ] Add `reset` command
- [ ] Add `--model` flag

### **Features:**
- [ ] Multi-model support (Ollama/LMStudio/LocalAI/llamafile)
- [ ] 3-layer memory buffers (code exists!)
- [ ] Attention management (code exists!)
- [ ] Forgetting curves (code exists!)
- [ ] Knowledge graph traversal
- [ ] Session state save/restore
- [ ] Background consolidation

### **Polish:**
- [ ] Config file for settings
- [ ] Comprehensive error handling
- [ ] Beautiful Rich terminal output (you have this!)
- [ ] Logging system
- [ ] Performance optimization
- [ ] Documentation updates
- [ ] Example usage demos

---

## 💡 **THE GOOD NEWS**

**You're 60% there!** You have:
- ✅ Cognitive Workspace (complete!)
- ✅ Graph RAG foundation
- ✅ Attention manager
- ✅ Forgetting curves
- ✅ Feed/recall commands
- ✅ Beautiful CLI

**You just need:**
- ⚡ Integration (wire up existing code)
- 🔌 Universal model wrapper
- 📦 Mem0 + Qdrant
- 🔄 Background processes

---

## 🎓 **BOTTOM LINE**

**To transform ContextVault into your vision:**

**Quick (3 hours):** Activate existing code → 60% there
**Medium (15 hours):** Add Mem0 + universal models → 85% there  
**Full (40 hours):** Complete system with all features → 100% there

**You have more built than you realized!**

