"""Mem0 Memory API Endpoints."""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response models
class AddMemoryRequest(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None
    extract_relationships: bool = True

class SearchMemoriesRequest(BaseModel):
    query: str
    limit: int = 10
    include_relationships: bool = True

class MemoryResponse(BaseModel):
    memory_id: str
    content: str
    score: Optional[float] = None
    metadata: Dict[str, Any] = {}
    relationships: Optional[Dict[str, Any]] = None


@router.post("/mem0/add", status_code=status.HTTP_201_CREATED)
async def add_memory(request: AddMemoryRequest):
    """Add a memory to Mem0."""
    try:
        from ..services.mem0_service import get_mem0_service

        mem0 = get_mem0_service()

        if not mem0.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Mem0 service is not available"
            )

        result = mem0.add_memory(
            content=request.content,
            metadata=request.metadata,
            extract_relationships=request.extract_relationships
        )

        return result

    except Exception as e:
        logger.error(f"Failed to add memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/mem0/search")
async def search_memories(request: SearchMemoriesRequest):
    """Search memories using Mem0."""
    try:
        from ..services.mem0_service import get_mem0_service

        mem0 = get_mem0_service()

        if not mem0.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Mem0 service is not available"
            )

        results = mem0.search_memories(
            query=request.query,
            limit=request.limit,
            include_relationships=request.include_relationships
        )

        return {"results": results, "total": len(results)}

    except Exception as e:
        logger.error(f"Failed to search memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/mem0/list")
async def list_memories(limit: Optional[int] = None):
    """List all memories."""
    try:
        from ..services.mem0_service import get_mem0_service

        mem0 = get_mem0_service()

        if not mem0.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Mem0 service is not available"
            )

        memories = mem0.get_all_memories(limit=limit)

        return {"memories": memories, "total": len(memories)}

    except Exception as e:
        logger.error(f"Failed to list memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/mem0/relationships")
async def get_relationships(
    entity: Optional[str] = None,
    memory_id: Optional[str] = None
):
    """Get relationships from NetworkX graph."""
    try:
        from ..services.mem0_service import get_mem0_service

        mem0 = get_mem0_service()

        if not mem0.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Mem0 service is not available"
            )

        relationships = mem0.get_relationships(entity=entity, memory_id=memory_id)

        return {"relationships": relationships, "total": len(relationships)}

    except Exception as e:
        logger.error(f"Failed to get relationships: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/mem0/stats")
async def get_stats():
    """Get Mem0 and graph statistics."""
    try:
        from ..services.mem0_service import get_mem0_service

        mem0 = get_mem0_service()

        if not mem0.is_available():
            return {
                "available": False,
                "error": "Mem0 service not available"
            }

        # Get all memories count
        memories = mem0.get_all_memories()

        # Get graph stats
        graph_stats = mem0.get_graph_statistics()

        return {
            "available": True,
            "total_memories": len(memories),
            "graph": graph_stats
        }

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
