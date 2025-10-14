# 🚀 Contextible Quick Start Guide

Transform your local AI models with persistent memory in 5 minutes!

## ⚡ Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd contextvault

# Install the package
pip install -e .
```

This installs the `contextible` command globally.

## 🎯 First-Time Setup

### 1. Install Ollama (if you don't have it)

**macOS:**
```bash
brew install ollama
```

**Or download from:** https://ollama.ai

### 2. Start Ollama & Pull a Model

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Download a model
ollama pull llama2
```

### 3. Run Setup

```bash
contextible setup
```

This will:
- ✅ Check Python & dependencies
- ✅ Initialize the database
- ✅ Create sample context
- ✅ Set up permissions

## 🎨 Using Contextible

### Start the Proxy

```bash
contextible start
```

Starts Contextible on **port 11435** (Ollama runs on 11434)

### Add Your First Context

```bash
contextible context add "I'm a Python developer who loves FastAPI"
contextible context add "Working on an AI memory system" --type note
```

### Check Status

```bash
contextible system status
```

Beautiful animated status display!

### Search Your Context

```bash
contextible context search "python"
```

Cool animations and color coding!

## 🤖 Using With Your AI

Connect to `localhost:11435` instead of `localhost:11434`:

```bash
curl http://localhost:11435/api/generate -d '{
  "model": "llama2",
  "prompt": "What do I like to code in?"
}'
```

The AI now knows your preferences! 🎉

## 📊 Useful Commands

```bash
contextible start              # Start proxy
contextible system status      # System status
contextible context list       # List context
contextible context search "..." # Search
contextible learning stats     # Learning stats
```

**Enjoy your AI with superpowers! 🚀🧠**
