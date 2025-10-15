"""Configuration management for ContextVault."""

import os
from typing import Any, Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///./contextvault.db", env="DATABASE_URL")
    
    # API Configuration
    api_host: str = Field(default="127.0.0.1", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=1, env="API_WORKERS")
    
    # Security
    secret_key: str = Field(default="change-me-in-production", env="SECRET_KEY")
    encryption_key: Optional[str] = Field(default=None, env="ENCRYPTION_KEY")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # Ollama Integration
    ollama_host: str = Field(default="127.0.0.1", env="OLLAMA_HOST")
    ollama_port: int = Field(default=11434, env="OLLAMA_PORT")
    proxy_port: int = Field(default=11435, env="PROXY_PORT")
    
    # Context Management
    max_context_entries: int = Field(default=100, env="MAX_CONTEXT_ENTRIES")
    max_context_length: int = Field(default=10000, env="MAX_CONTEXT_LENGTH")  # Deprecated, use max_context_tokens
    max_context_tokens: int = Field(default=8192, env="MAX_CONTEXT_TOKENS")  # New token-based limit
    default_context_retention_days: int = Field(default=90, env="DEFAULT_CONTEXT_RETENTION_DAYS")

    # Graph RAG Configuration (Production Default: ENABLED)
    enable_graph_rag: bool = Field(default=True, env="ENABLE_GRAPH_RAG")
    neo4j_uri: str = Field(default="bolt://localhost:7687", env="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", env="NEO4J_USER")
    neo4j_password: str = Field(default="password", env="NEO4J_PASSWORD")

    # Cognitive Workspace Configuration (Production Default: ENABLED - no external deps)
    enable_cognitive_workspace: bool = Field(default=True, env="ENABLE_COGNITIVE_WORKSPACE")
    
    # Mem0 Cognitive Workspace Configuration (Production Default: DISABLED - requires Qdrant)
    enable_mem0: bool = Field(default=False, env="ENABLE_MEM0")
    qdrant_url: str = Field(default="http://localhost:6333", env="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")

    # Token window management
    use_token_counting: bool = Field(default=True, env="USE_TOKEN_COUNTING")
    default_tokenizer_type: str = Field(default="llama", env="DEFAULT_TOKENIZER_TYPE")
    
    # Permission Defaults
    default_model_permissions: str = Field(default="basic", env="DEFAULT_MODEL_PERMISSIONS")
    allow_unknown_models: bool = Field(default=False, env="ALLOW_UNKNOWN_MODELS")
    
    # Performance
    enable_caching: bool = Field(default=True, env="ENABLE_CACHING")
    cache_ttl_seconds: int = Field(default=300, env="CACHE_TTL_SECONDS")

    # Extended Thinking Configuration
    enable_extended_thinking: bool = Field(default=True, env="ENABLE_EXTENDED_THINKING")
    max_thinking_duration_minutes: int = Field(default=120, env="MAX_THINKING_DURATION_MINUTES")
    synthesis_interval_seconds: int = Field(default=300, env="SYNTHESIS_INTERVAL_SECONDS")
    max_concurrent_thinking_sessions: int = Field(default=5, env="MAX_CONCURRENT_THINKING_SESSIONS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_database_url() -> str:
    """Get the database URL, handling SQLite path resolution."""
    url = settings.database_url
    if url.startswith("sqlite:"):
        # Ensure SQLite paths are relative to the project root
        if ":///" in url and not os.path.isabs(url.split("///")[1]):
            db_path = url.split("///")[1]
            project_root = os.path.dirname(os.path.dirname(__file__))
            full_path = os.path.join(project_root, db_path)
            url = f"sqlite:///{full_path}"
    return url


def get_context_template() -> str:
    """Get the default context injection template."""
    return """Previous Context:
{context_entries}

Current Conversation:
{user_prompt}"""


def get_allowed_context_types() -> List[str]:
    """Get the list of allowed context types."""
    return ["text", "file", "event", "preference", "note"]


def get_default_permission_scopes() -> List[str]:
    """Get the default permission scopes."""
    return ["basic", "preferences", "notes", "files", "events", "all"]


def get_model_profiles() -> Dict[str, Dict[str, Any]]:
    """
    Get predefined model profiles with token window configurations.

    Returns:
        Dictionary of model profiles with token limits and configurations
    """
    return {
        # Llama models
        "llama3.1": {
            "max_context_window": 128000,
            "max_output": 4096,
            "tokenizer": "llama",
            "buffer": 512,
        },
        "llama3": {
            "max_context_window": 8192,
            "max_output": 2048,
            "tokenizer": "llama",
            "buffer": 256,
        },
        "llama2": {
            "max_context_window": 4096,
            "max_output": 2048,
            "tokenizer": "llama",
            "buffer": 256,
        },
        # Mistral models
        "mistral": {
            "max_context_window": 32000,
            "max_output": 8192,
            "tokenizer": "mistral",
            "buffer": 512,
        },
        "mixtral": {
            "max_context_window": 32000,
            "max_output": 8192,
            "tokenizer": "mistral",
            "buffer": 512,
        },
        # Gemma models
        "gemma2": {
            "max_context_window": 8192,
            "max_output": 2048,
            "tokenizer": "gemma",
            "buffer": 256,
        },
        "gemma": {
            "max_context_window": 8192,
            "max_output": 2048,
            "tokenizer": "gemma",
            "buffer": 256,
        },
        # Phi models
        "phi3": {
            "max_context_window": 128000,
            "max_output": 4096,
            "tokenizer": "phi",
            "buffer": 512,
        },
        "phi": {
            "max_context_window": 2048,
            "max_output": 1024,
            "tokenizer": "phi",
            "buffer": 128,
        },
        # Default fallback
        "default": {
            "max_context_window": 8192,
            "max_output": 2048,
            "tokenizer": "llama",
            "buffer": 256,
        },
    }


def get_model_profile(model_id: str) -> Dict[str, Any]:
    """
    Get token configuration for a specific model.

    Args:
        model_id: Model identifier (e.g., 'llama3.1', 'mistral:latest')

    Returns:
        Dictionary with model configuration
    """
    profiles = get_model_profiles()

    # Extract base model name (remove version/tags)
    model_base = model_id.split(':')[0].lower()

    # Try exact match first
    if model_base in profiles:
        return profiles[model_base]

    # Try partial match
    for profile_name, profile_config in profiles.items():
        if profile_name in model_base or model_base in profile_name:
            return profile_config

    # Return default
    return profiles["default"]


def validate_environment() -> Dict[str, Any]:
    """Validate the current environment and return a status report."""
    issues = []
    warnings = []

    # Check database accessibility
    db_url = get_database_url()
    if db_url.startswith("sqlite:"):
        db_path = db_url.split("///")[1]
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except PermissionError:
                issues.append(f"Cannot create database directory: {db_dir}")

    # Check security settings
    if settings.secret_key == "change-me-in-production":
        warnings.append("Using default secret key - change in production")

    if not settings.encryption_key:
        warnings.append("No encryption key set - sensitive data will be stored in plaintext")

    # Check Ollama connectivity (non-blocking)
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((settings.ollama_host, settings.ollama_port))
        sock.close()
        if result != 0:
            warnings.append(f"Ollama not accessible at {settings.ollama_host}:{settings.ollama_port}")
    except Exception:
        warnings.append("Could not check Ollama connectivity")

    return {
        "status": "healthy" if not issues else "error",
        "issues": issues,
        "warnings": warnings,
        "config": {
            "database_url": db_url,
            "api_endpoint": f"http://{settings.api_host}:{settings.api_port}",
            "ollama_endpoint": f"http://{settings.ollama_host}:{settings.ollama_port}",
            "proxy_endpoint": f"http://{settings.api_host}:{settings.proxy_port}",
        }
    }
