# 🚀 Quick Start Guide - For Complete Beginners

**You just downloaded Ollama. Here's how to give it superpowers with AI Memory.**

---

## 🎯 What Does This Actually Do?

**THE PROBLEM:**
```bash
# Without AI Memory - Ollama forgets everything:
$ ollama run llama3.1
>>> My name is Alice and I love Python
AI: Nice to meet you Alice!

>>> What's my name?  
AI: I don't have information about your name.  # ❌ It forgot!
```

**THE SOLUTION:**
```bash
# With AI Memory - Ollama remembers forever:
$ ai-memory chat
You: My name is Alice and I love Python
AI: Nice to meet you Alice!

You: What's my name?
AI: Your name is Alice, and I know you love Python!  # ✅ It remembers!
```

**AI Memory = Giving Ollama a photographic memory**

---

## 📋 Complete Setup (5 Minutes)

### **Step 1: Install Ollama** (if you haven't)
```bash
# Download from: https://ollama.ai
# Or on macOS:
brew install ollama

# Start Ollama
ollama serve

# Pull a model
ollama pull llama3.1
```

### **Step 2: Install AI Memory**
```bash
# Clone the repo
git clone https://github.com/AnikS22/contextvault.git
cd contextvault

# Install dependencies
pip install -r requirements.txt

# Initialize AI Memory
ai-memory setup
```

### **Step 3: Start AI Memory**
```bash
ai-memory start
```

That's it! You now have a memory-enhanced AI.

---

## 💬 How To Use It - Real Examples

### **Example 1: Teaching Your AI About You**

```bash
# Option A: Tell it directly
$ ai-memory context add "I'm a software engineer at Google"
$ ai-memory context add "I drive a Tesla Model 3"
$ ai-memory context add "I have two cats: Luna and Pixel"

# Option B: Use interactive chat (it learns automatically)
$ ai-memory chat

You: I'm a software engineer at Google
AI: Nice to meet you! What kind of work do you do at Google?

You: I work on AI safety and alignment
AI: That's fascinating work! AI safety is crucial.

# AI Memory automatically saves this conversation
```

### **Example 2: Uploading Documents**

```bash
# Feed your research papers, notes, or any documents
$ ai-memory feed research_paper.pdf
$ ai-memory feed notes.md meeting_notes.txt
$ ai-memory feed documents/ --recursive

# Now AI knows everything in those documents!
```

### **Example 3: Searching Your Memory**

```bash
# Search what you've told it
$ ai-memory recall "my cats"

Results:
  1. I have two cats: Luna and Pixel
  2. Luna is a tabby cat
  3. Pixel loves playing with string toys

# Search documents you uploaded
$ ai-memory recall "AI alignment" --limit 5
```

### **Example 4: Interactive Chat With Memory**

```bash
$ ai-memory chat

You: What do you know about me?
AI: Based on our previous conversations, you're a software engineer at 
    Google working on AI safety and alignment. You drive a Tesla Model 3 
    and have two cats named Luna and Pixel.

You: What car should I buy next?
AI: Given that you currently drive a Tesla Model 3 and seem to enjoy 
    electric vehicles, you might consider the Tesla Model Y for more space, 
    or perhaps the Rivian R1T if you want something different.

# It remembers your Tesla! 🎉
```

---

## 🔄 How It Actually Works (Behind The Scenes)

### **Normal Ollama (Without AI Memory):**

```
You → Ollama
     "What are my hobbies?"
     
Ollama: "I don't have any information about your hobbies."
```

Ollama has NO memory. Every conversation starts from scratch.

---

### **With AI Memory:**

```
You → AI Memory Proxy → Ollama
     "What are my hobbies?"

AI Memory intercepts and adds context:
  1. Searches its database: "hobbies"
  2. Finds: "I love hiking" and "I play guitar"
  3. Whispers to Ollama:
     "CONTEXT: User loves hiking and plays guitar
      USER QUESTION: What are my hobbies?"

Ollama → Response
     "Based on our conversations, you love hiking and playing guitar!"
```

**AI Memory sits between you and Ollama, secretly feeding it your history.**

---

## 🎨 Advanced Features

### **1. Memory Management**

```bash
# See what AI knows about you
$ ai-memory context list

# Search specific topics
$ ai-memory context search "python"

# See statistics
$ ai-memory context stats

# Delete something
$ ai-memory context delete <id>
```

