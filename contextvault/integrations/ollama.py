"""Ollama integration for ContextVault."""

import json
import logging
from typing import Any, Dict, List, Optional

from .base import BaseIntegration
from ..models import Session as SessionModel
from ..services import context_retrieval_service
from ..config import settings
from ..services.templates import template_manager, format_context_with_template

logger = logging.getLogger(__name__)


class OllamaIntegration(BaseIntegration):
    """Integration for Ollama AI models."""
    
    def __init__(self, host: str = None, port: int = None):
        """
        Initialize Ollama integration.
        
        Args:
            host: Ollama host (defaults to config)
            port: Ollama port (defaults to config)
        """
        host = host or settings.ollama_host
        port = port or settings.ollama_port
        super().__init__(name="ollama", host=host, port=port)
    
    async def inject_context(
        self,
        request_data: Dict[str, Any],
        model_id: str,
        session: Optional[SessionModel] = None,
        use_graph_rag: bool = False,
    ) -> Dict[str, Any]:
        """
        Inject context into Ollama request.

        Supports both /api/generate and /api/chat endpoints.

        Args:
            request_data: Original Ollama request data
            model_id: Model identifier
            session: Optional session for tracking
            use_graph_rag: Whether to use Graph RAG for context retrieval

        Returns:
            Modified request data with context injection
        """
        try:
            # Determine request type and extract prompt
            original_prompt = self._extract_prompt(request_data)
            if not original_prompt:
                self.logger.debug("No prompt found in request, skipping context injection")
                return request_data

            # Check if Graph RAG should be used
            # Priority: explicit parameter > request data > global config
            request_use_graph_rag = (
                use_graph_rag or
                request_data.get('use_graph_rag', False) or
                request_data.get('graph_rag', False) or
                request_data.get('options', {}).get('use_graph_rag', False) or
                settings.enable_graph_rag  # Global config setting
            )

            # Get relevant context with session management
            from ..database import get_db_context
            from ..services.context_retrieval import ContextRetrievalService

            with get_db_context() as db:
                session_retrieval_service = ContextRetrievalService(
                    db_session=db,
                    use_graph_rag=request_use_graph_rag,
                    use_mem0=settings.enable_mem0  # Enable Mem0 from config
                )
                context_result = session_retrieval_service.get_context_for_prompt(
                    model_id=model_id,
                    user_prompt=original_prompt,
                    max_context_length=settings.max_context_length,
                )
            
            if context_result.get("error"):
                self.logger.warning(f"Context retrieval failed for model {model_id}: {context_result['error']}")
                return request_data
            
            context_entries = context_result.get("context_entries", [])
            if not context_entries:
                self.logger.debug(f"No relevant context found for model {model_id}")
                return request_data
            
            # Format context using Cognitive Workspace if enabled
            if settings.enable_cognitive_workspace:
                try:
                    # Use Cognitive Workspace for hierarchical memory management
                    from ..cognitive import cognitive_workspace
                    
                    # Prepare memories for workspace
                    relevant_memories = [{
                        "id": entry.id if hasattr(entry, 'id') else str(i),
                        "content": entry.content if hasattr(entry, 'content') else str(entry),
                        "metadata": entry.entry_metadata if hasattr(entry, 'entry_metadata') else {},
                        "relevance_score": getattr(entry, 'relevance_score', 0.5)
                    } for i, entry in enumerate(context_entries)]
                    
                    formatted_context, workspace_stats = cognitive_workspace.load_query_context(
                        query=original_prompt,
                        relevant_memories=relevant_memories
                    )
                    
                    self.logger.info(f"🧠 Cognitive Workspace active: {workspace_stats['total_tokens']} tokens across {workspace_stats['memories_processed']} memories")
                    
                except Exception as e:
                    self.logger.warning(f"Cognitive Workspace failed, using fallback: {e}")
                    # Fallback to simple template formatting
                    context_strings = [entry.content if hasattr(entry, 'content') else str(entry) for entry in context_entries]
                    formatted_context = self.format_prompt(
                        original_prompt=original_prompt,
                        context_entries=context_strings,
                        template_name=None
                    )
            else:
                # Use traditional template system
                context_strings = [entry.content if hasattr(entry, 'content') else str(entry) for entry in context_entries]
                formatted_context = self.format_prompt(
                    original_prompt=original_prompt,
                    context_entries=context_strings,
                    template_name=None  # Uses current template from template_manager
                )
            
            # Inject context into request
            modified_request = self._inject_into_request(request_data, formatted_context)
            
            # Track context usage in session
            if session:
                for entry_data in context_entries:
                    session.add_context_entry(entry_data)

                session.original_prompt = original_prompt
                session.final_prompt = self._extract_prompt(modified_request)
                session.total_context_length = context_result.get("total_length", 0)

            # Log context injection with Graph RAG indicator
            graph_rag_info = context_result.get("metadata", {}).get("graph_rag", {})
            if graph_rag_info.get("graph_rag_used"):
                self.logger.info(
                    f"Context injected successfully for model {model_id} using Graph RAG: "
                    f"{len(context_entries)} entries, {context_result.get('total_length', 0)} chars, "
                    f"method={graph_rag_info.get('search_method', 'unknown')}"
                )
            else:
                self.logger.info(
                    f"Context injected successfully for model {model_id}: "
                    f"{len(context_entries)} entries, {context_result.get('total_length', 0)} chars"
                )

            return modified_request
            
        except Exception as e:
            self.logger.error(f"Context injection failed for model {model_id}: {str(e)}", exc_info=True)
            # Return original request if injection fails
            return request_data
    
    def _extract_prompt(self, request_data: Dict[str, Any]) -> Optional[str]:
        """Extract prompt from Ollama request data."""
        
        # /api/generate endpoint
        if "prompt" in request_data:
            return request_data["prompt"]
        
        # /api/chat endpoint
        if "messages" in request_data:
            messages = request_data["messages"]
            if messages and isinstance(messages, list):
                # Get the last user message
                for message in reversed(messages):
                    if isinstance(message, dict) and message.get("role") == "user":
                        return message.get("content", "")
        
        return None
    
    def _inject_into_request(
        self,
        request_data: Dict[str, Any],
        formatted_context: str,
    ) -> Dict[str, Any]:
        """Inject formatted context into Ollama request."""
        
        modified_request = request_data.copy()
        
        # /api/generate endpoint
        if "prompt" in modified_request:
            modified_request["prompt"] = formatted_context
            return modified_request
        
        # /api/chat endpoint
        if "messages" in modified_request:
            messages = modified_request["messages"].copy() if modified_request["messages"] else []
            
            if messages:
                # Find the last user message and inject context
                for i in range(len(messages) - 1, -1, -1):
                    if messages[i].get("role") == "user":
                        # Create context-injected message
                        original_content = messages[i].get("content", "")
                        
                        # Use the formatted context which already includes the original prompt
                        messages[i] = {
                            **messages[i],
                            "content": formatted_context
                        }
                        break
            else:
                # No messages, create a user message with context
                messages = [{
                    "role": "user",
                    "content": formatted_context
                }]
            
            modified_request["messages"] = messages
            return modified_request
        
        # Unknown format, return as-is
        self.logger.warning("Unknown Ollama request format, cannot inject context")
        return modified_request
    
    async def check_model_availability(self, model_id: str) -> bool:
        """Check if a model is available in Ollama."""
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.endpoint}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    
                    # Check if model exists in the list
                    for model in models:
                        if model.get("name") == model_id:
                            return True
                
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to check model availability: {e}")
            return False
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models from Ollama."""
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.endpoint}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    
                    # Format model information
                    formatted_models = []
                    for model in models:
                        formatted_models.append({
                            "id": model.get("name"),
                            "name": model.get("name"),
                            "size": model.get("size"),
                            "modified_at": model.get("modified_at"),
                            "digest": model.get("digest"),
                            "details": model.get("details", {}),
                        })
                    
                    return formatted_models
                else:
                    self.logger.warning(f"Failed to get models: HTTP {response.status_code}")
                    return []
                
        except Exception as e:
            self.logger.error(f"Failed to get available models: {e}")
            return []
    
    def extract_model_id(self, request_data: Dict[str, Any]) -> Optional[str]:
        """Extract model ID from Ollama request data."""
        return request_data.get("model")
    
    def format_prompt(
        self,
        original_prompt: str,
        context_entries: List[str],
        template_name: Optional[str] = None,
    ) -> str:
        """Format prompt with context for Ollama using enhanced templates."""
        
        # Use the new template system
        formatted_prompt = format_context_with_template(
            context_entries=context_entries,
            user_prompt=original_prompt,
            template_name=template_name
        )
        
        # Log the template being used for debugging
        current_template = template_manager.get_template(template_name)
        logger.info(f"Using template: {current_template.name} (strength: {current_template.strength}/10)")
        logger.debug(f"Context entries: {len(context_entries)}")
        logger.debug(f"Original prompt: {original_prompt}")
        logger.debug(f"Formatted prompt length: {len(formatted_prompt)} chars")
        
        # Optional: Log the full formatted prompt for debugging (be careful with sensitive data)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Full formatted prompt:\n{formatted_prompt}")
        
        return formatted_prompt
    
    async def pull_model(self, model_name: str) -> Dict[str, Any]:
        """
        Pull a model in Ollama.
        
        Args:
            model_name: Name of the model to pull
            
        Returns:
            Dictionary with operation status
        """
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=300.0) as client:  # Long timeout for model pulls
                response = await client.post(
                    f"{self.endpoint}/api/pull",
                    json={"name": model_name},
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "model": model_name,
                        "message": f"Model {model_name} pulled successfully"
                    }
                else:
                    return {
                        "success": False,
                        "model": model_name,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "model": model_name,
                "error": str(e)
            }
    
    async def generate_response(
        self,
        model_id: str,
        prompt: str,
        inject_context: bool = True,
        use_graph_rag: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response using Ollama with optional context injection.

        Args:
            model_id: Model to use for generation
            prompt: User prompt
            inject_context: Whether to inject context
            use_graph_rag: Whether to use Graph RAG for context retrieval
            **kwargs: Additional parameters for Ollama

        Returns:
            Dictionary with response and metadata
        """
        try:
            import httpx

            # Prepare request
            request_data = {
                "model": model_id,
                "prompt": prompt,
                **kwargs
            }

            # Inject context if requested
            if inject_context:
                session = self.create_session(model_id, source="direct_generate")
                request_data = await self.inject_context(
                    request_data, model_id, session, use_graph_rag=use_graph_rag
                )
            
            # Make request to Ollama
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.endpoint}/api/generate",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "response": data.get("response", ""),
                        "model": data.get("model"),
                        "created_at": data.get("created_at"),
                        "done": data.get("done"),
                        "context_injected": inject_context,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "context_injected": inject_context,
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "context_injected": inject_context,
            }
    
    async def chat(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        inject_context: bool = True,
        use_graph_rag: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Chat with Ollama model with optional context injection.

        Args:
            model_id: Model to use for chat
            messages: List of chat messages
            inject_context: Whether to inject context
            use_graph_rag: Whether to use Graph RAG for context retrieval
            **kwargs: Additional parameters for Ollama

        Returns:
            Dictionary with response and metadata
        """
        try:
            import httpx

            # Prepare request
            request_data = {
                "model": model_id,
                "messages": messages,
                **kwargs
            }

            # Inject context if requested
            if inject_context:
                session = self.create_session(model_id, source="direct_chat")
                request_data = await self.inject_context(
                    request_data, model_id, session, use_graph_rag=use_graph_rag
                )
            
            # Make request to Ollama
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.endpoint}/api/chat",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "message": data.get("message", {}),
                        "model": data.get("model"),
                        "created_at": data.get("created_at"),
                        "done": data.get("done"),
                        "context_injected": inject_context,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "context_injected": inject_context,
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "context_injected": inject_context,
            }


# Global Ollama integration instance
ollama_integration = OllamaIntegration()
