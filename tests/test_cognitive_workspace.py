"""Tests for Cognitive Workspace and Vector Database."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from contextvault.cognitive.workspace import (
    MemoryItem,
    MemoryBuffer,
    AttentionManager,
    CognitiveWorkspace
)
from contextvault.storage.vector_db import VectorDatabase


class TestMemoryItem:
    """Test MemoryItem functionality."""

    def test_memory_item_creation(self):
        """Test creating a memory item."""
        item = MemoryItem(
            id="test-1",
            content="This is a test memory item",
            metadata={"type": "test", "category": "unit_test"},
        )

        assert item.id == "test-1"
        assert item.content == "This is a test memory item"
        assert item.tokens > 0  # Auto-calculated
        assert item.access_count == 0

    def test_memory_item_access_tracking(self):
        """Test access count and timestamp tracking."""
        item = MemoryItem(id="test-2", content="Test content")

        initial_access = item.last_accessed
        initial_count = item.access_count

        item.update_access()

        assert item.access_count == initial_count + 1
        assert item.last_accessed >= initial_access

    def test_recency_score(self):
        """Test recency score calculation."""
        item = MemoryItem(id="test-3", content="Test content")

        # Fresh item should have high recency score
        score = item.get_recency_score(half_life_minutes=60.0)
        assert 0.9 <= score <= 1.0

    def test_forgetting_curve(self):
        """Test forgetting curve calculation."""
        item = MemoryItem(id="test-4", content="Test content")

        # Fresh item with no accesses should have lower retention
        retention = item.calculate_forgetting_curve(days_since_access=0.0)
        assert 0.8 <= retention <= 1.0

        # Accessed multiple times should have better retention
        item.access_count = 10
        retention_high = item.calculate_forgetting_curve(days_since_access=1.0)

        item.access_count = 1
        retention_low = item.calculate_forgetting_curve(days_since_access=1.0)

        assert retention_high > retention_low


class TestMemoryBuffer:
    """Test MemoryBuffer functionality."""

    def test_buffer_creation(self):
        """Test creating a memory buffer."""
        buffer = MemoryBuffer(
            name="test_buffer",
            max_tokens=1000,
            eviction_strategy="lru"
        )

        assert buffer.name == "test_buffer"
        assert buffer.max_tokens == 1000
        assert buffer.current_tokens == 0
        assert len(buffer.items) == 0

    def test_add_item(self):
        """Test adding items to buffer."""
        buffer = MemoryBuffer("test_buffer", max_tokens=1000)

        item = MemoryItem(id="test-1", content="Test content for buffer")

        success = buffer.add(item)
        assert success is True
        assert len(buffer.items) == 1
        assert buffer.current_tokens > 0

    def test_buffer_overflow_eviction(self):
        """Test eviction when buffer is full."""
        buffer = MemoryBuffer("test_buffer", max_tokens=100, eviction_strategy="lru")

        # Add items until buffer is full
        for i in range(10):
            item = MemoryItem(
                id=f"item-{i}",
                content=f"This is test content number {i}"
            )
            buffer.add(item)

        # Buffer should have evicted some items to stay under limit
        assert buffer.current_tokens <= buffer.max_tokens

    def test_item_too_large(self):
        """Test that items larger than buffer are rejected."""
        buffer = MemoryBuffer("test_buffer", max_tokens=50)

        large_item = MemoryItem(
            id="large",
            content="This is a very long content that exceeds buffer capacity " * 20
        )

        success = buffer.add(large_item)
        assert success is False

    def test_get_item(self):
        """Test retrieving items from buffer."""
        buffer = MemoryBuffer("test_buffer", max_tokens=1000)

        item = MemoryItem(id="test-get", content="Test content")
        buffer.add(item)

        retrieved = buffer.get("test-get")
        assert retrieved is not None
        assert retrieved.id == "test-get"
        assert retrieved.access_count == 1

    def test_remove_item(self):
        """Test removing items from buffer."""
        buffer = MemoryBuffer("test_buffer", max_tokens=1000)

        item = MemoryItem(id="test-remove", content="Test content")
        buffer.add(item)

        initial_tokens = buffer.current_tokens
        success = buffer.remove("test-remove")

        assert success is True
        assert len(buffer.items) == 0
        assert buffer.current_tokens < initial_tokens

    def test_clear_buffer(self):
        """Test clearing buffer."""
        buffer = MemoryBuffer("test_buffer", max_tokens=1000)

        for i in range(5):
            item = MemoryItem(id=f"item-{i}", content=f"Content {i}")
            buffer.add(item)

        buffer.clear()
        assert len(buffer.items) == 0
        assert buffer.current_tokens == 0

    def test_get_statistics(self):
        """Test getting buffer statistics."""
        buffer = MemoryBuffer("test_buffer", max_tokens=1000)

        item = MemoryItem(id="test-stats", content="Test content")
        buffer.add(item)

        stats = buffer.get_statistics()

        assert stats["name"] == "test_buffer"
        assert stats["item_count"] == 1
        assert stats["current_tokens"] > 0
        assert stats["max_tokens"] == 1000
        assert 0 <= stats["utilization"] <= 100


class TestAttentionManager:
    """Test AttentionManager functionality."""

    def test_attention_manager_creation(self):
        """Test creating attention manager."""
        manager = AttentionManager()
        assert manager is not None
        assert len(manager.attention_history) == 0

    def test_compute_attention_weights(self):
        """Test computing attention weights."""
        manager = AttentionManager()

        items = [
            MemoryItem(id="item-1", content="Important business contract", relevance_score=0.9),
            MemoryItem(id="item-2", content="Random note", relevance_score=0.3),
            MemoryItem(id="item-3", content="Recent meeting notes", relevance_score=0.7),
        ]

        # Give item-3 more accesses
        items[2].access_count = 10

        query = "Tell me about the business contract"
        weights = manager.compute_attention_weights(query, items)

        assert len(weights) == 3
        assert all(0.0 <= w <= 1.0 for w in weights)

        # Item with higher relevance should have higher weight
        assert weights[0] >= weights[1]

    def test_prioritize_items(self):
        """Test prioritizing items by attention weight."""
        manager = AttentionManager()

        items = [
            MemoryItem(id="item-1", content="Low priority", attention_weight=0.2),
            MemoryItem(id="item-2", content="High priority", attention_weight=0.9),
            MemoryItem(id="item-3", content="Medium priority", attention_weight=0.5),
        ]

        prioritized = manager.prioritize_items(items, max_items=2, min_weight=0.0)

        assert len(prioritized) == 2
        assert prioritized[0].id == "item-2"  # Highest weight first
        assert prioritized[1].id == "item-3"

    def test_context_match(self):
        """Test context matching."""
        manager = AttentionManager()

        item_metadata = {"type": "contract", "category": "business"}
        query_context = {"type": "contract", "category": "business"}

        match_score = manager._compute_context_match(item_metadata, query_context)
        assert match_score == 1.0  # Perfect match

        query_context_partial = {"type": "contract", "category": "personal"}
        match_score_partial = manager._compute_context_match(item_metadata, query_context_partial)
        assert 0.0 < match_score_partial < 1.0  # Partial match


class TestCognitiveWorkspace:
    """Test CognitiveWorkspace functionality."""

    def test_workspace_creation(self):
        """Test creating cognitive workspace."""
        workspace = CognitiveWorkspace(
            scratchpad_tokens=8000,
            task_buffer_tokens=64000,
            episodic_cache_tokens=256000
        )

        assert workspace.scratchpad.max_tokens == 8000
        assert workspace.task_buffer.max_tokens == 64000
        assert workspace.episodic_cache.max_tokens == 256000

    def test_load_query_context(self):
        """Test loading query context into workspace."""
        workspace = CognitiveWorkspace()

        query = "What are the key findings from my research papers?"

        relevant_memories = [
            {
                "id": "mem-1",
                "content": "Research finding 1: AI models benefit from external memory",
                "metadata": {"type": "research", "relevance": "high"},
                "relevance_score": 0.9
            },
            {
                "id": "mem-2",
                "content": "Research finding 2: Attention mechanisms improve retrieval",
                "metadata": {"type": "research", "relevance": "high"},
                "relevance_score": 0.85
            },
            {
                "id": "mem-3",
                "content": "Unrelated note about lunch",
                "metadata": {"type": "note", "relevance": "low"},
                "relevance_score": 0.1
            }
        ]

        formatted_context, stats = workspace.load_query_context(
            query, relevant_memories
        )

        assert formatted_context is not None
        assert len(formatted_context) > 0
        assert stats["memories_processed"] == 3
        assert stats["total_tokens"] > 0

        # High relevance items should be in scratchpad
        assert len(workspace.scratchpad.items) > 0

    def test_distribute_to_buffers(self):
        """Test distribution of items across buffers."""
        workspace = CognitiveWorkspace()

        items = [
            MemoryItem(id="high", content="High attention content", attention_weight=0.9),
            MemoryItem(id="med", content="Medium attention content", attention_weight=0.5),
            MemoryItem(id="low", content="Low attention content", attention_weight=0.2),
        ]

        query = "Test query"
        workspace._distribute_to_buffers(query, items)

        # Check that items are distributed appropriately
        scratchpad_ids = [item.id for item in workspace.scratchpad.items]
        task_buffer_ids = [item.id for item in workspace.task_buffer.items]
        episodic_ids = [item.id for item in workspace.episodic_cache.items]

        # High attention should be in scratchpad
        assert "high" in scratchpad_ids or "high" in task_buffer_ids

        # Low attention should be in episodic cache or task buffer
        assert "low" in episodic_ids or "low" in task_buffer_ids

    def test_workspace_statistics(self):
        """Test getting workspace statistics."""
        workspace = CognitiveWorkspace()

        stats = workspace.get_workspace_statistics()

        assert "buffers" in stats
        assert "total_tokens" in stats
        assert "total_items" in stats
        assert stats["total_tokens"] >= 0

    def test_session_management(self):
        """Test session start and end."""
        workspace = CognitiveWorkspace()

        session_id = "test-session-123"
        workspace.start_session(session_id, metadata={"user": "test_user"})

        assert workspace.session_id == session_id
        assert workspace.session_metadata["user"] == "test_user"

        workspace.end_session()

        assert workspace.session_id is None
        assert len(workspace.session_metadata) == 0

    def test_clear_workspace(self):
        """Test clearing workspace."""
        workspace = CognitiveWorkspace()

        # Add some items
        item = MemoryItem(id="test", content="Test content")
        workspace.scratchpad.add(item)
        workspace.task_buffer.add(item)

        workspace.clear_workspace()

        assert len(workspace.scratchpad.items) == 0
        assert len(workspace.task_buffer.items) == 0
        assert len(workspace.episodic_cache.items) == 0


class TestVectorDatabase:
    """Test VectorDatabase functionality."""

    def test_vector_db_creation(self):
        """Test creating vector database."""
        db = VectorDatabase(
            persist_directory="./test_chroma",
            collection_name="test_collection"
        )

        assert db.collection_name == "test_collection"
        assert db.is_available()

    def test_add_document(self):
        """Test adding a document."""
        db = VectorDatabase(collection_name="test_add_doc")

        if not db.is_available():
            pytest.skip("ChromaDB not available")

        doc_id = str(uuid4())
        success = db.add_document(
            document_id=doc_id,
            content="This is a test document about AI and machine learning",
            metadata={"type": "test", "category": "ml"}
        )

        assert success is True

    def test_search_documents(self):
        """Test searching documents."""
        db = VectorDatabase(collection_name="test_search")

        if not db.is_available():
            pytest.skip("ChromaDB not available")

        # Add some test documents
        db.add_document(
            "doc-1",
            "Artificial intelligence and machine learning",
            {"type": "tech"}
        )
        db.add_document(
            "doc-2",
            "Business contracts and legal documents",
            {"type": "business"}
        )

        # Search
        results = db.search("AI and machine learning", n_results=5)

        assert len(results) > 0
        # First result should be most relevant
        assert "doc-1" in [r["id"] for r in results]

    def test_get_document(self):
        """Test retrieving a specific document."""
        db = VectorDatabase(collection_name="test_get_doc")

        if not db.is_available():
            pytest.skip("ChromaDB not available")

        doc_id = "test-doc-123"
        db.add_document(doc_id, "Test content", {"type": "test"})

        retrieved = db.get_document(doc_id)

        assert retrieved is not None
        assert retrieved["id"] == doc_id
        assert "Test content" in retrieved["content"]

    def test_batch_operations(self):
        """Test batch add and delete."""
        db = VectorDatabase(collection_name="test_batch")

        if not db.is_available():
            pytest.skip("ChromaDB not available")

        documents = [
            {
                "id": f"batch-doc-{i}",
                "content": f"Document {i} content about various topics",
                "metadata": {"batch": True, "index": i}
            }
            for i in range(10)
        ]

        successful, failed = db.add_documents_batch(documents, batch_size=5)

        assert successful == 10
        assert failed == 0

        # Delete batch
        doc_ids = [f"batch-doc-{i}" for i in range(10)]
        deleted, failed = db.delete_documents_batch(doc_ids)

        assert deleted == 10
        assert failed == 0

    def test_count_documents(self):
        """Test counting documents."""
        db = VectorDatabase(collection_name="test_count")

        if not db.is_available():
            pytest.skip("ChromaDB not available")

        # Clear collection first
        db.clear_collection()

        # Add some documents
        for i in range(5):
            db.add_document(f"count-doc-{i}", f"Content {i}", {"type": "test"})

        count = db.count_documents()
        assert count == 5

    def test_statistics(self):
        """Test getting database statistics."""
        db = VectorDatabase(collection_name="test_stats")

        if not db.is_available():
            pytest.skip("ChromaDB not available")

        stats = db.get_statistics()

        assert stats["available"] is True
        assert "total_documents" in stats
        assert "storage_size_bytes" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
