"""API endpoints for extended thinking sessions."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from ..thinking import session_manager
from ..models.thinking import ThinkingStatus

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response models
class StartThinkingRequest(BaseModel):
    """Request model for starting a thinking session."""

    question: str = Field(..., description="Question or problem to think about", min_length=10)
    duration_minutes: int = Field(30, description="Thinking duration in minutes", ge=1, le=240)
    model_id: str = Field("llama3.1", description="AI model to use for thinking")
    synthesis_interval_seconds: int = Field(300, description="How often to synthesize (seconds)", ge=60)


class ThinkingSessionResponse(BaseModel):
    """Response model for thinking session."""

    session_id: str
    question: str
    status: str
    duration_minutes: int
    progress: Dict[str, Any]
    started_at: Optional[str]
    completed_at: Optional[str]


# Endpoints
@router.post("/start", tags=["Extended Thinking"])
async def start_thinking(request: StartThinkingRequest):
    """
    Start a new extended thinking session.

    The AI will think about the question for the specified duration,
    autonomously exploring different aspects, generating sub-questions,
    and evolving its understanding over time.
    """
    try:
        session = await session_manager.start_session(
            question=request.question,
            duration_minutes=request.duration_minutes,
            model_id=request.model_id,
            synthesis_interval_seconds=request.synthesis_interval_seconds
        )

        return {
            "success": True,
            "session_id": session.id,
            "status": session.status,
            "message": f"Thinking session started for {request.duration_minutes} minutes",
            "session": session.to_dict()
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start thinking session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start thinking session: {str(e)}")


@router.get("/{session_id}", tags=["Extended Thinking"])
async def get_thinking_session(session_id: str):
    """
    Get current status and progress of a thinking session.

    Returns the session details including:
    - Current status (thinking, paused, completed)
    - Progress metrics (thoughts, questions, syntheses)
    - Confidence evolution
    - Final answer (if completed)
    """
    try:
        session = session_manager.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        return {
            "success": True,
            "session": session.to_dict(include_details=True)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/stream", tags=["Extended Thinking"])
async def get_thinking_stream(
    session_id: str,
    limit: Optional[int] = Query(None, description="Max number of thoughts to return")
):
    """
    Get the AI's stream of consciousness for a thinking session.

    Returns all thoughts in chronological order, showing how the AI's
    thinking evolved over time.
    """
    try:
        thoughts = session_manager.get_thinking_stream(session_id, limit=limit)

        return {
            "success": True,
            "session_id": session_id,
            "thought_count": len(thoughts),
            "thoughts": [thought.to_dict() for thought in thoughts]
        }

    except Exception as e:
        logger.error(f"Failed to get thinking stream for {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/questions", tags=["Extended Thinking"])
async def get_sub_questions(
    session_id: str,
    explored_only: bool = Query(False, description="Only return explored questions"),
    unexplored_only: bool = Query(False, description="Only return unexplored questions")
):
    """
    Get sub-questions generated during thinking.

    As the AI thinks, it discovers new questions that arise from its exploration.
    This endpoint returns those questions, which can be filtered by exploration status.
    """
    try:
        questions = session_manager.get_sub_questions(
            session_id=session_id,
            explored_only=explored_only,
            unexplored_only=unexplored_only
        )

        return {
            "success": True,
            "session_id": session_id,
            "question_count": len(questions),
            "questions": [q.to_dict() for q in questions]
        }

    except Exception as e:
        logger.error(f"Failed to get sub-questions for {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/syntheses", tags=["Extended Thinking"])
async def get_syntheses(session_id: str):
    """
    Get all syntheses for a thinking session.

    Syntheses are periodic summaries of the AI's current understanding.
    This endpoint returns all syntheses in chronological order, showing
    how understanding evolved during the thinking session.
    """
    try:
        syntheses = session_manager.get_syntheses(session_id)

        return {
            "success": True,
            "session_id": session_id,
            "synthesis_count": len(syntheses),
            "syntheses": [s.to_dict() for s in syntheses]
        }

    except Exception as e:
        logger.error(f"Failed to get syntheses for {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/stats", tags=["Extended Thinking"])
async def get_session_stats(session_id: str):
    """
    Get detailed statistics for a thinking session.

    Returns analytics including:
    - Thought distribution by type
    - Average confidence levels
    - Question exploration status
    - Confidence evolution over time
    """
    try:
        stats = session_manager.get_session_stats(session_id)

        if "error" in stats:
            raise HTTPException(status_code=404, detail=stats["error"])

        return {
            "success": True,
            "stats": stats
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stats for {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/pause", tags=["Extended Thinking"])
async def pause_thinking(session_id: str):
    """
    Pause a running thinking session.

    The session can be resumed later to continue thinking.
    """
    try:
        success = await session_manager.pause_session(session_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot pause session {session_id} (not found or not running)"
            )

        return {
            "success": True,
            "session_id": session_id,
            "message": "Thinking session paused"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/resume", tags=["Extended Thinking"])
async def resume_thinking(
    session_id: str,
    synthesis_interval_seconds: int = Query(300, description="Synthesis interval in seconds", ge=60)
):
    """
    Resume a paused thinking session.

    The session will continue thinking from where it left off.
    The time spent paused is added to the thinking duration.
    """
    try:
        success = await session_manager.resume_session(
            session_id=session_id,
            synthesis_interval_seconds=synthesis_interval_seconds
        )

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume session {session_id} (not found or not paused)"
            )

        return {
            "success": True,
            "session_id": session_id,
            "message": "Thinking session resumed"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", tags=["Extended Thinking"])
async def list_sessions(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Max sessions to return", ge=1, le=200)
):
    """
    List thinking sessions.

    Returns a list of thinking sessions, optionally filtered by status.
    """
    try:
        # Validate status if provided
        if status and status not in [s.value for s in ThinkingStatus]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in ThinkingStatus]}"
            )

        sessions = session_manager.list_sessions(status=status, limit=limit)

        return {
            "success": True,
            "session_count": len(sessions),
            "sessions": [s.to_dict() for s in sessions]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/export", tags=["Extended Thinking"])
async def export_session(session_id: str):
    """
    Export complete thinking session data.

    Returns all data for a session in a comprehensive format suitable
    for analysis or archiving.
    """
    try:
        session = session_manager.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        thoughts = session_manager.get_thinking_stream(session_id)
        questions = session_manager.get_sub_questions(session_id)
        syntheses = session_manager.get_syntheses(session_id)

        return {
            "success": True,
            "session": session.to_dict(include_details=True),
            "thoughts": [t.to_dict() for t in thoughts],
            "sub_questions": [q.to_dict() for q in questions],
            "syntheses": [s.to_dict() for s in syntheses],
            "export_metadata": {
                "exported_at": __import__('datetime').datetime.utcnow().isoformat(),
                "total_thoughts": len(thoughts),
                "total_questions": len(questions),
                "total_syntheses": len(syntheses)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