### **2. Control What AI Can See (Permissions)**

```bash
# Give a model permission to see your personal info
$ ai-memory permissions add llama3.1 --scope personal,work

# Different models can see different things!
# Work model only sees work context
# Personal model sees everything
```

### **3. Graph RAG (Understands Relationships)**

*Requires Neo4j server (optional)*

```bash
# Start Neo4j
docker run -d -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j

# Add context with relationship extraction
$ ai-memory graph-rag add "Bob Smith works at Acme Corp as CEO" --id doc1

# Search with relationships
$ ai-memory graph-rag search "Acme Corp"

Results:
  - Bob Smith (WORKS_AT) → Acme Corp
  - Bob Smith (POSITION) → CEO
  
# Get all relationships for an entity
$ ai-memory graph-rag entity "Bob Smith"

Relationships:
  Bob Smith → WORKS_AT → Acme Corp
  Bob Smith → POSITION → CEO
```

---

## 🔍 What Makes It Special?

### **1. Cognitive Workspace (ACTIVE NOW!)**

Your AI doesn't just dump all context into the prompt. It organizes it:

```
When you ask: "What are my projects?"

Cognitive Workspace organizes memories:
  
  ┌─────────────────────────────────────┐
  │ IMMEDIATE CONTEXT (8K tokens)       │ ← Highest priority
  │ • Current query                     │
  │ • Most relevant recent info         │
  └─────────────────────────────────────┘
  
  ┌─────────────────────────────────────┐
  │ TASK BUFFER (64K tokens)            │ ← Medium priority
  │ • Project-specific context          │
  │ • Related conversations             │
  └─────────────────────────────────────┘
  
  ┌─────────────────────────────────────┐
  │ EPISODIC CACHE (256K tokens)        │ ← Background
  │ • All historical context            │
  │ • Full document corpus              │
  └─────────────────────────────────────┘
```

**Result:** AI focuses on what matters, with background knowledge ready.

### **2. Attention Management**

Not all memories are equal:

```python
High attention (>0.7):
  - Recent conversations (last 24h)
  - Frequently accessed info
  - High relevance to current query
  → Goes in SCRATCHPAD

Medium attention (0.3-0.7):
  - Related but not immediate
  - Session-specific context
  → Goes in TASK BUFFER

Low attention (<0.3):
  - Background knowledge
  - Old conversations
  → Goes in EPISODIC CACHE
```

### **3. Forgetting Curves**

Old, unused memories naturally fade:

```
Day 1: Memory strength = 100%
Day 30 (no access): Memory strength = 50%
Day 90 (no access): Memory strength = 20%
Day 365 (no access): Memory archived
```

**But frequently accessed memories stay strong!**

---

## 📚 Common Use Cases

### **Use Case 1: Personal Assistant**

```bash
# Teach it about you
$ ai-memory context add "I prefer email over Slack"
$ ai-memory context add "My work hours are 9-5 EST"
$ ai-memory context add "I'm allergic to peanuts"

# Now ask
$ ai-memory chat

You: How should someone contact me?
AI: Based on your preferences, email is better than Slack. Your work 
    hours are 9-5 EST, so that's the best time to reach you.

You: Can I eat this peanut butter cookie?
AI: No! You're allergic to peanuts. That wouldn't be safe.
```

### **Use Case 2: Research Assistant**

```bash
# Feed all your research papers
$ ai-memory feed research/ --recursive --pattern "*.pdf"

# Now ask questions
$ ai-memory chat

You: What are the key findings about constitutional AI?
AI: Based on your uploaded papers, constitutional AI has three main 
    approaches: [summarizes from YOUR papers]

# It read your 50 PDFs and remembers all of them!
```

### **Use Case 3: Project Memory**

```bash
# Different projects = different memories
$ ai-memory chat --session project_alpha

You: This project uses React and TypeScript
AI: Got it, I'll remember that for project_alpha.

# Later, different project:
$ ai-memory chat --session project_beta

You: This project uses Django and Python
AI: Understood, project_beta uses Django and Python.

# Switch back:
$ ai-memory chat --session project_alpha

You: What tech stack am I using?
AI: For project_alpha, you're using React and TypeScript.

# It remembers per-project context!
```

---

## 🛠️ Troubleshooting

### **"Context injection not working"**

