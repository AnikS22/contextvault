"""Graph RAG API endpoints for ContextVault."""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..storage.graph_db import GraphRAGDatabase

logger = logging.getLogger(__name__)

router = APIRouter()

# Global Graph RAG instance
_graph_rag_db: Optional[GraphRAGDatabase] = None


def get_graph_rag() -> GraphRAGDatabase:
    """Get the global Graph RAG database instance."""
    global _graph_rag_db

    if _graph_rag_db is None:
        _graph_rag_db = GraphRAGDatabase()

    return _graph_rag_db


class AddDocumentRequest(BaseModel):
    """Request model for adding documents to Graph RAG."""
    content: str = Field(..., description="Document content to add")
    document_id: str = Field(..., description="Unique document identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    extract_entities: bool = Field(True, description="Whether to extract entities")


class AddDocumentResponse(BaseModel):
    """Response model for adding documents."""
    document_id: str
    entities_extracted: int
    relationships_created: int
    message: str = "Document added successfully"


class SearchRequest(BaseModel):
    """Request model for Graph RAG search."""
    query: str = Field(..., description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    use_graph: bool = Field(True, description="Use graph traversal")
    min_relevance: float = Field(0.5, ge=0.0, le=1.0, description="Minimum relevance score")


class SearchResult(BaseModel):
    """Model for a search result."""
    document_id: str
    content: str
    relevance_score: float
    search_type: str
    matched_entity: Optional[str] = None
    entity_type: Optional[str] = None
    related_entities: List[Dict[str, str]] = []


class SearchResponse(BaseModel):
    """Response model for search."""
    results: List[SearchResult]
    total: int


class EntityRelationshipsRequest(BaseModel):
    """Request model for entity relationships."""
    entity_text: str = Field(..., description="Entity text to search for")
    entity_type: Optional[str] = Field(None, description="Entity type")
    depth: int = Field(1, ge=1, le=3, description="Relationship depth")


class EntityRelationshipsResponse(BaseModel):
    """Response model for entity relationships."""
    entity: Optional[Dict[str, str]]
    relationships: List[Dict[str, str]]


class GraphStatsResponse(BaseModel):
    """Response model for graph statistics."""
    available: bool
    total_documents: int = 0
    total_entities: int = 0
    total_relationships: int = 0
    database: str = "Neo4j Graph RAG"
    error: Optional[str] = None


@router.post("/graph-rag/add", response_model=AddDocumentResponse, status_code=status.HTTP_201_CREATED)
async def add_document(request: AddDocumentRequest):
    """
    Add a document to the Graph RAG database with entity extraction.

    - **content**: Document content
    - **document_id**: Unique document identifier
    - **metadata**: Additional metadata (optional)
    - **extract_entities**: Whether to extract entities (default: True)
    """
    try:
        graph_rag = get_graph_rag()

        if not graph_rag.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Graph RAG is not available. Please ensure Neo4j is running."
            )

        result = graph_rag.add_document(
            content=request.content,
            document_id=request.document_id,
            metadata=request.metadata,
            extract_entities=request.extract_entities
        )

        return AddDocumentResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add document: {str(e)}"
        )


@router.post("/graph-rag/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search the Graph RAG database using hybrid search.

    Combines vector similarity and graph traversal for intelligent results.

    - **query**: Search query
    - **limit**: Maximum number of results (1-100)
    - **use_graph**: Whether to use graph traversal
    - **min_relevance**: Minimum relevance score (0.0-1.0)
    """
    try:
        graph_rag = get_graph_rag()

        if not graph_rag.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Graph RAG is not available. Please ensure Neo4j is running."
            )

        results = graph_rag.search(
            query=request.query,
            limit=request.limit,
            use_graph=request.use_graph,
            min_relevance=request.min_relevance
        )

        return SearchResponse(
            results=[SearchResult(**r) for r in results],
            total=len(results)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Graph RAG search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/graph-rag/entity-relationships", response_model=EntityRelationshipsResponse)
async def get_entity_relationships(request: EntityRelationshipsRequest):
    """
    Get all relationships for an entity.

    - **entity_text**: Entity text to search for
    - **entity_type**: Entity type (optional)
    - **depth**: Relationship depth (1-3)
    """
    try:
        graph_rag = get_graph_rag()

        if not graph_rag.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Graph RAG is not available. Please ensure Neo4j is running."
            )

        result = graph_rag.get_entity_relationships(
            entity_text=request.entity_text,
            entity_type=request.entity_type,
            depth=request.depth
        )

        return EntityRelationshipsResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entity relationships: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get entity relationships: {str(e)}"
        )


@router.get("/graph-rag/stats", response_model=GraphStatsResponse)
async def get_stats():
    """
    Get Graph RAG database statistics.

    Returns information about the number of documents, entities, and relationships.
    """
    try:
        graph_rag = get_graph_rag()
        stats = graph_rag.get_statistics()
        return GraphStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get graph stats: {e}", exc_info=True)
        return GraphStatsResponse(
            available=False,
            error=str(e)
        )


@router.get("/graph-rag/health")
async def health_check():
    """
    Check Graph RAG health status.

    Returns whether Graph RAG is available and ready to use.
    """
    try:
        graph_rag = get_graph_rag()
        is_available = graph_rag.is_available()

        return {
            "status": "healthy" if is_available else "unavailable",
            "available": is_available,
            "message": "Graph RAG is ready" if is_available else "Neo4j is not running or not configured"
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "available": False,
            "message": f"Error: {str(e)}"
        }
