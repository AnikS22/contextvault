"""API endpoints for multi-model routing."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from ..routing import model_router, model_profile_service, workload_splitter
from ..models import ModelCapabilityType, RoutingStrategy

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response models
class RegisterModelRequest(BaseModel):
    """Request model for registering a new model."""

    model_id: str = Field(..., description="Unique model identifier")
    model_name: Optional[str] = Field(None, description="Human-readable model name")
    capabilities: List[str] = Field(default_factory=list, description="List of capabilities")
    capability_scores: Optional[Dict[str, float]] = Field(None, description="Scores for each capability")
    estimated_memory_mb: Optional[int] = Field(None, description="Memory requirement in MB")
    requires_gpu: bool = Field(False, description="Whether GPU is required")
    max_concurrent_requests: int = Field(1, description="Max concurrent requests")
    priority: int = Field(0, description="Priority level for routing")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")


class RouteRequestModel(BaseModel):
    """Request model for routing a query."""

    text: str = Field(..., description="Text to route")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")
    strategy: Optional[str] = Field(None, description="Routing strategy")
    required_capabilities: Optional[List[str]] = Field(None, description="Required capabilities")
    exclude_models: Optional[List[str]] = Field(None, description="Models to exclude")
    prefer_models: Optional[List[str]] = Field(None, description="Models to prefer")


class DecomposeRequestModel(BaseModel):
    """Request model for workload decomposition."""

    text: str = Field(..., description="Text to decompose")
    max_sub_tasks: int = Field(10, description="Maximum number of sub-tasks")


class UpdatePerformanceRequest(BaseModel):
    """Request model for updating model performance."""

    model_id: str = Field(..., description="Model identifier")
    latency_ms: float = Field(..., description="Latency in milliseconds")
    tokens_per_second: Optional[float] = Field(None, description="Tokens per second")
    success: bool = Field(True, description="Whether request succeeded")
    quality_score: Optional[float] = Field(None, description="Quality score (0.0-1.0)")


class CompleteRoutingRequest(BaseModel):
    """Request model for completing a routing decision."""

    decision_id: str = Field(..., description="Routing decision ID")
    success: bool = Field(..., description="Whether request succeeded")
    latency_ms: float = Field(..., description="Latency in milliseconds")
    tokens_generated: Optional[int] = Field(None, description="Tokens generated")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    quality_score: Optional[float] = Field(None, description="Quality score (0.0-1.0)")


# Model Management Endpoints
@router.post("/models/register", tags=["Model Management"])
async def register_model(request: RegisterModelRequest):
    """Register a new model or update existing profile."""
    try:
        profile = model_profile_service.register_model(
            model_id=request.model_id,
            model_name=request.model_name,
            capabilities=request.capabilities,
            capability_scores=request.capability_scores,
            estimated_memory_mb=request.estimated_memory_mb,
            requires_gpu=request.requires_gpu,
            max_concurrent_requests=request.max_concurrent_requests,
            priority=request.priority,
            tags=request.tags,
        )

        return {
            "success": True,
            "message": f"Model {request.model_id} registered successfully",
            "profile": profile.to_dict()
        }

    except Exception as e:
        logger.error(f"Failed to register model: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models", tags=["Model Management"])
async def list_models(
    active_only: bool = Query(True, description="Only return active models"),
    has_capability: Optional[str] = Query(None, description="Filter by capability"),
    requires_gpu: Optional[bool] = Query(None, description="Filter by GPU requirement"),
    min_priority: Optional[int] = Query(None, description="Minimum priority level")
):
    """List all registered models with optional filtering."""
    try:
        profiles = model_profile_service.list_profiles(
            active_only=active_only,
            has_capability=has_capability,
            requires_gpu=requires_gpu,
            min_priority=min_priority
        )

        return {
            "success": True,
            "count": len(profiles),
            "models": [p.to_dict() for p in profiles]
        }

    except Exception as e:
        logger.error(f"Failed to list models: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}", tags=["Model Management"])
async def get_model(model_id: str):
    """Get model capability profile by ID."""
    try:
        profile = model_profile_service.get_profile(model_id)

        if not profile:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

        return {
            "success": True,
            "profile": profile.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/{model_id}/activate", tags=["Model Management"])
async def activate_model(model_id: str):
    """Activate a model (make available for routing)."""
    try:
        success = model_profile_service.activate_model(model_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

        return {
            "success": True,
            "message": f"Model {model_id} activated"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate model: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/{model_id}/deactivate", tags=["Model Management"])
async def deactivate_model(model_id: str):
    """Deactivate a model (make unavailable for routing)."""
    try:
        success = model_profile_service.deactivate_model(model_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

        return {
            "success": True,
            "message": f"Model {model_id} deactivated"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deactivate model: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}/stats", tags=["Model Management"])
async def get_model_stats(
    model_id: str,
    days: int = Query(7, description="Number of days to analyze")
):
    """Get performance statistics for a model."""
    try:
        stats = model_profile_service.get_performance_stats(model_id, days)

        if "error" in stats:
            raise HTTPException(status_code=404, detail=stats["error"])

        return {
            "success": True,
            "stats": stats
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/{model_id}/auto-tune", tags=["Model Management"])
async def auto_tune_model(
    model_id: str,
    days: int = Query(30, description="Number of days to analyze")
):
    """Auto-tune capability scores based on recent performance."""
    try:
        success = model_profile_service.auto_tune_capability_scores(model_id, days)

        if not success:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found or no data")

        return {
            "success": True,
            "message": f"Auto-tuned capability scores for {model_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to auto-tune model: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Routing Endpoints
@router.post("/route", tags=["Routing"])
async def route_request(request: RouteRequestModel):
    """Route a request to the most appropriate model."""
    try:
        model_id, decision = model_router.route_request(
            request_text=request.text,
            session_id=request.session_id,
            strategy=request.strategy,
            required_capabilities=request.required_capabilities,
            exclude_models=request.exclude_models,
            prefer_models=request.prefer_models
        )

        return {
            "success": True,
            "selected_model": model_id,
            "decision": decision.to_dict()
        }

    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to route request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/route/complete", tags=["Routing"])
async def complete_routing(request: CompleteRoutingRequest):
    """Complete a routing decision with outcome metrics."""
    try:
        success = model_router.complete_routing_decision(
            decision_id=request.decision_id,
            success=request.success,
            latency_ms=request.latency_ms,
            tokens_generated=request.tokens_generated,
            error_message=request.error_message,
            quality_score=request.quality_score
        )

        if not success:
            raise HTTPException(status_code=404, detail="Routing decision not found")

        return {
            "success": True,
            "message": "Routing decision completed"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete routing: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/route/stats", tags=["Routing"])
async def get_routing_stats(days: int = Query(7, description="Number of days to analyze")):
    """Get routing statistics for the specified period."""
    try:
        stats = model_router.get_routing_stats(days)

        if "error" in stats:
            raise HTTPException(status_code=500, detail=stats["error"])

        return {
            "success": True,
            "stats": stats
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get routing stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Workload Decomposition Endpoints
@router.post("/decompose", tags=["Workload Decomposition"])
async def decompose_workload(request: DecomposeRequestModel):
    """Decompose a complex task into sub-tasks."""
    try:
        decomposition = workload_splitter.decompose(
            text=request.text,
            max_sub_tasks=request.max_sub_tasks
        )

        return {
            "success": True,
            "decomposition": decomposition.to_dict()
        }

    except Exception as e:
        logger.error(f"Failed to decompose workload: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decompose/should-split", tags=["Workload Decomposition"])
async def should_split_workload(text: str = Body(..., embed=True)):
    """Check if a task should be split into sub-tasks."""
    try:
        should_split = workload_splitter.should_split(text)

        return {
            "success": True,
            "should_split": should_split
        }

    except Exception as e:
        logger.error(f"Failed to check if should split: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Performance Update Endpoint
@router.post("/performance/update", tags=["Performance"])
async def update_performance(request: UpdatePerformanceRequest):
    """Update performance metrics for a model."""
    try:
        success = model_profile_service.update_performance(
            model_id=request.model_id,
            latency_ms=request.latency_ms,
            tokens_per_second=request.tokens_per_second,
            success=request.success,
            quality_score=request.quality_score
        )

        if not success:
            raise HTTPException(status_code=404, detail=f"Model {request.model_id} not found")

        return {
            "success": True,
            "message": f"Performance updated for {request.model_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update performance: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Capability Detection Endpoint
@router.post("/capabilities/detect", tags=["Capabilities"])
async def detect_capabilities(text: str = Body(..., embed=True)):
    """Detect required capabilities from input text."""
    try:
        capabilities = model_router.detect_capabilities(text)

        return {
            "success": True,
            "text": text,
            "detected_capabilities": capabilities
        }

    except Exception as e:
        logger.error(f"Failed to detect capabilities: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Info Endpoints
@router.get("/capabilities/types", tags=["Info"])
async def list_capability_types():
    """List all available capability types."""
    return {
        "success": True,
        "capability_types": [cap.value for cap in ModelCapabilityType]
    }


@router.get("/strategies", tags=["Info"])
async def list_routing_strategies():
    """List all available routing strategies."""
    return {
        "success": True,
        "routing_strategies": [strategy.value for strategy in RoutingStrategy],
        "descriptions": {
            "round_robin": "Distribute requests evenly across capable models",
            "capability_based": "Route based on capability match and scores",
            "performance_based": "Route based on latency and success rate",
            "load_balanced": "Route based on current load and routing weights",
            "specialized": "Route to most specialized model for required capabilities"
        }
    }