```bash
# Check status
$ ai-memory system status

# Make sure proxy is running
$ ai-memory start

# Test with Ollama
$ curl http://localhost:11435/api/generate -d '{
  "model":"llama3.1",
  "prompt":"What do you know about me?",
  "stream":false
}'

# Should include your context!
```

### **"Commands not found"**

```bash
# Reinstall package
$ pip install -e . --force-reinstall

# Verify
$ ai-memory --help
```

### **"Graph RAG not working"**

```bash
# Start Neo4j
$ docker run -d -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j

# Wait 30 seconds for Neo4j to start

# Test
$ ai-memory graph-rag health

# Should show: ✅ Neo4j connected
```

---

## 📖 Command Reference Card

```bash
# BASIC USAGE
ai-memory setup                        # First-time setup
ai-memory start                        # Start the proxy
ai-memory chat                         # Interactive chat
ai-memory chat "quick question"        # Single question

# MEMORY MANAGEMENT
ai-memory context add "text"           # Add memory manually
ai-memory context list                 # See all memories
ai-memory context search "keyword"     # Search memories
ai-memory context stats                # Statistics

# DOCUMENT INGESTION
ai-memory feed file.txt                # Add one file
ai-memory feed *.pdf                   # Add multiple files
ai-memory feed folder/ --recursive     # Add entire folder

# MEMORY SEARCH
ai-memory recall "search query"        # Search directly
ai-memory recall "python" --limit 5    # Limit results

# PERMISSIONS
ai-memory permissions list             # See what models can access
ai-memory permissions add llama3.1     # Grant permissions

# GRAPH RAG (requires Neo4j)
ai-memory graph-rag init               # Initialize graph
ai-memory graph-rag add "text" --id 1  # Add with entity extraction
ai-memory graph-rag search "query"     # Search graph
ai-memory graph-rag entity "Alice"     # Get relationships

# SYSTEM
ai-memory system status                # Check health
ai-memory start                        # Start proxy
ai-memory stop                         # Stop proxy
```

---

## 🎯 Real-World Workflow

**Morning:**
```bash
# Start AI Memory
$ ai-memory start

# Add today's notes
$ ai-memory feed meeting_notes.txt todo_list.md

# Check what's on your plate
$ ai-memory chat

You: What are my tasks for today?
AI: Based on your todo list, you have:
    1. Code review for PR #123
    2. Team meeting at 2 PM
    3. Finish documentation for project_alpha
```

**During Work:**
```bash
# Keep chatting, it remembers everything
You: What did I discuss in this morning's meeting?
AI: In this morning's meeting, you discussed...
    [pulls from meeting_notes.txt you uploaded]
```

**Evening:**
```bash
# Add what you accomplished
$ ai-memory context add "Completed PR #123 review" --type work

# Exit
$ ai-memory stop
```

**Next Day:**
```bash
$ ai-memory start
$ ai-memory chat

You: What did I work on yesterday?
AI: Yesterday you completed the code review for PR #123, attended 
    the team meeting, and worked on project_alpha documentation.

# It remembers! 🎉
```

---

## 💡 Pro Tips

### **Tip 1: Use Tags**
```bash
$ ai-memory context add "Python 3.12 released" --tags "news,python"
$ ai-memory context add "Meeting with Bob" --tags "work,meetings"

# Later search by tag
$ ai-memory context search "python" 
# Finds everything tagged "python"
```

### **Tip 2: Use Sessions**
```bash
# Work context
$ ai-memory chat --session work

# Personal context  
$ ai-memory chat --session personal

# Each session has separate memory!
```

### **Tip 3: Feed Entire Folders**
```bash
# Add all your documents at once
$ ai-memory feed ~/Documents/Research/ --recursive --pattern "*.pdf"

# AI now knows everything in that folder!
```

### **Tip 4: Check What AI Knows**
```bash
# Before asking AI, check memory directly
$ ai-memory recall "my preferences"

# See everything
$ ai-memory context list --limit 50
```

---

## 🔬 Technical: How The Proxy Works

```
┌─────────────────────────────────────────────────────────────┐
│  YOUR SETUP                                                 │
└─────────────────────────────────────────────────────────────┘

Normal Ollama:
   Your App → http://localhost:11434 → Ollama

With AI Memory:
   Your App → http://localhost:11435 → AI Memory → Ollama
                     ↑
                 (port 11435)
```

**What happens:**

