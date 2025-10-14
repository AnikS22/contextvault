# ContextVault User Guide

**Give your local AI unlimited memory - as easy as Claude Code!**

---

## 🚀 Quick Start (3 Minutes)

### Step 1: Initial Setup
```bash
# Run the setup wizard (it's interactive and easy!)
contextible setup

# Or use quick setup with defaults
contextible quickstart
```

The setup wizard will:
- ✅ Check your Python environment
- ✅ Initialize the database
- ✅ Set up Ollama connection
- ✅ Add sample memories

### Step 2: Start ContextVault
```bash
contextible start
```

That's it! Your AI now has unlimited memory 🧠

---

## 📚 Core Commands (The Easy Ones)

### Adding Documents to Memory
```bash
# Add a single file
contextible feed document.txt

# Add multiple files
contextible feed file1.txt file2.pdf file3.md

# Add entire folder
contextible feed my_documents/ --recursive

# Add specific file types
contextible feed contracts/ --pattern "*.pdf" --type contract
```

### Searching Memory
```bash
# Search for anything
contextible recall "python projects"

# Limit results
contextible recall "contracts" --limit 5

# Filter by type
contextible recall "meetings" --type note

# Show full content (not just preview)
contextible recall "budget" --full
```

### Checking Status
```bash
# System health check
contextible status

# See what's in memory
contextible feed-status

# Show recent documents
contextible recent

# Memory statistics
contextible memory-stats
```

---

## ⚙️ Settings (No Coding Required!)

### View Current Settings
```bash
contextible settings show
```

Shows you everything:
- Database location
- Model connection (Ollama/LMStudio/LocalAI)
- Memory limits
- Performance settings

### Edit Settings Interactively
```bash
contextible settings edit
```

Walks you through changing:
- Model host and port
- Maximum context tokens
- Cache settings
- More...

All with helpful prompts and previews!

### Quick Presets
```bash
# See available presets
contextible settings presets

# Apply a preset instantly
contextible settings apply medium  # Balanced (recommended)
contextible settings apply large   # Maximum context (128K tokens)
contextible settings apply small   # Quick tasks (8K tokens)
```

### Reset to Defaults
```bash
contextible settings reset
```

---

## 🎯 Common Use Cases

### For Business Documents
```bash
# Add all your business docs
contextible feed ~/Documents/Business/ --recursive

# Search when you need info
contextible recall "Q2 revenue projections"
contextible recall "client contracts" --type contract
```

### For Research Papers
```bash
# Add research papers
contextible feed ~/Papers/ --pattern "*.pdf" --recursive

# Search your research
contextible recall "machine learning architectures"
contextible recall "transformer models" --full
```

### For Code Projects
```bash
# Add project documentation
contextible feed ./docs/ --recursive

# Search code docs
contextible recall "API endpoints"
contextible recall "authentication flow"
```

---

## 🔧 Advanced Features

### Configuration Presets

| Preset | Context | Best For |
|--------|---------|----------|
| **tiny** | 4K tokens | Testing |
| **small** | 8K tokens | Quick tasks |
| **medium** | 32K tokens | Daily use (recommended) |
| **large** | 128K tokens | Huge documents (Llama 3.1) |
| **xl** | 256K tokens | Future models |

Apply with: `contextible settings apply <preset>`

### Model Connections

**Ollama (Default)**:
```bash
contextible settings edit
# Set: ollama_host=127.0.0.1, ollama_port=11434
```

**LMStudio**:
```bash
contextible settings edit
# Set: ollama_host=127.0.0.1, ollama_port=1234
```

**LocalAI**:
```bash
contextible settings edit
# Set: ollama_host=127.0.0.1, ollama_port=8080
```

### Performance Tuning

Enable caching for speed:
```bash
contextible settings edit
# Enable caching: Yes
# Cache TTL: 300 seconds (default)
```

---

## 📖 Full Command Reference

### System Commands
```bash
contextible setup          # Initial setup wizard
contextible start          # Start the proxy
contextible stop           # Stop the proxy
contextible status         # System health check
```

### Document Management
```bash
contextible feed <paths>           # Add documents
contextible feed-status            # Storage stats
contextible recall <query>         # Search memory
contextible recent                 # Recent documents
contextible memory-stats           # Memory statistics
```

### Settings Management
```bash
contextible settings show          # View all settings
contextible settings edit          # Interactive editor
contextible settings presets       # Show presets
contextible settings apply <name>  # Apply preset
contextible settings reset         # Reset to defaults
```

### Advanced Commands
```bash
contextible config <action>        # Config management
contextible context <action>       # Legacy context commands
contextible permissions <action>   # Access control
contextible templates <action>     # Template management
contextible diagnose               # Troubleshooting
contextible test                   # Run system tests
```

---

## 💡 Tips & Tricks

### 1. Start Fresh
```bash
contextible setup
contextible settings apply medium
contextible feed ~/Documents/
```

### 2. Quick Status Check
```bash
contextible status && contextible memory-stats
```

### 3. Batch Document Import
```bash
# Add everything at once
contextible feed \
  ~/Documents/Work/ \
  ~/Documents/Personal/ \
  ~/Downloads/*.pdf \
  --recursive
```

### 4. Search with Context
```bash
# Get full details on important matches
contextible recall "important contract" --limit 3 --full
```

### 5. Tune for Your Hardware

**Fast Machine**:
```bash
contextible settings apply large  # Use maximum context
```

**Slower Machine**:
```bash
contextible settings apply small  # Lighter memory usage
```

---

## 🐛 Troubleshooting

### "Vector database not available"
```bash
pip install chromadb
```

### "Ollama not running"
```bash
ollama serve
# In another terminal:
contextible start
```

### "Can't connect to proxy"
Check your proxy port:
```bash
contextible settings show  # Look for proxy_port
# Default is 11435
```

Point your AI client to `http://localhost:11435` instead of `http://localhost:11434`

### Reset Everything
```bash
contextible settings reset
contextible setup
```

---

## 🎓 Learning More

### Built-in Help
```bash
contextible --help
contextible feed --help
contextible settings --help
```

### Documentation
- `README.md` - Project overview
- `IMPLEMENTATION_SUMMARY.md` - Technical details
- `HOW_TO_USE.md` - Step-by-step guide

### Examples
```bash
# Run the demo to see it in action
python scripts/demo_cognitive_system.py
```

---

## 🌟 Why ContextVault?

✅ **Easy to use** - CLI as simple as Claude Code
✅ **No coding needed** - Interactive prompts for everything
✅ **Unlimited memory** - Store thousands of documents
✅ **100% local** - Your data never leaves your computer
✅ **Intelligent** - Automatically finds relevant information
✅ **Fast** - Semantic search across massive corpus in milliseconds
✅ **Flexible** - Works with Ollama, LMStudio, LocalAI

---

## 🆘 Getting Help

**Quick Fixes**:
1. Run `contextible setup` to reconfigure
2. Check `contextible status` for health
3. Try `contextible settings reset` if confused

**Need More Help?**
- Check the built-in help: `contextible --help`
- Run diagnostics: `contextible diagnose`
- View logs: `contextible system logs`

---

## 🎉 You're Ready!

Start using your AI with unlimited memory:

```bash
# 1. Setup (one time)
contextible setup

# 2. Add your documents
contextible feed ~/Documents/ --recursive

# 3. Start the proxy
contextible start

# 4. Use your AI as normal!
# Point it to http://localhost:11435
```

**Your AI now remembers everything!** 🧠✨

---

*Made with ❤️ for easy-to-use AI memory*
