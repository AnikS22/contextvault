#!/usr/bin/env python3
"""
Demonstration of the Cognitive Workspace system with unlimited document storage.

This script shows:
1. Document ingestion into vector database
2. Semantic search across massive document corpus
3. Cognitive workspace with 3-layer buffers
4. Attention management and intelligent context assembly
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from contextvault.storage.vector_db import VectorDatabase
from contextvault.storage.document_ingestion import DocumentIngestionPipeline
from contextvault.cognitive.workspace import CognitiveWorkspace
from contextvault.services.token_counter import token_counter

def print_header(title: str):
    """Print formatted header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def demo_document_ingestion():
    """Demonstrate document ingestion."""
    print_header("PHASE 1: Document Ingestion")

    # Initialize vector database
    print("🔧 Initializing vector database...")
    db = VectorDatabase(collection_name="demo_business_docs")

    if not db.is_available():
        print("❌ ChromaDB not available. Please install: pip install chromadb")
        return None

    # Clear previous demo data
    db.clear_collection()
    print("✅ Vector database initialized\n")

    # Create ingestion pipeline
    pipeline = DocumentIngestionPipeline(
        vector_db=db,
        chunk_size=500,
        chunk_overlap=100
    )
    print("✅ Document ingestion pipeline ready\n")

    # Simulate business documents
    print("📄 Ingesting business documents...\n")

    business_documents = [
        {
            "type": "text",
            "content": """
            BUSINESS CONTRACT - Project Alpha

            This agreement is made on January 15, 2024 between Company A and Company B.

            Scope of Work:
            - Development of AI-powered chatbot system
            - Integration with existing CRM platform
            - Training and documentation for staff
            - 6-month support and maintenance period

            Payment Terms:
            - Total contract value: $150,000
            - 40% upfront payment
            - 40% upon delivery
            - 20% after 30-day acceptance period

            Timeline:
            - Phase 1 (Months 1-2): Requirements and design
            - Phase 2 (Months 3-4): Development and testing
            - Phase 3 (Months 5-6): Deployment and training

            Deliverables include source code, documentation, and training materials.
            """,
            "metadata": {
                "type": "contract",
                "category": "business",
                "client": "Company A",
                "project": "Project Alpha",
                "value": 150000,
                "date": "2024-01-15"
            }
        },
        {
            "type": "text",
            "content": """
            BUSINESS CONTRACT - Project Beta

            Agreement dated February 1, 2024 between Company A and Company C.

            Project Scope:
            - Cloud infrastructure migration to AWS
            - Database optimization and scaling
            - Security audit and implementation
            - Performance monitoring setup

            Budget: $85,000

            Payment Schedule:
            - 50% milestone-based payments
            - 50% upon completion

            Project Duration: 4 months

            Technical Requirements:
            - AWS EC2, RDS, S3 integration
            - Multi-region deployment
            - Auto-scaling configuration
            - Backup and disaster recovery setup
            """,
            "metadata": {
                "type": "contract",
                "category": "business",
                "client": "Company A",
                "project": "Project Beta",
                "value": 85000,
                "date": "2024-02-01"
            }
        },
        {
            "type": "text",
            "content": """
            MEETING NOTES - Q1 Strategy Session

            Date: March 10, 2024
            Attendees: CEO, CTO, CFO, Product Team

            Key Discussion Points:

            1. Product Roadmap
            - Focus on AI integration features
            - Customer-requested dashboard improvements
            - Mobile app development (Q2 target)

            2. Budget Allocation
            - 40% to R&D
            - 30% to Sales and Marketing
            - 20% to Operations
            - 10% to Infrastructure

            3. Hiring Plans
            - 3 senior engineers
            - 2 product managers
            - 1 data scientist
            - Target completion: End of Q2

            4. Revenue Targets
            - Q1: $500K (achieved: $520K)
            - Q2: $600K projected
            - Annual target: $2.5M

            Action Items:
            - CTO to draft technical architecture for AI features
            - CFO to finalize Q2 budget
            - Product team to prioritize feature requests
            """,
            "metadata": {
                "type": "meeting_notes",
                "category": "internal",
                "date": "2024-03-10",
                "attendees": ["CEO", "CTO", "CFO"],
                "quarter": "Q1"
            }
        },
        {
            "type": "text",
            "content": """
            EMAIL - Client Follow-up: Project Alpha

            From: john@companya.com
            To: team@ourcompany.com
            Date: March 15, 2024
            Subject: Project Alpha - Phase 2 Feedback

            Hi team,

            Thanks for the excellent progress on Project Alpha. The Phase 1 deliverables
            exceeded our expectations. Here's our feedback for Phase 2:

            Positive Points:
            - User interface is intuitive and modern
            - Response times are excellent
            - Integration with our CRM works seamlessly
            - Staff training materials are comprehensive

            Requests for Phase 2:
            - Add multi-language support (Spanish and French)
            - Implement conversation history export feature
            - Enhance analytics dashboard with custom reports
            - Add role-based access controls

            Budget Discussion:
            We'd like to discuss a scope expansion for the multi-language feature.
            Can we schedule a call next week to review the additional requirements
            and associated costs?

            Looking forward to the continued partnership.

            Best regards,
            John Smith
            Director of IT, Company A
            """,
            "metadata": {
                "type": "email",
                "category": "client_communication",
                "client": "Company A",
                "project": "Project Alpha",
                "date": "2024-03-15",
                "sentiment": "positive"
            }
        },
        {
            "type": "text",
            "content": """
            TECHNICAL DOCUMENTATION - AI Chatbot Architecture

            System Overview:
            The AI chatbot system consists of three main components:

            1. Natural Language Processing Engine
            - Uses transformer-based models (GPT architecture)
            - Context window: 8K tokens
            - Response generation with temperature control
            - Intent classification and entity extraction

            2. Knowledge Base Integration
            - Vector database for semantic search
            - SQL database for structured data
            - API connectors for external systems
            - Caching layer for performance

            3. User Interface Layer
            - Web-based chat interface
            - Mobile-responsive design
            - Real-time message streaming
            - Conversation history management

            Technical Stack:
            - Backend: Python (FastAPI)
            - Frontend: React + TypeScript
            - Database: PostgreSQL + ChromaDB
            - Infrastructure: Docker + Kubernetes
            - Monitoring: Prometheus + Grafana

            Performance Metrics:
            - Average response time: 300ms
            - 99th percentile: 800ms
            - Concurrent users supported: 1000+
            - Uptime: 99.9%

            Security Features:
            - End-to-end encryption
            - OAuth 2.0 authentication
            - Rate limiting
            - Input sanitization
            - Audit logging
            """,
            "metadata": {
                "type": "documentation",
                "category": "technical",
                "project": "Project Alpha",
                "version": "1.0",
                "date": "2024-02-20"
            }
        }
    ]

    # Ingest documents
    stats = pipeline.ingest_batch(business_documents)

    print(f"📊 Ingestion Results:")
    print(f"   - Total documents: {stats['total_items']}")
    print(f"   - Successful: {stats['successful_items']}")
    print(f"   - Failed: {stats['failed_items']}")
    print(f"   - Total chunks: {stats['total_chunks']}")
    print(f"   - Success rate: {stats['success_rate']}%\n")

    # Show database statistics
    db_stats = db.get_statistics()
    print(f"💾 Vector Database Statistics:")
    print(f"   - Total documents: {db_stats['total_documents']}")
    print(f"   - Storage size: {db_stats['storage_size_mb']} MB")
    print(f"   - Collection: {db_stats['collection_name']}\n")

    return db


