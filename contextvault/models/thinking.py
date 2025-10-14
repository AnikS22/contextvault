"""SQLAlchemy models for extended thinking sessions."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum as PyEnum

from sqlalchemy import JSON, DateTime, String, Text, func, Integer, Float, Boolean, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class ThinkingStatus(str, PyEnum):
    """Status of a thinking session."""
    CREATED = "created"
    THINKING = "thinking"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ThoughtType(str, PyEnum):
    """Types of thoughts during thinking."""
    EXPLORATION = "exploration"      # Exploring a concept or idea
    CRITIQUE = "critique"            # Questioning or critiquing assumptions
    CONNECTION = "connection"        # Making connections between ideas
    INSIGHT = "insight"              # New understanding or realization
    QUESTION = "question"            # Generating a new question
    SYNTHESIS = "synthesis"          # Combining multiple thoughts


class ThinkingSession(Base):
    """
    A long-running thinking session where AI explores a question over time.

    Unlike immediate responses, thinking sessions allow AI to spend minutes
    or hours exploring a problem, generating sub-questions, and evolving
    its understanding.
    """

    __tablename__ = "thinking_sessions"

    # Primary identifier
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the thinking session"
    )

    # Core question and configuration
    original_question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The question or problem to think about"
    )

    thinking_duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Allocated thinking time in minutes"
    )

    # Model configuration
    model_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="AI model used for thinking"
    )

    # Session status
    status: Mapped[str] = mapped_column(
        Enum("created", "thinking", "paused", "completed", "failed", name="thinking_status_enum"),
        nullable=False,
        default=ThinkingStatus.CREATED.value,
        comment="Current status of the thinking session"
    )

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When thinking started"
    )

    paused_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When thinking was paused"
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When thinking completed"
    )

    # Progress tracking
    total_thoughts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Total number of thoughts generated"
    )

    total_questions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Total number of sub-questions generated"
    )

    total_syntheses: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Total number of syntheses created"
    )

    current_focus: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="What the AI is currently thinking about"
    )

    # Results
    final_synthesis: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Final answer/synthesis after thinking"
    )

    confidence_evolution: Mapped[Optional[List[float]]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        comment="Confidence scores over time (0.0-1.0)"
    )

    # Metadata
    session_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: {},
        comment="Additional session metadata"
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if session failed"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="When the session was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="When the session was last updated"
    )

    def __repr__(self) -> str:
        """String representation of the thinking session."""
        return (
            f"<ThinkingSession(id='{self.id}', "
            f"status='{self.status}', "
            f"thoughts={self.total_thoughts})>"
        )

    def to_dict(self, include_details: bool = False) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "id": self.id,
            "original_question": self.original_question,
            "thinking_duration_minutes": self.thinking_duration_minutes,
            "model_id": self.model_id,
            "status": self.status,
            "progress": {
                "total_thoughts": self.total_thoughts,
                "total_questions": self.total_questions,
                "total_syntheses": self.total_syntheses,
                "current_focus": self.current_focus,
            },
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

        if include_details:
            result.update({
                "final_synthesis": self.final_synthesis,
                "confidence_evolution": self.confidence_evolution or [],
                "metadata": self.session_metadata or {},
                "error_message": self.error_message,
            })

        return result

    def get_elapsed_seconds(self) -> int:
        """Get total elapsed thinking time in seconds."""
        if not self.started_at:
            return 0

        end_time = self.completed_at or datetime.utcnow()
        return int((end_time - self.started_at).total_seconds())

    def get_progress_percentage(self) -> float:
        """Get progress as percentage of allocated time."""
        if not self.started_at:
            return 0.0

        elapsed = self.get_elapsed_seconds()
        total = self.thinking_duration_minutes * 60
        return min(100.0, (elapsed / total) * 100)


class Thought(Base):
    """
    Individual thought generated during a thinking session.

    Represents one unit in the AI's stream of consciousness as it
    explores the question over time.
    """

    __tablename__ = "thoughts"

    # Primary identifier
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the thought"
    )

    # Relationship
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("thinking_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The thinking session this thought belongs to"
    )

    # Sequencing
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Order in the thinking stream (0-indexed)"
    )

    # Content
    thought_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The actual thought content"
    )

    thought_type: Mapped[str] = mapped_column(
        Enum("exploration", "critique", "connection", "insight", "question", "synthesis", name="thought_type_enum"),
        nullable=False,
        default=ThoughtType.EXPLORATION.value,
        comment="Type of thought"
    )

    # Relationships
    related_to_question_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("sub_questions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Sub-question this thought addresses (if any)"
    )

    # Quality metrics
    confidence: Mapped[float] = mapped_column(
        Float,
        default=0.5,
        comment="Confidence level in this thought (0.0-1.0)"
    )

    importance: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Importance score (0.0-1.0)"
    )

    # Timing
    time_offset_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Seconds since thinking session started"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="When the thought was generated"
    )

    def __repr__(self) -> str:
        """String representation of the thought."""
        return (
            f"<Thought(id='{self.id}', "
            f"sequence={self.sequence_number}, "
            f"type='{self.thought_type}')>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "sequence_number": self.sequence_number,
            "thought_text": self.thought_text,
            "thought_type": self.thought_type,
            "confidence": self.confidence,
            "importance": self.importance,
            "time_offset_seconds": self.time_offset_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SubQuestion(Base):
    """
    Questions that the AI generates during thinking.

    As the AI thinks, it discovers new questions that need exploration.
    These are tracked and prioritized for future thinking.
    """

    __tablename__ = "sub_questions"

    # Primary identifier
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the sub-question"
    )

    # Relationship
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("thinking_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The thinking session that generated this question"
    )

    # Question content
    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The sub-question text"
    )

    # Prioritization
    priority: Mapped[int] = mapped_column(
        Integer,
        default=5,
        comment="Priority/importance (1-10, higher = more important)"
    )

    # Exploration status
    explored: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Has this question been explored yet?"
    )

    insights_gained: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="What was learned from exploring this question"
    )

    # Timestamps
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="When the question was generated"
    )

    explored_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the question was explored"
    )

    def __repr__(self) -> str:
        """String representation of the sub-question."""
        return (
            f"<SubQuestion(id='{self.id}', "
            f"priority={self.priority}, "
            f"explored={self.explored})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "question_text": self.question_text,
            "priority": self.priority,
            "explored": self.explored,
            "insights_gained": self.insights_gained,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "explored_at": self.explored_at.isoformat() if self.explored_at else None,
        }

    def mark_explored(self, insights: Optional[str] = None) -> None:
        """Mark this question as explored."""
        self.explored = True
        self.explored_at = datetime.utcnow()
        if insights:
            self.insights_gained = insights


class ThinkingSynthesis(Base):
    """
    Periodic summaries of the AI's current understanding.

    Every few minutes during thinking, the AI synthesizes what it has
    learned so far. This tracks the evolution of understanding over time.
    """

    __tablename__ = "thinking_syntheses"

    # Primary identifier
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the synthesis"
    )

    # Relationship
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("thinking_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The thinking session this synthesis belongs to"
    )

    # Sequencing
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Order in synthesis sequence (0-indexed)"
    )

    # Synthesis content
    synthesis_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Current understanding summary"
    )

    key_insights: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="Key insights at this point"
    )

    # Quality metrics
    confidence_level: Mapped[float] = mapped_column(
        Float,
        default=0.5,
        comment="Overall confidence in current understanding (0.0-1.0)"
    )

    remaining_questions: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="Questions that remain unclear"
    )

    # Timing
    time_offset_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Seconds since thinking session started"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="When the synthesis was created"
    )

    def __repr__(self) -> str:
        """String representation of the synthesis."""
        return (
            f"<ThinkingSynthesis(id='{self.id}', "
            f"sequence={self.sequence_number}, "
            f"confidence={self.confidence_level:.2f})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "sequence_number": self.sequence_number,
            "synthesis_text": self.synthesis_text,
            "key_insights": self.key_insights or [],
            "confidence_level": self.confidence_level,
            "remaining_questions": self.remaining_questions or [],
            "time_offset_seconds": self.time_offset_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
