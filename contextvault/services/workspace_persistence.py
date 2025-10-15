"""Workspace State Persistence.

Saves all memory buffers to database so you can continue
exactly where you left off:
- Working Memory (active context)
- Episodic Memory (conversation history)
- Semantic Memory (learned facts)
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class WorkspaceState:
    """Represents the complete workspace state."""

    def __init__(self):
        """Initialize workspace state."""
        self.working_memory: List[Dict[str, Any]] = []
        self.episodic_memory: List[Dict[str, Any]] = []
        self.semantic_memory: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "version": "1.0"
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert workspace state to dictionary."""
        return {
            "working_memory": self.working_memory,
            "episodic_memory": self.episodic_memory,
            "semantic_memory": self.semantic_memory,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkspaceState":
        """Create workspace state from dictionary."""
        state = cls()
        state.working_memory = data.get("working_memory", [])
        state.episodic_memory = data.get("episodic_memory", [])
        state.semantic_memory = data.get("semantic_memory", {})
        state.metadata = data.get("metadata", {})
        return state


class WorkspacePersistenceService:
    """Service for persisting workspace state to database/file."""

    def __init__(
        self,
        mem0_service,
        storage_path: Optional[Path] = None
    ):
        """Initialize workspace persistence service.

        Args:
            mem0_service: Mem0Service instance for memory storage
            storage_path: Optional path for file-based storage
        """
        self.mem0_service = mem0_service
        self.storage_path = storage_path or Path("./workspace_state")
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save_workspace(
        self,
        workspace_state: WorkspaceState,
        workspace_id: str = "default"
    ) -> bool:
        """Save workspace state.

        Args:
            workspace_state: WorkspaceState to save
            workspace_id: Identifier for this workspace

        Returns:
            True if saved successfully
        """
        try:
            # Update metadata
            workspace_state.metadata["updated_at"] = datetime.utcnow().isoformat()
            workspace_state.metadata["workspace_id"] = workspace_id

            # Save to Mem0 as a special memory
            state_dict = workspace_state.to_dict()

            self.mem0_service.add_memory(
                content=f"Workspace state: {workspace_id}",
                metadata={
                    "type": "workspace_state",
                    "workspace_id": workspace_id,
                    "state_data": json.dumps(state_dict),
                    "saved_at": datetime.utcnow().isoformat()
                },
                extract_relationships=False  # Don't extract relationships from workspace state
            )

            # Also save to file as backup
            file_path = self.storage_path / f"{workspace_id}.json"
            with open(file_path, 'w') as f:
                json.dump(state_dict, f, indent=2)

            logger.info(f"Saved workspace state: {workspace_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save workspace state: {e}")
            return False

    def load_workspace(
        self,
        workspace_id: str = "default"
    ) -> Optional[WorkspaceState]:
        """Load workspace state.

        Args:
            workspace_id: Identifier for the workspace to load

        Returns:
            WorkspaceState if found, None otherwise
        """
        try:
            # Try loading from Mem0 first
            memories = self.mem0_service.search_memories(
                query=f"Workspace state: {workspace_id}",
                limit=1,
                include_relationships=False
            )

            if memories:
                memory = memories[0]
                metadata = memory.get("metadata", {})

                if metadata.get("type") == "workspace_state":
                    state_data_str = metadata.get("state_data")
                    if state_data_str:
                        state_dict = json.loads(state_data_str)
                        workspace_state = WorkspaceState.from_dict(state_dict)

                        logger.info(f"Loaded workspace state from Mem0: {workspace_id}")
                        return workspace_state

            # Fallback to file-based storage
            file_path = self.storage_path / f"{workspace_id}.json"
            if file_path.exists():
                with open(file_path, 'r') as f:
                    state_dict = json.load(f)

                workspace_state = WorkspaceState.from_dict(state_dict)
                logger.info(f"Loaded workspace state from file: {workspace_id}")
                return workspace_state

            logger.warning(f"No workspace state found for: {workspace_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to load workspace state: {e}")
            return None

    def list_workspaces(self) -> List[str]:
        """List all saved workspaces.

        Returns:
            List of workspace IDs
        """
        try:
            workspaces = []

            # Get from Mem0
            memories = self.mem0_service.search_memories(
                query="Workspace state:",
                limit=100,
                include_relationships=False
            )

            for memory in memories:
                metadata = memory.get("metadata", {})
                if metadata.get("type") == "workspace_state":
                    workspace_id = metadata.get("workspace_id")
                    if workspace_id:
                        workspaces.append(workspace_id)

            # Also check file storage
            for file_path in self.storage_path.glob("*.json"):
                workspace_id = file_path.stem
                if workspace_id not in workspaces:
                    workspaces.append(workspace_id)

            return sorted(set(workspaces))

        except Exception as e:
            logger.error(f"Failed to list workspaces: {e}")
            return []

    def delete_workspace(self, workspace_id: str) -> bool:
        """Delete a workspace state.

        Args:
            workspace_id: Workspace to delete

        Returns:
            True if deleted successfully
        """
        try:
            deleted = False

            # Delete from Mem0
            memories = self.mem0_service.search_memories(
                query=f"Workspace state: {workspace_id}",
                limit=10,
                include_relationships=False
            )

            for memory in memories:
                metadata = memory.get("metadata", {})
                if (metadata.get("type") == "workspace_state" and
                    metadata.get("workspace_id") == workspace_id):
                    self.mem0_service.delete_memory(memory.get("memory_id"))
                    deleted = True

            # Delete file
            file_path = self.storage_path / f"{workspace_id}.json"
            if file_path.exists():
                file_path.unlink()
                deleted = True

            if deleted:
                logger.info(f"Deleted workspace state: {workspace_id}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete workspace state: {e}")
            return False


# Global instance
_workspace_service = None


def get_workspace_service(
    mem0_service,
    storage_path: Optional[Path] = None
) -> WorkspacePersistenceService:
    """Get or create the global workspace persistence service.

    Args:
        mem0_service: Mem0Service instance
        storage_path: Optional storage path

    Returns:
        WorkspacePersistenceService instance
    """
    global _workspace_service

    if _workspace_service is None:
        _workspace_service = WorkspacePersistenceService(mem0_service, storage_path)

    return _workspace_service