def demo_semantic_search(db):
    """Demonstrate semantic search."""
    print_header("PHASE 2: Semantic Search")

    queries = [
        "What are the payment terms for Project Alpha?",
        "Tell me about the cloud infrastructure migration",
        "What were the key points from the Q1 strategy meeting?",
    ]

    for query in queries:
        print(f"🔍 Query: \"{query}\"")
        print(f"   Searching across {db.count_documents()} document chunks...\n")

        results = db.search(query, n_results=3)

        print(f"   📋 Top 3 Results:")
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            content_preview = result['content'][:150].replace('\n', ' ')

            print(f"\n   {i}. [{metadata.get('type', 'unknown')}] "
                  f"{metadata.get('project', metadata.get('category', 'N/A'))}")
            print(f"      Distance: {result.get('distance', 0):.4f}")
            print(f"      Preview: {content_preview}...")

        print("\n" + "-" * 80 + "\n")


def demo_cognitive_workspace(db):
    """Demonstrate cognitive workspace with 3-layer buffers."""
    print_header("PHASE 3: Cognitive Workspace & Attention Management")

    # Initialize cognitive workspace
    print("🧠 Initializing Cognitive Workspace...")
    workspace = CognitiveWorkspace(
        scratchpad_tokens=2000,    # Immediate context
        task_buffer_tokens=8000,    # Working memory
        episodic_cache_tokens=32000  # Long-term storage
    )
    print("✅ Workspace initialized with 3-layer buffer system\n")

    # Simulate a complex query
    query = "I need a summary of all active projects, their budgets, and current status"
    print(f"💬 Query: \"{query}\"\n")

    # Search for relevant memories
    print("🔍 Retrieving relevant documents...")
    search_results = db.search(query, n_results=10)
    print(f"   Found {len(search_results)} relevant document chunks\n")

    # Convert search results to memory format
    memories = []
    for result in search_results:
        memories.append({
            "id": result["id"],
            "content": result["content"],
            "metadata": result["metadata"],
            "relevance_score": 1.0 - (result.get("distance", 0) / 2)  # Convert distance to relevance
        })

    # Load into cognitive workspace
    print("🧠 Loading context into cognitive workspace...")
    formatted_context, stats = workspace.load_query_context(
        query=query,
        relevant_memories=memories
    )

    print(f"\n📊 Workspace Statistics:")
    print(f"   - Memories processed: {stats['memories_processed']}")
    print(f"   - Query tokens: {stats['query_tokens']}")
    print(f"   - Total context tokens: {stats['total_tokens']}\n")

    print(f"   📦 Buffer Utilization:")

    # Immediate Scratchpad
    scratchpad_stats = stats['scratchpad']
    print(f"\n   1️⃣  IMMEDIATE SCRATCHPAD (High-priority context)")
    print(f"      - Items: {scratchpad_stats['item_count']}")
    print(f"      - Tokens: {scratchpad_stats['current_tokens']}/{scratchpad_stats['max_tokens']}")
    print(f"      - Utilization: {scratchpad_stats['utilization']}%")
    print(f"      - Strategy: {scratchpad_stats['eviction_strategy']}")

    # Task Buffer
    task_stats = stats['task_buffer']
    print(f"\n   2️⃣  TASK BUFFER (Working memory)")
    print(f"      - Items: {task_stats['item_count']}")
    print(f"      - Tokens: {task_stats['current_tokens']}/{task_stats['max_tokens']}")
    print(f"      - Utilization: {task_stats['utilization']}%")
    print(f"      - Strategy: {task_stats['eviction_strategy']}")

    # Episodic Cache
    episodic_stats = stats['episodic_cache']
    print(f"\n   3️⃣  EPISODIC CACHE (Background knowledge)")
    print(f"      - Items: {episodic_stats['item_count']}")
    print(f"      - Tokens: {episodic_stats['current_tokens']}/{episodic_stats['max_tokens']}")
    print(f"      - Utilization: {episodic_stats['utilization']}%")
    print(f"      - Strategy: {episodic_stats['eviction_strategy']}")

    # Show formatted context preview
    print(f"\n📝 Formatted Context Preview (first 500 chars):")
    print("-" * 80)
    print(formatted_context[:500] + "...")
    print("-" * 80)

    return workspace, formatted_context