1. You send request to **port 11435** (AI Memory proxy)
2. AI Memory:
   - Extracts your question
   - Searches its database for relevant memories
   - Uses Cognitive Workspace to organize (3-layer buffers)
   - Computes attention weights
   - Adds top memories to your prompt
3. Forwards enhanced prompt to **port 11434** (Ollama)
4. Ollama responds using the context
5. AI Memory returns response to you
6. AI Memory saves the conversation

**You just change the port number** and get superpowers!

---

## 🎮 Interactive Chat Demo

```bash
$ ai-memory chat

╭──────────────────────────────────────╮
│ 💬 AI Memory Chat                    │
│ Model: llama3.1                      │
│ Session: default                     │
│ Memory: 480 entries                  │
│                                      │
│ Type 'exit' to quit                  │
╰──────────────────────────────────────╯

You: Hi, I'm starting a new project using Python and FastAPI

AI: Great choice! Python and FastAPI are excellent for building 
    APIs. What kind of project are you building?

You: An AI memory system for local models

AI: That sounds interesting! You mentioned you love Python, so 
    this project aligns well with your interests.
    [It remembered you love Python from earlier!]

You: What tech stack am I using again?

AI: For this project, you're using Python and FastAPI.

You: exit

💾 Saving conversation...
👋 Goodbye! All memories saved.
```

---

## 📊 What The Cognitive Workspace Does

**Without Cognitive Workspace** (old RAG):
```
Your question → Search database → Dump ALL 50 results into prompt
→ AI tries to process everything at once
→ Important stuff gets lost in noise
```

**With Cognitive Workspace** (NOW ACTIVE!):
```
Your question → Search database → Cognitive Workspace organizes:

IMMEDIATE SCRATCHPAD (8K tokens):
  ✅ Your current question
  ✅ Most relevant recent info (high attention >0.7)

TASK BUFFER (64K tokens):
  ✅ Related project context (medium attention 0.3-0.7)
  ✅ Session-specific memories

EPISODIC CACHE (256K tokens):
  ✅ Background knowledge (low attention <0.3)
  ✅ Full document corpus

→ AI gets perfectly organized context
→ Focuses on what matters
→ Background knowledge available if needed
```

**Result:** AI responds more accurately with better focus.

---

## 🎯 What You Can Do Now

### **Basic (Works out-of-the-box):**
- ✅ Add memories manually
- ✅ Upload documents (PDFs, text files, markdown)
- ✅ Interactive chat with memory
- ✅ Search your memories
- ✅ Cognitive Workspace (3-layer buffers)
- ✅ Attention management
- ✅ Permission control per model

### **Advanced (Requires Neo4j server):**
- ⚠️ Graph RAG (entity extraction)
- ⚠️ Relationship graphs ("Bob works at Acme")
- ⚠️ Multi-hop reasoning

### **Future (Can enable in config):**
- ⚠️ Mem0 integration (set ENABLE_MEM0=true)
- ⚠️ Background consolidation
- ⚠️ LMStudio/LocalAI support (coming soon)

---

## 🚀 Daily Workflow

**Morning:**
```bash
ai-memory start
ai-memory chat --session today
```

**During Day:**
```bash
# Upload documents as needed
ai-memory feed new_document.pdf

# Chat with full memory
ai-memory chat
```

**Evening:**
```bash
# Add notes about what you did
ai-memory context add "Completed project X" --type work

# Stop when done
ai-memory stop
```

**Next Day:**
```bash
# It remembers everything from yesterday!
ai-memory chat

You: What did I work on yesterday?
AI: Yesterday you completed project X...
```

---

## 💰 Cost & Privacy

**Cost:** $0 (100% free)
- No API fees
- No cloud services
- Runs entirely on your machine

**Privacy:** 100% Local
- Data never leaves your computer
- Stored in local SQLite database
- No telemetry, no tracking
- You own everything

---

## 🎓 Summary

**AI Memory gives Ollama a persistent, organized, searchable memory.**

**Before:** Generic chatbot that forgets everything
**After:** Personal assistant that knows you, remembers your documents, and never forgets

**Setup:** 5 minutes
**Usage:** As simple as `ai-memory chat`
**Benefit:** Infinite memory, zero cost, complete privacy

---

## 🆘 Need Help?

```bash
# System diagnostics
$ ai-memory diagnose run

# Check health
$ ai-memory system status

# See all commands
$ ai-memory --help

# Get command help
$ ai-memory chat --help
```

**That's it!** You now have an AI with a photographic memory. 🧠

