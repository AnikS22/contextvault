#!/usr/bin/env python3
"""Test Graph RAG integration."""

import sys
from pathlib import Path

# Add the contextvault package to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        from contextvault.services.context_retrieval import ContextRetrievalService, GRAPH_RAG_AVAILABLE
        print(f"✅ ContextRetrievalService imported successfully")
        print(f"   Graph RAG available: {GRAPH_RAG_AVAILABLE}")
    except ImportError as e:
        print(f"❌ Failed to import ContextRetrievalService: {e}")
        return False

    try:
        from contextvault.storage.graph_db import GraphRAGDatabase, NEO4J_AVAILABLE, SPACY_AVAILABLE
        print(f"✅ GraphRAGDatabase imported successfully")
        print(f"   Neo4j driver available: {NEO4J_AVAILABLE}")
        print(f"   spaCy available: {SPACY_AVAILABLE}")
    except ImportError as e:
        print(f"❌ Failed to import GraphRAGDatabase: {e}")
        return False

    try:
        from contextvault.integrations.ollama import OllamaIntegration
        print(f"✅ OllamaIntegration imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import OllamaIntegration: {e}")
        return False

    try:
        from contextvault.config import settings
        print(f"✅ Config imported successfully")
        print(f"   Graph RAG enabled: {settings.enable_graph_rag}")
        print(f"   Neo4j URI: {settings.neo4j_uri}")
    except ImportError as e:
        print(f"❌ Failed to import config: {e}")
        return False

    return True


def test_context_retrieval_service():
    """Test ContextRetrievalService with Graph RAG."""
    print("\nTesting ContextRetrievalService initialization...")

    try:
        from contextvault.services.context_retrieval import ContextRetrievalService

        # Test without Graph RAG
        service = ContextRetrievalService(use_graph_rag=False)
        print(f"✅ Created ContextRetrievalService without Graph RAG")
        print(f"   use_graph_rag: {service.use_graph_rag}")

        # Test with Graph RAG (will fail if Neo4j not running, but should initialize)
        service_with_graph = ContextRetrievalService(use_graph_rag=True)
        print(f"✅ Created ContextRetrievalService with Graph RAG enabled")
        print(f"   use_graph_rag: {service_with_graph.use_graph_rag}")
        print(f"   graph_rag_db initialized: {service_with_graph.graph_rag_db is not None}")

        return True
    except Exception as e:
        print(f"❌ Failed to initialize ContextRetrievalService: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_rag_database():
    """Test GraphRAGDatabase initialization."""
    print("\nTesting GraphRAGDatabase initialization...")

    try:
        from contextvault.storage.graph_db import GraphRAGDatabase, NEO4J_AVAILABLE

        if not NEO4J_AVAILABLE:
            print("⚠️  Neo4j driver not available, skipping database test")
            return True

        # Test initialization
        db = GraphRAGDatabase()
        print(f"✅ Created GraphRAGDatabase")
        print(f"   URI: {db.uri}")
        print(f"   Available: {db.is_available()}")

        if not db.is_available():
            print("⚠️  Neo4j is not running (this is expected if you haven't started Neo4j)")

        return True
    except Exception as e:
        print(f"❌ Failed to initialize GraphRAGDatabase: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("Graph RAG Integration Tests")
    print("="*60)

    results = []

    # Test imports
    results.append(("Imports", test_imports()))

    # Test ContextRetrievalService
    results.append(("ContextRetrievalService", test_context_retrieval_service()))

    # Test GraphRAGDatabase
    results.append(("GraphRAGDatabase", test_graph_rag_database()))

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
