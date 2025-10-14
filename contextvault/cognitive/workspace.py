"""Cognitive Workspace: Three-layer memory buffer system with attention management.

Based on cognitive architecture research for managing unlimited context with focused attention.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import math

from ..services.token_counter import token_counter
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    """Single item in a memory buffer."""

    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tokens: int = 0
    relevance_score: float = 0.0
    attention_weight: float = 0.0
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Calculate tokens if not provided."""
        if self.tokens == 0 and self.content:
            tokenizer_type = self.metadata.get("tokenizer_type", "llama")
            self.tokens = token_counter.count_tokens(self.content, tokenizer_type)

    def update_access(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()

    def get_age_minutes(self) -> float:
        """Get age in minutes."""
        return (datetime.utcnow() - self.created_at).total_seconds() / 60

    def get_recency_score(self, half_life_minutes: float = 60.0) -> float:
        """
        Calculate recency score using exponential decay.

        Args:
            half_life_minutes: Time for score to decay to 50%

        Returns:
            Score between 0 and 1
        """
        age_minutes = self.get_age_minutes()
        return math.exp(-0.693 * age_minutes / half_life_minutes)

    def calculate_forgetting_curve(self, days_since_access: Optional[float] = None) -> float:
        """
        Calculate forgetting curve score (Ebbinghaus forgetting curve).

        Args:
            days_since_access: Override days since last access

        Returns:
            Memory retention score (0-1)
        """
        if days_since_access is None:
            time_delta = datetime.utcnow() - self.last_accessed
            days_since_access = time_delta.total_seconds() / 86400

        # Ebbinghaus forgetting curve: R = e^(-t/S)
        # S = strength (based on access count)
        strength = 1 + math.log(1 + self.access_count)
        retention = math.exp(-days_since_access / strength)

        return max(0.0, min(1.0, retention))  # Clamp to [0, 1]


class MemoryBuffer:
    """
    Single memory buffer with token-based capacity management.

    Implements intelligent eviction strategies and priority management.
    """

    def __init__(
        self,
        name: str,
        max_tokens: int,
        tokenizer_type: str = "llama",
        eviction_strategy: str = "lru"  # lru, priority, forgetting
    ):
        """
        Initialize memory buffer.

        Args:
            name: Buffer name (e.g., "scratchpad", "task_buffer")
            max_tokens: Maximum token capacity
            tokenizer_type: Tokenizer type for token counting
            eviction_strategy: Strategy for evicting items when full
        """
        self.name = name
        self.max_tokens = max(10, max_tokens)  # Minimum 10 tokens - prevents divide by zero
        self.tokenizer_type = tokenizer_type
        self.eviction_strategy = eviction_strategy

        self.items: List[MemoryItem] = []
        self.current_tokens = 0

        logger.info(
            f"Initialized {name} buffer: max_tokens={self.max_tokens}, "
            f"strategy={eviction_strategy}"
        )

    def add(self, item: MemoryItem) -> bool:
        """
        Add item to buffer, evicting if necessary.

        Args:
            item: Memory item to add

        Returns:
            True if added successfully
        """
        if not item or not item.content:
            logger.warning("Cannot add empty item to buffer")
            return False

        # Ensure tokens are calculated
        if item.tokens == 0:
            item.tokens = token_counter.count_tokens(item.content, self.tokenizer_type)

        # Check if item is too large for buffer
        if item.tokens > self.max_tokens:
            logger.warning(
                f"Item {item.id} ({item.tokens} tokens) exceeds buffer capacity "
                f"({self.max_tokens} tokens)"
            )
            return False

        # Make space if needed
        space_needed = item.tokens
        while self.current_tokens + space_needed > self.max_tokens and self.items:
            self._evict_item()

        # Add item
        self.items.append(item)
        self.current_tokens += item.tokens

        logger.debug(
            f"Added item {item.id} to {self.name}: "
            f"{self.current_tokens}/{self.max_tokens} tokens used"
        )

        return True

    def get(self, item_id: str) -> Optional[MemoryItem]:
        """Get item by ID and update access statistics."""
        for item in self.items:
            if item.id == item_id:
                item.update_access()
                return item
        return None

    def remove(self, item_id: str) -> bool:
        """Remove item by ID."""
        for i, item in enumerate(self.items):
            if item.id == item_id:
                self.current_tokens -= item.tokens
                self.items.pop(i)
                logger.debug(f"Removed item {item_id} from {self.name}")
                return True
        return False

    def clear(self):
        """Clear all items from buffer."""
        self.items.clear()
        self.current_tokens = 0
        logger.debug(f"Cleared {self.name} buffer")

    def _evict_item(self) -> Optional[MemoryItem]:
        """
        Evict one item based on eviction strategy.

        Returns:
            Evicted item or None
        """
        if not self.items:
            return None

        if self.eviction_strategy == "lru":
            # Least Recently Used
            evict_idx = min(
                range(len(self.items)),
                key=lambda i: self.items[i].last_accessed
            )

        elif self.eviction_strategy == "priority":
            # Lowest priority (attention_weight + relevance_score)
            evict_idx = min(
                range(len(self.items)),
                key=lambda i: (
                    self.items[i].attention_weight + self.items[i].relevance_score
                )
            )

        elif self.eviction_strategy == "forgetting":
            # Lowest forgetting curve score (most forgotten)
            evict_idx = min(
                range(len(self.items)),
                key=lambda i: self.items[i].calculate_forgetting_curve()
            )

        else:
            # Default: FIFO
            evict_idx = 0

        evicted = self.items.pop(evict_idx)
        self.current_tokens -= evicted.tokens

        logger.debug(
            f"Evicted item {evicted.id} from {self.name} "
            f"(strategy={self.eviction_strategy})"
        )

        return evicted

    def get_all_content(self, include_metadata: bool = False) -> str:
        """
        Get all content from buffer as a single string.

        Args:
            include_metadata: Include metadata in output

        Returns:
            Combined content string
        """
        if not self.items:
            return ""

        if include_metadata:
            parts = []
            for item in self.items:
                meta_str = f"[{item.metadata.get('type', 'unknown')}]"
                parts.append(f"{meta_str} {item.content}")
            return "\n\n".join(parts)
        else:
            return "\n\n".join(item.content for item in self.items)

    def get_statistics(self) -> Dict[str, Any]:
        """Get buffer statistics."""
        return {
            "name": self.name,
            "item_count": len(self.items),
            "current_tokens": self.current_tokens,
            "max_tokens": self.max_tokens,
            "utilization": round(self.current_tokens / self.max_tokens * 100, 2) if self.max_tokens > 0 else 0,
            "eviction_strategy": self.eviction_strategy,
        }


class AttentionManager:
    """
    Manages attention weights and priorities for memory items.

    Implements metacognitive evaluation of information relevance.
    """

    def __init__(self):
        """Initialize attention manager."""
        self.attention_history: deque = deque(maxlen=100)

    def compute_attention_weights(
        self,
        query: str,
        items: List[MemoryItem],
        query_context: Optional[Dict[str, Any]] = None
    ) -> List[float]:
        """
        Compute attention weights for memory items given a query.

        Uses multiple factors:
        - Semantic relevance (if available)
        - Recency score
        - Access frequency
        - Forgetting curve
        - Query context match

        Args:
            query: Current query/prompt
            items: Memory items to score
            query_context: Additional context about the query

        Returns:
            List of attention weights (0-1) for each item
        """
        if not items:
            return []

        query_context = query_context or {}
        weights = []

        for item in items:
            # Base weight from relevance score (if already computed)
            weight = item.relevance_score

            # Recency boost (more recent = higher attention)
            recency = item.get_recency_score(half_life_minutes=60.0)
            weight += recency * 0.3

            # Access frequency boost (frequently accessed = important)
            frequency_score = math.log(1 + item.access_count) / 5.0  # Normalized
            weight += frequency_score * 0.2

            # Forgetting curve (well-remembered = higher attention)
            retention = item.calculate_forgetting_curve()
            weight += retention * 0.2

            # Context match (if metadata matches query context)
            context_match = self._compute_context_match(item.metadata, query_context)
            weight += context_match * 0.3

            # Normalize to [0, 1]
            weight = max(0.0, min(1.0, weight))
            weights.append(weight)

        # Log attention computation
        self.attention_history.append({
            "timestamp": datetime.utcnow(),
            "query": query[:100],
            "item_count": len(items),
            "mean_weight": sum(weights) / len(weights) if weights else 0,
        })

        return weights

    def _compute_context_match(
        self,
        item_metadata: Dict[str, Any],
        query_context: Dict[str, Any]
    ) -> float:
        """
        Compute how well item metadata matches query context.

        Args:
            item_metadata: Item's metadata
            query_context: Query context to match against

        Returns:
            Match score (0-1)
        """
        if not query_context:
            return 0.5  # Neutral score

        matches = 0
        total = 0

        for key, value in query_context.items():
            total += 1
            if key in item_metadata and item_metadata[key] == value:
                matches += 1

        return matches / total if total > 0 else 0.5

    def prioritize_items(
        self,
        items: List[MemoryItem],
        max_items: Optional[int] = None,
        min_weight: float = 0.0
    ) -> List[MemoryItem]:
        """
        Prioritize items by attention weight.

        Args:
            items: Items to prioritize
            max_items: Maximum items to return
            min_weight: Minimum attention weight threshold

        Returns:
            Sorted list of items (highest attention first)
        """
        # Filter by minimum weight
        filtered = [item for item in items if item.attention_weight >= min_weight]

        # Sort by attention weight (descending)
        sorted_items = sorted(
            filtered,
            key=lambda x: x.attention_weight,
            reverse=True
        )

        # Limit to max_items
        if max_items:
            sorted_items = sorted_items[:max_items]

        return sorted_items


class CognitiveWorkspace:
    """
    Three-layer cognitive workspace for managing unlimited context with focused attention.

    Architecture:
    - Immediate Scratchpad (8K tokens): Active query + immediate context
    - Task Buffer (64K tokens): Session-specific working memory
    - Episodic Cache (256K+ tokens): Full document corpus access

    This enables handling massive document collections while maintaining focused attention.
    """

    def __init__(
        self,
        scratchpad_tokens: int = 8000,
        task_buffer_tokens: int = 64000,
        episodic_cache_tokens: int = 256000,
        tokenizer_type: str = "llama"
    ):
        """
        Initialize cognitive workspace.

        Args:
            scratchpad_tokens: Immediate scratchpad capacity
            task_buffer_tokens: Task buffer capacity
            episodic_cache_tokens: Episodic cache capacity
            tokenizer_type: Tokenizer type for all buffers
        """
        self.tokenizer_type = tokenizer_type

        # Three-layer buffer system
        self.scratchpad = MemoryBuffer(
            "immediate_scratchpad",
            max_tokens=scratchpad_tokens,
            tokenizer_type=tokenizer_type,
            eviction_strategy="priority"
        )

        self.task_buffer = MemoryBuffer(
            "task_buffer",
            max_tokens=task_buffer_tokens,
            tokenizer_type=tokenizer_type,
            eviction_strategy="lru"
        )

        self.episodic_cache = MemoryBuffer(
            "episodic_cache",
            max_tokens=episodic_cache_tokens,
            tokenizer_type=tokenizer_type,
            eviction_strategy="forgetting"
        )

        # Attention manager
        self.attention_manager = AttentionManager()

        # Session state
        self.session_id: Optional[str] = None
        self.session_metadata: Dict[str, Any] = {}

        logger.info(
            f"Initialized CognitiveWorkspace: "
            f"scratchpad={scratchpad_tokens}, task_buffer={task_buffer_tokens}, "
            f"episodic_cache={episodic_cache_tokens}"
        )

    def load_query_context(
        self,
        query: str,
        relevant_memories: List[Dict[str, Any]],
        query_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Load query and relevant context into workspace buffers.

        This is the main entry point for preparing context before model inference.

        Args:
            query: User query/prompt
            relevant_memories: Retrieved memories from vector DB
            query_context: Additional query context

        Returns:
            Tuple of (formatted_context, statistics)
        """
        query_context = query_context or {}

        # Clear scratchpad for new query
        self.scratchpad.clear()

        # Convert memories to MemoryItems
        memory_items = []
        for mem in relevant_memories:
            item = MemoryItem(
                id=mem.get("id", str(len(memory_items))),
                content=mem.get("content", ""),
                metadata=mem.get("metadata", {}),
                relevance_score=mem.get("relevance_score", 0.5),
            )
            memory_items.append(item)

        # Compute attention weights
        attention_weights = self.attention_manager.compute_attention_weights(
            query, memory_items, query_context
        )

        # Assign attention weights to items
        for item, weight in zip(memory_items, attention_weights):
            item.attention_weight = weight

        # Distribute items across buffers based on attention weights
        self._distribute_to_buffers(query, memory_items)

        # Build formatted context
        formatted_context = self._build_context_string()

        # Gather statistics
        stats = {
            "query_length": len(query),
            "query_tokens": token_counter.count_tokens(query, self.tokenizer_type),
            "memories_processed": len(memory_items),
            "scratchpad": self.scratchpad.get_statistics(),
            "task_buffer": self.task_buffer.get_statistics(),
            "episodic_cache": self.episodic_cache.get_statistics(),
            "total_tokens": (
                self.scratchpad.current_tokens +
                self.task_buffer.current_tokens +
                self.episodic_cache.current_tokens
            ),
        }

        logger.info(
            f"Loaded query context: {stats['memories_processed']} memories, "
            f"{stats['total_tokens']} total tokens across buffers"
        )

        return formatted_context, stats

    def _distribute_to_buffers(
        self,
        query: str,
        items: List[MemoryItem]
    ):
        """
        Intelligently distribute memory items across the three buffers.

        Distribution strategy:
        - High attention (>0.7): Immediate scratchpad
        - Medium attention (0.3-0.7): Task buffer
        - Low attention (<0.3): Episodic cache

        Args:
            query: Current query (added to scratchpad)
            items: Memory items to distribute
        """
        # Add query to scratchpad
        query_item = MemoryItem(
            id="current_query",
            content=f"Current Query: {query}",
            metadata={"type": "query", "priority": "highest"},
            relevance_score=1.0,
            attention_weight=1.0
        )
        self.scratchpad.add(query_item)

        # Sort items by attention weight
        sorted_items = sorted(items, key=lambda x: x.attention_weight, reverse=True)

        # Distribute based on attention weights
        for item in sorted_items:
            if item.attention_weight > 0.7:
                # High attention → Scratchpad
                if not self.scratchpad.add(item):
                    # If scratchpad full, try task buffer
                    self.task_buffer.add(item)

            elif item.attention_weight > 0.3:
                # Medium attention → Task buffer
                if not self.task_buffer.add(item):
                    # If task buffer full, add to episodic cache
                    self.episodic_cache.add(item)

            else:
                # Low attention → Episodic cache
                self.episodic_cache.add(item)

    def _build_context_string(self) -> str:
        """
        Build formatted context string from all buffers.

        Returns:
            Formatted context ready for model injection
        """
        parts = []

        # Scratchpad (highest priority)
        scratchpad_content = self.scratchpad.get_all_content(include_metadata=True)
        if scratchpad_content:
            parts.append(f"=== IMMEDIATE CONTEXT ===\n{scratchpad_content}")

        # Task buffer
        task_content = self.task_buffer.get_all_content(include_metadata=True)
        if task_content:
            parts.append(f"\n=== RELEVANT INFORMATION ===\n{task_content}")

        # Episodic cache
        episodic_content = self.episodic_cache.get_all_content(include_metadata=False)
        if episodic_content:
            parts.append(f"\n=== BACKGROUND KNOWLEDGE ===\n{episodic_content}")

        return "\n".join(parts)

    def get_workspace_statistics(self) -> Dict[str, Any]:
        """Get comprehensive workspace statistics."""
        return {
            "session_id": self.session_id,
            "tokenizer_type": self.tokenizer_type,
            "buffers": {
                "scratchpad": self.scratchpad.get_statistics(),
                "task_buffer": self.task_buffer.get_statistics(),
                "episodic_cache": self.episodic_cache.get_statistics(),
            },
            "total_tokens": (
                self.scratchpad.current_tokens +
                self.task_buffer.current_tokens +
                self.episodic_cache.current_tokens
            ),
            "total_items": (
                len(self.scratchpad.items) +
                len(self.task_buffer.items) +
                len(self.episodic_cache.items)
            ),
        }

    def clear_workspace(self):
        """Clear all buffers."""
        self.scratchpad.clear()
        self.task_buffer.clear()
        self.episodic_cache.clear()
        logger.info("Cleared all workspace buffers")

    def start_session(self, session_id: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Start a new session.

        Args:
            session_id: Unique session identifier
            metadata: Session metadata
        """
        self.session_id = session_id
        self.session_metadata = metadata or {}
        self.clear_workspace()
        logger.info(f"Started session: {session_id}")

    def end_session(self):
        """End current session and clear buffers."""
        session_id = self.session_id
        self.session_id = None
        self.session_metadata.clear()
        self.clear_workspace()
        logger.info(f"Ended session: {session_id}")


# Global cognitive workspace instance
cognitive_workspace = CognitiveWorkspace(
    scratchpad_tokens=settings.max_context_tokens // 16,  # 8K default
    task_buffer_tokens=settings.max_context_tokens // 2,  # 64K default
    episodic_cache_tokens=settings.max_context_tokens * 2,  # 256K default
    tokenizer_type=settings.default_tokenizer_type
)
