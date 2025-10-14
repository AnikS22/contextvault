"""Session manager for extended thinking sessions."""

import asyncio
import uuid
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session as DBSession

from ..database import get_db_context
from ..models.thinking import (
    ThinkingSession,
    Thought,
    SubQuestion,
    ThinkingSynthesis,
    ThinkingStatus,
)
from .thinking_engine import ThinkingEngine

logger = logging.getLogger(__name__)


class ThinkingSessionManager:
    """
    Manages lifecycle of thinking sessions.

    Handles:
    - Starting new thinking sessions
    - Pausing and resuming sessions
    - Retrieving session status and data
    - Managing concurrent sessions
    """

    def __init__(self, thinking_engine: Optional[ThinkingEngine] = None):
        """
        Initialize the session manager.

        Args:
            thinking_engine: Thinking engine instance (uses global if not provided)
        """
        from .thinking_engine import thinking_engine as default_engine
        self.thinking_engine = thinking_engine or default_engine

        # Track running session tasks
        self._running_tasks: Dict[str, asyncio.Task] = {}

    async def start_session(
        self,
        question: str,
        duration_minutes: int,
        model_id: str = "llama3.1",
        synthesis_interval_seconds: int = 300
    ) -> ThinkingSession:
        """
        Start a new extended thinking session.

        Args:
            question: The question or problem to think about
            duration_minutes: How long to think (in minutes)
            model_id: Which AI model to use for thinking
            synthesis_interval_seconds: How often to synthesize understanding

        Returns:
            Created thinking session

        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If session creation fails
        """
        # Validate inputs
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        if duration_minutes < 1:
            raise ValueError("Duration must be at least 1 minute")

        if duration_minutes > 240:  # 4 hours max
            raise ValueError("Duration cannot exceed 240 minutes (4 hours)")

        try:
            with get_db_context() as db:
                # Create session
                session = ThinkingSession(
                    id=str(uuid.uuid4()),
                    original_question=question.strip(),
                    thinking_duration_minutes=duration_minutes,
                    model_id=model_id,
                    status=ThinkingStatus.CREATED.value,
                    total_thoughts=0,
                    total_questions=0,
                    total_syntheses=0,
                    confidence_evolution=[]
                )

                db.add(session)
                db.commit()
                db.refresh(session)

                session_id = session.id

                logger.info(
                    f"Created thinking session {session_id}: "
                    f"{duration_minutes}min on '{question[:50]}...'"
                )

            # Start thinking in background
            await self._start_thinking_task(session_id, synthesis_interval_seconds)

            return session

        except Exception as e:
            logger.error(f"Failed to start thinking session: {e}", exc_info=True)
            raise RuntimeError(f"Failed to start thinking session: {str(e)}")

    async def _start_thinking_task(
        self,
        session_id: str,
        synthesis_interval_seconds: int
    ) -> None:
        """Start the background thinking task for a session."""

        async def thinking_task():
            """Background task that runs the thinking engine."""
            try:
                with get_db_context() as db:
                    session = db.query(ThinkingSession).filter(
                        ThinkingSession.id == session_id
                    ).first()

                    if not session:
                        logger.error(f"Session {session_id} not found")
                        return

                    # Run thinking engine
                    await self.thinking_engine.think(
                        session=session,
                        db_session=db,
                        synthesis_interval_seconds=synthesis_interval_seconds
                    )

            except Exception as e:
                logger.error(f"Thinking task failed for session {session_id}: {e}", exc_info=True)

                # Mark session as failed
                try:
                    with get_db_context() as db:
                        session = db.query(ThinkingSession).filter(
                            ThinkingSession.id == session_id
                        ).first()

                        if session:
                            session.status = ThinkingStatus.FAILED.value
                            session.error_message = str(e)
                            session.completed_at = datetime.utcnow()
                            db.commit()
                except Exception:
                    pass

            finally:
                # Remove from running tasks
                if session_id in self._running_tasks:
                    del self._running_tasks[session_id]

        # Create and start task
        task = asyncio.create_task(thinking_task())
        self._running_tasks[session_id] = task

        logger.info(f"Started thinking task for session {session_id}")

    async def pause_session(self, session_id: str) -> bool:
        """
        Pause a running thinking session.

        Args:
            session_id: ID of the session to pause

        Returns:
            True if session was paused, False otherwise
        """
        try:
            with get_db_context() as db:
                session = db.query(ThinkingSession).filter(
                    ThinkingSession.id == session_id
                ).first()

                if not session:
                    logger.warning(f"Session {session_id} not found")
                    return False

                if session.status != ThinkingStatus.THINKING.value:
                    logger.warning(f"Session {session_id} is not currently thinking (status: {session.status})")
                    return False

                # Update status
                session.status = ThinkingStatus.PAUSED.value
                session.paused_at = datetime.utcnow()
                db.commit()

                logger.info(f"Paused thinking session {session_id}")

                return True

        except Exception as e:
            logger.error(f"Failed to pause session {session_id}: {e}", exc_info=True)
            return False

    async def resume_session(
        self,
        session_id: str,
        synthesis_interval_seconds: int = 300
    ) -> bool:
        """
        Resume a paused thinking session.

        Args:
            session_id: ID of the session to resume
            synthesis_interval_seconds: Synthesis interval

        Returns:
            True if session was resumed, False otherwise
        """
        try:
            with get_db_context() as db:
                session = db.query(ThinkingSession).filter(
                    ThinkingSession.id == session_id
                ).first()

                if not session:
                    logger.warning(f"Session {session_id} not found")
                    return False

                if session.status != ThinkingStatus.PAUSED.value:
                    logger.warning(f"Session {session_id} is not paused (status: {session.status})")
                    return False

                # Calculate how long session was paused
                if session.paused_at:
                    pause_duration = datetime.utcnow() - session.paused_at
                    # Extend thinking duration to account for pause
                    additional_minutes = int(pause_duration.total_seconds() / 60)
                    session.thinking_duration_minutes += additional_minutes

                # Update status (don't commit yet, let thinking task handle it)
                session.status = ThinkingStatus.CREATED.value

                db.commit()

            # Restart thinking task
            await self._start_thinking_task(session_id, synthesis_interval_seconds)

            logger.info(f"Resumed thinking session {session_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to resume session {session_id}: {e}", exc_info=True)
            return False

    def get_session(self, session_id: str) -> Optional[ThinkingSession]:
        """
        Get a thinking session by ID.

        Args:
            session_id: ID of the session

        Returns:
            ThinkingSession or None if not found
        """
        try:
            with get_db_context() as db:
                session = db.query(ThinkingSession).filter(
                    ThinkingSession.id == session_id
                ).first()

                return session

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}", exc_info=True)
            return None

    def get_thinking_stream(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Thought]:
        """
        Get the stream of consciousness for a session.

        Args:
            session_id: ID of the session
            limit: Maximum number of thoughts to return

        Returns:
            List of thoughts in chronological order
        """
        try:
            with get_db_context() as db:
                query = db.query(Thought).filter(
                    Thought.session_id == session_id
                ).order_by(Thought.sequence_number)

                if limit:
                    query = query.limit(limit)

                return query.all()

        except Exception as e:
            logger.error(f"Failed to get thinking stream for {session_id}: {e}", exc_info=True)
            return []

    def get_sub_questions(
        self,
        session_id: str,
        explored_only: bool = False,
        unexplored_only: bool = False
    ) -> List[SubQuestion]:
        """
        Get sub-questions for a session.

        Args:
            session_id: ID of the session
            explored_only: Only return explored questions
            unexplored_only: Only return unexplored questions

        Returns:
            List of sub-questions
        """
        try:
            with get_db_context() as db:
                query = db.query(SubQuestion).filter(
                    SubQuestion.session_id == session_id
                )

                if explored_only:
                    query = query.filter(SubQuestion.explored == True)
                elif unexplored_only:
                    query = query.filter(SubQuestion.explored == False)

                return query.order_by(SubQuestion.priority.desc()).all()

        except Exception as e:
            logger.error(f"Failed to get sub-questions for {session_id}: {e}", exc_info=True)
            return []

    def get_syntheses(self, session_id: str) -> List[ThinkingSynthesis]:
        """
        Get all syntheses for a session.

        Args:
            session_id: ID of the session

        Returns:
            List of syntheses in chronological order
        """
        try:
            with get_db_context() as db:
                return db.query(ThinkingSynthesis).filter(
                    ThinkingSynthesis.session_id == session_id
                ).order_by(ThinkingSynthesis.sequence_number).all()

        except Exception as e:
            logger.error(f"Failed to get syntheses for {session_id}: {e}", exc_info=True)
            return []

    def list_sessions(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[ThinkingSession]:
        """
        List thinking sessions.

        Args:
            status: Filter by status (optional)
            limit: Maximum number of sessions to return

        Returns:
            List of thinking sessions
        """
        try:
            with get_db_context() as db:
                query = db.query(ThinkingSession)

                if status:
                    query = query.filter(ThinkingSession.status == status)

                return query.order_by(
                    ThinkingSession.created_at.desc()
                ).limit(limit).all()

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}", exc_info=True)
            return []

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics for a thinking session.

        Args:
            session_id: ID of the session

        Returns:
            Dictionary with session statistics
        """
        try:
            with get_db_context() as db:
                session = db.query(ThinkingSession).filter(
                    ThinkingSession.id == session_id
                ).first()

                if not session:
                    return {"error": "Session not found"}

                thoughts = db.query(Thought).filter(
                    Thought.session_id == session_id
                ).all()

                questions = db.query(SubQuestion).filter(
                    SubQuestion.session_id == session_id
                ).all()

                syntheses = db.query(ThinkingSynthesis).filter(
                    ThinkingSynthesis.session_id == session_id
                ).all()

                # Calculate stats
                avg_confidence = sum(t.confidence for t in thoughts) / len(thoughts) if thoughts else 0.0

                thought_types = {}
                for thought in thoughts:
                    thought_types[thought.thought_type] = thought_types.get(thought.thought_type, 0) + 1

                explored_questions = sum(1 for q in questions if q.explored)

                return {
                    "session_id": session_id,
                    "status": session.status,
                    "progress_percentage": session.get_progress_percentage(),
                    "elapsed_seconds": session.get_elapsed_seconds(),
                    "thoughts": {
                        "total": len(thoughts),
                        "by_type": thought_types,
                        "average_confidence": avg_confidence,
                    },
                    "questions": {
                        "total": len(questions),
                        "explored": explored_questions,
                        "unexplored": len(questions) - explored_questions,
                    },
                    "syntheses": {
                        "total": len(syntheses),
                        "confidence_evolution": [s.confidence_level for s in syntheses],
                    },
                }

        except Exception as e:
            logger.error(f"Failed to get stats for {session_id}: {e}", exc_info=True)
            return {"error": str(e)}

    def is_session_running(self, session_id: str) -> bool:
        """
        Check if a session has a running background task.

        Args:
            session_id: ID of the session

        Returns:
            True if session has a running task
        """
        return session_id in self._running_tasks

    async def stop_all_sessions(self) -> None:
        """Stop all running thinking sessions (for shutdown)."""
        logger.info(f"Stopping {len(self._running_tasks)} running thinking sessions")

        # Pause all running sessions in database
        try:
            with get_db_context() as db:
                db.query(ThinkingSession).filter(
                    ThinkingSession.status == ThinkingStatus.THINKING.value
                ).update({
                    "status": ThinkingStatus.PAUSED.value,
                    "paused_at": datetime.utcnow()
                })
                db.commit()
        except Exception as e:
            logger.error(f"Error pausing sessions during shutdown: {e}")

        # Cancel all tasks
        for session_id, task in list(self._running_tasks.items()):
            try:
                task.cancel()
                await asyncio.wait_for(task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                logger.error(f"Error stopping task for session {session_id}: {e}")

        self._running_tasks.clear()

        logger.info("All thinking sessions stopped")


# Global session manager instance
session_manager = ThinkingSessionManager()