def demo_summary():
    """Print demonstration summary."""
    print_header("DEMONSTRATION COMPLETE")

    print("✅ What we've built:\n")
    print("   1. 🗄️  Vector Database (ChromaDB)")
    print("      - Unlimited document storage")
    print("      - Fast semantic search")
    print("      - Persistent local storage\n")

    print("   2. 📥 Document Ingestion Pipeline")
    print("      - Intelligent text chunking")
    print("      - Batch processing")
    print("      - Multiple file format support\n")

    print("   3. 🧠 Cognitive Workspace")
    print("      - 3-layer buffer system (Scratchpad → Task Buffer → Episodic Cache)")
    print("      - Attention-based memory management")
    print("      - Token-aware context assembly\n")

    print("   4. 🎯 Attention Management")
    print("      - Relevance scoring")
    print("      - Recency weighting")
    print("      - Forgetting curves")
    print("      - Access frequency tracking\n")

    print("🎊 YOUR SYSTEM CAN NOW:")
    print("   ✓ Store UNLIMITED business documents")
    print("   ✓ Search semantically across massive corpus")
    print("   ✓ Intelligently prioritize relevant information")
    print("   ✓ Fit context within any model's token window")
    print("   ✓ Maintain attention on high-priority information")
    print("   ✓ Run 100% locally (no cloud dependencies)\n")

    print("📝 Next Steps:")
    print("   - Hierarchical summarization (4-level compression)")
    print("   - Graph-RAG for document relationships")
    print("   - Enhanced CLI (chat/feed/recall commands)")
    print("   - Session persistence\n")


def main():
    """Run the complete demonstration."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  CONTEXTVAULT: COGNITIVE WORKSPACE DEMONSTRATION".center(78) + "║")
    print("║" + "  Unlimited Context + Intelligent Attention Management".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")

    try:
        # Phase 1: Document Ingestion
        db = demo_document_ingestion()
        if not db:
            return

        # Phase 2: Semantic Search
        demo_semantic_search(db)

        # Phase 3: Cognitive Workspace
        demo_cognitive_workspace(db)

        # Summary
        demo_summary()

    except KeyboardInterrupt:
        print("\n\n⚠️  Demonstration interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
