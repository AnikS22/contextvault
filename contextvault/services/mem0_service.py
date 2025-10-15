"""Mem0-based Memory Service for ContextVault.

This replaces the custom VaultService with industry-standard Mem0,
providing production-grade memory management with:
- Semantic search
- Memory consolidation
- Relationship tracking
- Vector embeddings
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Optional imports
try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    logger.warning("Mem0 not available. Install with: pip install mem0ai")
    MEM0_AVAILABLE = False
    Memory = None

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    logger.warning("NetworkX not available. Install with: pip install networkx")
    NETWORKX_AVAILABLE = False
    nx = None


class Mem0Service:
    """Mem0-based memory service with relationship tracking."""

    def __init__(
        self,
        user_id: str = "default_user",
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize Mem0 service.

        Args:
            user_id: User identifier for memory isolation
            config: Mem0 configuration dictionary
        """
        self.user_id = user_id
        self.memory = None
        self.relationship_graph = None

        if not MEM0_AVAILABLE:
            logger.error("Mem0 is not available. Memory service will not function.")
            return

        # Default Mem0 configuration
        default_config = {
            "llm": {
                "provider": "ollama",
                "config": {
                    "model": "mistral:latest",
                    "base_url": "http://localhost:11434"
                }
            },
            "embedder": {
                "provider": "ollama",
                "config": {
                    "model": "nomic-embed-text:latest",
                    "base_url": "http://localhost:11434"
                }
            },
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": "contextvault_memories",
                    "path": "./qdrant_data"
                }
            },
            "version": "v1.1"
        }

        # Merge with user config
        self.config = {**default_config, **(config or {})}

        # Initialize Mem0
        try:
            self.memory = Memory.from_config(self.config)
            logger.info(f"Mem0 memory initialized for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Mem0: {e}")
            logger.info("Falling back to local Qdrant storage")

            # Fallback to simpler config
            try:
                self.memory = Memory()
                logger.info("Mem0 initialized with default configuration")
            except Exception as e2:
                logger.error(f"Failed to initialize Mem0 with defaults: {e2}")
                self.memory = None

        # Initialize NetworkX relationship graph
        if NETWORKX_AVAILABLE:
            self.relationship_graph = nx.DiGraph()
            logger.info("NetworkX relationship graph initialized")
        else:
            logger.warning("NetworkX not available - relationship tracking disabled")

    def is_available(self) -> bool:
        """Check if Mem0 is available and initialized."""
        return self.memory is not None

    def add_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        extract_relationships: bool = True
    ) -> Dict[str, Any]:
        """Add a memory to Mem0.

        Args:
            content: Memory content
            metadata: Additional metadata
            extract_relationships: Whether to extract relationships

        Returns:
            Dictionary with memory_id and extracted relationships
        """
        if not self.is_available():
            raise RuntimeError("Mem0 is not available")

        try:
            # Add memory to Mem0
            result = self.memory.add(
                messages=content,
                user_id=self.user_id,
                metadata=metadata or {}
            )

            memory_id = result.get("id") if isinstance(result, dict) else str(result)

            logger.info(f"Added memory to Mem0: {memory_id}")

            # Extract relationships if enabled and NetworkX available
            relationships = []
            if extract_relationships and NETWORKX_AVAILABLE and self.relationship_graph:
                relationships = self._extract_and_store_relationships(content, memory_id)

            return {
                "memory_id": memory_id,
                "content": content,
                "metadata": metadata,
                "relationships": relationships,
                "created_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            raise

    def search_memories(
        self,
        query: str,
        limit: int = 10,
        include_relationships: bool = True
    ) -> List[Dict[str, Any]]:
        """Search memories using Mem0's semantic search.

        Args:
            query: Search query
            limit: Maximum number of results
            include_relationships: Whether to include relationship info

        Returns:
            List of memory dictionaries with optional relationships
        """
        if not self.is_available():
            raise RuntimeError("Mem0 is not available")

        try:
            # Search Mem0
            results = self.memory.search(
                query=query,
                user_id=self.user_id,
                limit=limit
            )

            memories = []
            for result in results:
                memory_dict = {
                    "memory_id": result.get("id"),
                    "content": result.get("memory"),
                    "score": result.get("score", 0.0),
                    "metadata": result.get("metadata", {}),
                    "created_at": result.get("created_at"),
                    "updated_at": result.get("updated_at")
                }

                # Add relationship information if requested
                if include_relationships and NETWORKX_AVAILABLE and self.relationship_graph:
                    memory_id = result.get("id")
                    if memory_id and self.relationship_graph.has_node(memory_id):
                        # Get connected nodes
                        successors = list(self.relationship_graph.successors(memory_id))
                        predecessors = list(self.relationship_graph.predecessors(memory_id))

                        memory_dict["relationships"] = {
                            "outgoing": successors,
                            "incoming": predecessors,
                            "total": len(successors) + len(predecessors)
                        }

                memories.append(memory_dict)

            logger.info(f"Found {len(memories)} memories for query: {query[:50]}")
            return memories

        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            raise

    def get_all_memories(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all memories for the user.

        Args:
            limit: Optional limit on number of memories

        Returns:
            List of all memory dictionaries
        """
        if not self.is_available():
            raise RuntimeError("Mem0 is not available")

        try:
            results = self.memory.get_all(user_id=self.user_id)

            memories = []
            for result in results:
                memories.append({
                    "memory_id": result.get("id"),
                    "content": result.get("memory"),
                    "metadata": result.get("metadata", {}),
                    "created_at": result.get("created_at"),
                    "updated_at": result.get("updated_at")
                })

            if limit:
                memories = memories[:limit]

            logger.info(f"Retrieved {len(memories)} memories")
            return memories

        except Exception as e:
            logger.error(f"Failed to get all memories: {e}")
            raise

    def update_memory(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update an existing memory.

        Args:
            memory_id: Memory identifier
            content: New content
            metadata: Updated metadata

        Returns:
            Updated memory dictionary
        """
        if not self.is_available():
            raise RuntimeError("Mem0 is not available")

        try:
            result = self.memory.update(
                memory_id=memory_id,
                data=content
            )

            logger.info(f"Updated memory: {memory_id}")

            return {
                "memory_id": memory_id,
                "content": content,
                "metadata": metadata,
                "updated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to update memory: {e}")
            raise

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory.

        Args:
            memory_id: Memory identifier

        Returns:
            True if deleted successfully
        """
        if not self.is_available():
            raise RuntimeError("Mem0 is not available")

        try:
            self.memory.delete(memory_id=memory_id)

            # Remove from relationship graph if present
            if NETWORKX_AVAILABLE and self.relationship_graph:
                if self.relationship_graph.has_node(memory_id):
                    self.relationship_graph.remove_node(memory_id)

            logger.info(f"Deleted memory: {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False

    def delete_all_memories(self) -> bool:
        """Delete all memories for the user.

        Returns:
            True if deleted successfully
        """
        if not self.is_available():
            raise RuntimeError("Mem0 is not available")

        try:
            self.memory.delete_all(user_id=self.user_id)

            # Clear relationship graph
            if NETWORKX_AVAILABLE and self.relationship_graph:
                self.relationship_graph.clear()

            logger.info("Deleted all memories")
            return True

        except Exception as e:
            logger.error(f"Failed to delete all memories: {e}")
            return False

    def _extract_and_store_relationships(
        self,
        content: str,
        memory_id: str
    ) -> List[Dict[str, str]]:
        """Extract relationships from content and store in NetworkX graph.

        Args:
            content: Memory content
            memory_id: Memory identifier

        Returns:
            List of extracted relationships
        """
        if not NETWORKX_AVAILABLE or not self.relationship_graph:
            return []

        relationships = []

        # Simple pattern matching for relationships
        # Format: "X works at Y", "X is friend of Y", etc.
        import re

        # Relationship patterns
        patterns = [
            (r"(\w+(?:\s+\w+)*)\s+works at\s+(\w+(?:\s+\w+)*)", "WORKS_AT"),
            (r"(\w+(?:\s+\w+)*)\s+is (?:a |an )?(\w+) at\s+(\w+(?:\s+\w+)*)", "POSITION_AT"),
            (r"(\w+(?:\s+\w+)*)\s+founded\s+(\w+(?:\s+\w+)*)", "FOUNDED"),
            (r"(\w+(?:\s+\w+)*)\s+manages\s+(\w+(?:\s+\w+)*)", "MANAGES"),
            (r"(\w+(?:\s+\w+)*)\s+reports to\s+(\w+(?:\s+\w+)*)", "REPORTS_TO"),
            (r"(\w+(?:\s+\w+)*)\s+lives in\s+(\w+(?:\s+\w+)*)", "LIVES_IN"),
            (r"(\w+(?:\s+\w+)*)\s+owns\s+(\w+(?:\s+\w+)*)", "OWNS"),
        ]

        for pattern, relationship_type in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                entity1 = match.group(1).strip()
                entity2 = match.group(2).strip() if len(match.groups()) == 2 else match.group(3).strip()

                # Add to graph
                if not self.relationship_graph.has_node(entity1):
                    self.relationship_graph.add_node(entity1, type="entity")
                if not self.relationship_graph.has_node(entity2):
                    self.relationship_graph.add_node(entity2, type="entity")

                self.relationship_graph.add_edge(
                    entity1,
                    entity2,
                    relationship=relationship_type,
                    memory_id=memory_id
                )

                relationships.append({
                    "source": entity1,
                    "target": entity2,
                    "type": relationship_type
                })

                logger.debug(f"Extracted relationship: {entity1} --{relationship_type}-> {entity2}")

        return relationships

    def get_relationships(
        self,
        entity: Optional[str] = None,
        memory_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get relationships from the NetworkX graph.

        Args:
            entity: Optional entity name to filter relationships
            memory_id: Optional memory ID to filter relationships

        Returns:
            List of relationship dictionaries
        """
        if not NETWORKX_AVAILABLE or not self.relationship_graph:
            return []

        relationships = []

        if entity:
            # Get relationships for specific entity
            if self.relationship_graph.has_node(entity):
                # Outgoing relationships
                for target in self.relationship_graph.successors(entity):
                    edge_data = self.relationship_graph.get_edge_data(entity, target)
                    relationships.append({
                        "source": entity,
                        "target": target,
                        "type": edge_data.get("relationship"),
                        "memory_id": edge_data.get("memory_id")
                    })

                # Incoming relationships
                for source in self.relationship_graph.predecessors(entity):
                    edge_data = self.relationship_graph.get_edge_data(source, entity)
                    relationships.append({
                        "source": source,
                        "target": entity,
                        "type": edge_data.get("relationship"),
                        "memory_id": edge_data.get("memory_id")
                    })

        elif memory_id:
            # Get relationships for specific memory
            for source, target, data in self.relationship_graph.edges(data=True):
                if data.get("memory_id") == memory_id:
                    relationships.append({
                        "source": source,
                        "target": target,
                        "type": data.get("relationship"),
                        "memory_id": memory_id
                    })

        else:
            # Get all relationships
            for source, target, data in self.relationship_graph.edges(data=True):
                relationships.append({
                    "source": source,
                    "target": target,
                    "type": data.get("relationship"),
                    "memory_id": data.get("memory_id")
                })

        return relationships

    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the relationship graph.

        Returns:
            Dictionary with graph statistics
        """
        if not NETWORKX_AVAILABLE or not self.relationship_graph:
            return {"available": False}

        return {
            "available": True,
            "nodes": self.relationship_graph.number_of_nodes(),
            "edges": self.relationship_graph.number_of_edges(),
            "density": nx.density(self.relationship_graph),
            "is_directed": self.relationship_graph.is_directed()
        }


# Global instance
_mem0_service = None


def get_mem0_service(
    user_id: str = "default_user",
    config: Optional[Dict[str, Any]] = None
) -> Mem0Service:
    """Get or create the global Mem0 service instance.

    Args:
        user_id: User identifier
        config: Optional Mem0 configuration

    Returns:
        Mem0Service instance
    """
    global _mem0_service

    if _mem0_service is None or _mem0_service.user_id != user_id:
        _mem0_service = Mem0Service(user_id=user_id, config=config)

    return _mem0_service
