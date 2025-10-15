"""Model Manager for Multi-Model Support.

Supports switching between different AI models:
- ollama:llama3.1
- ollama:mistral
- lmstudio:mistral
- openai:gpt-4
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Supported model providers."""
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ModelConfig:
    """Configuration for a specific model."""

    def __init__(
        self,
        provider: ModelProvider,
        model_name: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ):
        """Initialize model configuration."""
        self.provider = provider
        self.model_name = model_name
        self.base_url = base_url or self._get_default_url(provider)
        self.api_key = api_key
        self.extra_config = kwargs

    def _get_default_url(self, provider: ModelProvider) -> str:
        """Get default URL for provider."""
        defaults = {
            ModelProvider.OLLAMA: "http://localhost:11434",
            ModelProvider.LMSTUDIO: "http://localhost:1234",
            ModelProvider.OPENAI: "https://api.openai.com/v1",
            ModelProvider.ANTHROPIC: "https://api.anthropic.com/v1"
        }
        return defaults.get(provider, "http://localhost:11434")

    @classmethod
    def from_string(cls, model_string: str) -> "ModelConfig":
        """Parse model string like 'ollama:llama3.1'."""
        if ":" in model_string:
            provider_str, model_name = model_string.split(":", 1)
            provider = ModelProvider(provider_str.lower())
        else:
            provider = ModelProvider.OLLAMA
            model_name = model_string

        return cls(provider=provider, model_name=model_name)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "provider": self.provider.value,
            "model_name": self.model_name,
            "base_url": self.base_url,
            **self.extra_config
        }


class ModelManager:
    """Manages multiple AI models."""

    def __init__(self):
        """Initialize model manager."""
        self.models: Dict[str, ModelConfig] = {}
        self.current_model: Optional[str] = None

    def register_model(
        self,
        model_id: str,
        config: ModelConfig
    ):
        """Register a model configuration."""
        self.models[model_id] = config
        logger.info(f"Registered model: {model_id} ({config.provider.value}:{config.model_name})")

    def set_current_model(self, model_id: str) -> bool:
        """Set the current active model."""
        if model_id in self.models:
            self.current_model = model_id
            logger.info(f"Switched to model: {model_id}")
            return True
        else:
            logger.error(f"Model not found: {model_id}")
            return False

    def get_current_model(self) -> Optional[ModelConfig]:
        """Get the current model configuration."""
        if self.current_model:
            return self.models.get(self.current_model)
        return None

    def list_models(self) -> List[str]:
        """List all registered models."""
        return list(self.models.keys())


# Global instance
_model_manager = ModelManager()


def get_model_manager() -> ModelManager:
    """Get the global model manager instance."""
    return _model_manager
