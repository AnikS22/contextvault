# ContextVault 🧠

[![GitHub](https://img.shields.io/badge/GitHub-ContextVault-blue?logo=github)](https://github.com/AnikS22/contextvault)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)

**AI Memory for Local AI Models**

ContextVault gives your local AI models persistent memory, transforming them from generic chatbots into personal assistants that actually know you.

## 🎯 **What is ContextVault?**

ContextVault is a proxy that sits between you and your local AI models (Ollama, etc.) and automatically injects relevant context into every conversation. Your AI suddenly remembers your preferences, projects, pets, and personal details.

### **The Problem ContextVault Solves:**

- **Without ContextVault**: "I don't have personal knowledge about you..."
- **With ContextVault**: "Based on your preferences, you love Python and have two cats named Luna and Pixel..."

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.8+
- [Docker](https://www.docker.com/get-started) (for Neo4j Graph RAG - recommended)
- [Ollama](https://ollama.ai) installed and running
- At least one Ollama model (e.g., `ollama pull mistral:latest`)

### **Installation**

```bash
# Clone the repository
git clone https://github.com/AnikS22/contextvault.git
cd contextvault

# Install dependencies
pip install -r requirements.txt

# Start Neo4j for Graph RAG (Primary Retrieval System)
docker run -d --name contextvault-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# Initialize ContextVault
python -m contextvault.cli setup

# Start the proxy
python -m contextvault.cli start
```

> **Note**: ContextVault uses **Graph RAG** as the primary retrieval system by default. Neo4j is required for full functionality. The system will gracefully fall back to semantic search if Neo4j is unavailable.

### **Test It Works**

```bash
# Test ContextVault is working
python -m contextvault.cli test

# Run a demo
python -m contextvault.cli demo
```

### **Add Knowledge to Graph RAG**

ContextVault uses Graph RAG for intelligent context retrieval with entity extraction and relationship mapping:

```bash
# Add documents with automatic entity extraction
python -m contextvault.cli graph-rag add \
  "John Smith works at Acme Corp as a Software Engineer in San Francisco" \
  --id doc1

python -m contextvault.cli graph-rag add \
  "Acme Corp raised $50M in Series A funding from Venture Partners" \
  --id doc2

# Search with entity-aware retrieval
python -m contextvault.cli graph-rag search "Acme Corp" --show-entities

# Check entity relationships
python -m contextvault.cli graph-rag entity "John Smith" --type PERSON

# View Graph RAG statistics
python -m contextvault.cli graph-rag stats
```

### **Use ContextVault**

Instead of connecting directly to Ollama:
```bash
# OLD WAY (generic responses)
curl http://localhost:11434/api/generate -d '{"model":"mistral:latest","prompt":"Tell me about Acme Corp"}'

# NEW WAY (personalized responses with Graph RAG)
curl http://localhost:11435/api/generate -d '{"model":"mistral:latest","prompt":"Tell me about Acme Corp"}'
# Automatically retrieves and injects knowledge about Acme Corp, John Smith, funding, etc.
```

## 📋 **Command Line Interface**

ContextVault provides a comprehensive CLI for power users:

```bash
# System management
python -m contextvault.cli start          # Start the proxy
python -m contextvault.cli stop           # Stop the proxy
python -m contextvault.cli status         # Check system status
python -m contextvault.cli health         # Detailed health check

# Graph RAG (Primary Retrieval System)
python -m contextvault.cli graph-rag add "Content here" --id doc1
python -m contextvault.cli graph-rag search "query" --show-entities
python -m contextvault.cli graph-rag entity "Entity Name" --type PERSON
python -m contextvault.cli graph-rag stats
python -m contextvault.cli graph-rag health

# Context management (Legacy/Fallback)
python -m contextvault.cli context add "I love Python and testing" --type preference --tags programming
python -m contextvault.cli context list
python -m contextvault.cli context search "programming languages"
python -m contextvault.cli context delete <id>

# Permission management
python -m contextvault.cli permissions list
python -m contextvault.cli permissions grant mistral:latest preferences notes
python -m contextvault.cli permissions revoke mistral:latest personal

# Template management
python -m contextvault.cli templates list
python -m contextvault.cli templates set direct_instruction

# Testing and validation
python -m contextvault.cli test           # Quick test
python -m contextvault.cli demo           # Full demo
python -m contextvault.cli validate       # Comprehensive validation

# Troubleshooting
python -m contextvault.cli diagnose       # Run diagnostics
python -m contextvault.cli fix            # Auto-fix issues
python -m contextvault.cli logs           # View logs
```

## 🔧 **Configuration**

ContextVault uses YAML configuration files for easy customization:

### **Main Config (`config.yaml`)**
```yaml
# ContextVault Configuration
server:
  host: "127.0.0.1"
  port: 11435
  debug: false

ollama:
  host: "127.0.0.1"
  port: 11434

database:
  url: "sqlite:///contextvault.db"
  echo: false

semantic_search:
  model: "all-MiniLM-L6-v2"
  fallback_threshold: 0.15
  max_results: 50

context:
  max_length: 2000
  max_entries: 10
  default_template: "direct_instruction"

logging:
  level: "INFO"
  file: "contextvault.log"
```

### **Context Templates (`templates.yaml`)**
```yaml
templates:
  direct_instruction:
    strength: 8
    template: |
      Previous Context:
      {context}
      
      Current Conversation:
      {prompt}
  
  assistant_roleplay:
    strength: 9
    template: |
      You are a personal assistant with access to the following information:
      {context}
      
      User: {prompt}
      Assistant:
```

## 🌐 **API Reference**

ContextVault provides a REST API for integrations:

### **Health Check**
```bash
GET http://localhost:11435/health
```

### **Add Context**
```bash
POST http://localhost:11435/api/context/add
Content-Type: application/json

{
  "content": "I am a software engineer who loves Python",
  "context_type": "preference",
  "source": "manual",
  "tags": ["programming", "python"]
}
```

### **Search Context**
```bash
GET http://localhost:11435/api/context/search?query=programming&limit=5
```

### **List Context**
```bash
GET http://localhost:11435/api/context/list?limit=10&context_type=preference
```

### **AI Generation (with context injection)**
```bash
POST http://localhost:11435/api/generate
Content-Type: application/json

{
  "model": "mistral:latest",
  "prompt": "What programming languages do I like?",
  "stream": false
}
```

### **Permission Management**
```bash
# Grant permissions
POST http://localhost:11435/api/permissions/grant
{
  "model_id": "mistral:latest",
  "scopes": ["preferences", "notes"]
}

# Check permissions
GET http://localhost:11435/api/permissions/check/mistral:latest
```

## 🎛️ **Web Dashboard**

Access the web dashboard at `http://localhost:8080` for:

- **System Status**: Monitor ContextVault health and performance
- **Context Overview**: View and manage your context entries
- **Permission Management**: Configure model access permissions
- **Usage Analytics**: See how context is being used
- **Live Demo**: Interactive demonstration of ContextVault

## 🔌 **Integration Examples**

### **Python Integration**
```python
import requests

# Add context
requests.post('http://localhost:11435/api/context/add', json={
    'content': 'I prefer Python over JavaScript',
    'context_type': 'preference',
    'tags': ['programming']
})

# Use AI with context
response = requests.post('http://localhost:11435/api/generate', json={
    'model': 'mistral:latest',
    'prompt': 'What should I learn next?'
})
print(response.json()['response'])
```

### **Shell Script Integration**
```bash
#!/bin/bash

# Add context from command line
curl -X POST http://localhost:11435/api/context/add \
  -H "Content-Type: application/json" \
  -d '{"content": "I work as a software engineer", "context_type": "note"}'

# Get personalized AI response
curl -X POST http://localhost:11435/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "mistral:latest", "prompt": "What do I do for work?"}' | \
  jq -r '.response'
```

### **Node.js Integration**
```javascript
const axios = require('axios');

// Add context
await axios.post('http://localhost:11435/api/context/add', {
  content: 'I love hiking and photography',
  context_type: 'preference',
  tags: ['hobbies', 'photography']
});

// Get AI response
const response = await axios.post('http://localhost:11435/api/generate', {
  model: 'mistral:latest',
  prompt: 'What are my hobbies?'
});

console.log(response.data.response);
```

## 🧪 **Testing & Validation**

ContextVault includes comprehensive testing tools:

```bash
# Quick validation
python -m contextvault.cli test

# Comprehensive testing
python scripts/bulletproof_test.py

# System validation
python scripts/validate_system.py

# Performance testing
python scripts/performance_test.py
```

## 🛠️ **Troubleshooting**

### **Common Issues**

**ContextVault not starting:**
```bash
python -m contextvault.cli diagnose
python -m contextvault.cli fix
```

**No context being injected:**
```bash
# Check permissions
python -m contextvault.cli permissions list

# Check context entries
python -m contextvault.cli context list

# Test context retrieval
python -m contextvault.cli context search "test"
```

**Ollama connection issues:**
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
ollama serve
```

### **Logs and Debugging**
```bash
# View logs
python -m contextvault.cli logs

# Enable debug mode
export CONTEXTVAULT_DEBUG=true
python -m contextvault.cli start
```

## 📊 **Performance**

ContextVault is designed for minimal overhead:

- **Latency**: < 50ms additional latency per request
- **Memory**: ~50MB base memory usage
- **Storage**: ~1MB per 1000 context entries
- **CPU**: < 5% additional CPU usage

## 🔒 **Security**

ContextVault prioritizes privacy and security:

- **Local-first**: All data stays on your machine
- **Permission-based**: Granular control over what models can access
- **Encrypted storage**: Optional encryption for sensitive data
- **Audit logging**: Track all context access and modifications

## 🤝 **Contributing**

ContextVault is open source and welcomes contributions:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 **License**

MIT License - see LICENSE file for details.

## 🆘 **Support**

- **Documentation**: [docs.contextvault.ai](https://docs.contextvault.ai)
- **Issues**: [GitHub Issues](https://github.com/yourusername/contextvault/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/contextvault/discussions)
- **Discord**: [ContextVault Community](https://discord.gg/contextvault)

---

**Transform your local AI from a generic chatbot into a personal assistant that actually knows you. Get started with ContextVault today! 🚀**