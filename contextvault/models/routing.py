"""SQLAlchemy models for multi-model routing and capabilities."""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum as PyEnum

from sqlalchemy import JSON, DateTime, String, Text, func, Integer, Float, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ModelCapabilityType(str, PyEnum):
    """Types of model capabilities."""
    LOGICAL = "logical"           # Reasoning, analysis, problem-solving
    CREATIVE = "creative"         # Creative writing, brainstorming
    FACTUAL = "factual"           # Knowledge retrieval, facts
    CONVERSATIONAL = "conversational"  # Natural conversation
    CODE = "code"                 # Code generation and understanding
    MATHEMATICAL = "mathematical"  # Math and calculations
    MULTIMODAL = "multimodal"     # Image/audio processing


class RoutingStrategy(str, PyEnum):
    """Routing strategy types."""
    ROUND_ROBIN = "round_robin"
    CAPABILITY_BASED = "capability_based"
    PERFORMANCE_BASED = "performance_based"
    LOAD_BALANCED = "load_balanced"
    SPECIALIZED = "specialized"


class ModelCapabilityProfile(Base):
    """
    Model for tracking AI model capabilities and performance.

    Stores information about what each model is good at,
    performance metrics, and routing preferences.
    """

    __tablename__ = "model_capability_profiles"

    # Primary identifier
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the capability profile"
    )

    # Model identification
    model_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique identifier for the AI model (e.g., 'mistral:latest')"
    )

    model_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Human-readable name for the model"
    )

    # Capabilities
    capabilities: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="List of capability types this model excels at"
    )

    # Performance metrics
    average_latency_ms: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=0.0,
        comment="Average response latency in milliseconds"
    )

    average_tokens_per_second: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=0.0,
        comment="Average tokens generated per second"
    )

    success_rate: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        comment="Success rate (0.0 to 1.0)"
    )

    total_requests: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Total number of requests processed"
    )

    failed_requests: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of failed requests"
    )

    # Quality metrics
    average_quality_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Average quality score from evaluations (0.0 to 1.0)"
    )

    # Capability scores (0.0 to 1.0 for each capability)
    capability_scores: Mapped[Optional[Dict[str, float]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Scores for each capability type"
    )

    # Resource requirements
    estimated_memory_mb: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Estimated memory requirement in MB"
    )

    requires_gpu: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether this model requires GPU"
    )

    max_concurrent_requests: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Maximum concurrent requests this model can handle"
    )

    # Token window configuration
    max_context_window_tokens: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=8192,
        comment="Maximum context window size in tokens (e.g., 128000 for Llama 3.1)"
    )

    max_output_tokens: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=2048,
        comment="Maximum tokens that can be generated in output"
    )

    context_window_buffer: Mapped[int] = mapped_column(
        Integer,
        default=512,
        comment="Safety buffer to reserve in context window (tokens)"
    )

    tokenizer_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        default="llama",
        comment="Tokenizer type: llama, mistral, gpt, gemma"
    )

    # Configuration
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="1",
        comment="Whether this model is active and available for routing"
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Priority level for routing (higher = preferred)"
    )

    routing_weight: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        comment="Weight for load-balanced routing"
    )

    # Metadata
    model_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: {},
        comment="Additional model metadata"
    )

    tags: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        comment="Tags for categorization"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="When the profile was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="When the profile was last updated"
    )

    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the model was last used"
    )

    def __repr__(self) -> str:
        """String representation of the capability profile."""
        return (
            f"<ModelCapabilityProfile(id='{self.id}', "
            f"model_id='{self.model_id}', "
            f"capabilities={self.capabilities})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "model_id": self.model_id,
            "model_name": self.model_name,
            "capabilities": self.capabilities,
            "capability_scores": self.capability_scores or {},
            "performance": {
                "average_latency_ms": self.average_latency_ms,
                "average_tokens_per_second": self.average_tokens_per_second,
                "success_rate": self.success_rate,
                "total_requests": self.total_requests,
                "failed_requests": self.failed_requests,
                "average_quality_score": self.average_quality_score,
            },
            "resources": {
                "estimated_memory_mb": self.estimated_memory_mb,
                "requires_gpu": self.requires_gpu,
                "max_concurrent_requests": self.max_concurrent_requests,
            },
            "configuration": {
                "is_active": self.is_active,
                "priority": self.priority,
                "routing_weight": self.routing_weight,
            },
            "metadata": self.model_metadata or {},
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }

    def has_capability(self, capability: str) -> bool:
        """Check if model has a specific capability."""
        return capability in self.capabilities

    def get_capability_score(self, capability: str) -> float:
        """Get score for a specific capability (0.0 if not present)."""
        if not self.capability_scores:
            return 0.0
        return self.capability_scores.get(capability, 0.0)

    def update_performance_metrics(
        self,
        latency_ms: float,
        tokens_per_second: Optional[float] = None,
        success: bool = True,
        quality_score: Optional[float] = None
    ) -> None:
        """Update performance metrics with new data point."""
        # Update request counts
        self.total_requests += 1
        if not success:
            self.failed_requests += 1

        # Update success rate
        self.success_rate = (self.total_requests - self.failed_requests) / self.total_requests

        # Update average latency (exponential moving average)
        alpha = 0.1  # Smoothing factor
        if self.average_latency_ms is None or self.average_latency_ms == 0:
            self.average_latency_ms = latency_ms
        else:
            self.average_latency_ms = alpha * latency_ms + (1 - alpha) * self.average_latency_ms

        # Update tokens per second if provided
        if tokens_per_second is not None:
            if self.average_tokens_per_second is None or self.average_tokens_per_second == 0:
                self.average_tokens_per_second = tokens_per_second
            else:
                self.average_tokens_per_second = alpha * tokens_per_second + (1 - alpha) * self.average_tokens_per_second

        # Update quality score if provided
        if quality_score is not None:
            if self.average_quality_score is None:
                self.average_quality_score = quality_score
            else:
                self.average_quality_score = alpha * quality_score + (1 - alpha) * self.average_quality_score

        # Update last used timestamp
        self.last_used_at = datetime.utcnow()

    def is_capable_for_task(self, required_capabilities: List[str], min_score: float = 0.5) -> bool:
        """Check if model is capable for a task requiring specific capabilities."""
        # Default is_active to True if not set (for in-memory objects)
        if self.is_active is False:  # Explicitly check for False, not None
            return False

        for capability in required_capabilities:
            if capability not in self.capabilities:
                return False

            score = self.get_capability_score(capability)
            if score < min_score:
                return False

        return True

    def get_routing_score(self, required_capabilities: List[str]) -> float:
        """
        Calculate routing score for this model given required capabilities.

        Score is based on:
        - Capability match and scores
        - Performance metrics
        - Priority
        - Current load

        Returns:
            Float score (higher is better), 0.0 if not suitable
        """
        # Default is_active to True if not set (for in-memory objects)
        if self.is_active is False:  # Explicitly check for False, not None
            return 0.0

        # Check if model has required capabilities
        if not all(cap in self.capabilities for cap in required_capabilities):
            return 0.0

        # Calculate capability score (average of required capabilities)
        capability_score = 0.0
        if required_capabilities:
            scores = [self.get_capability_score(cap) for cap in required_capabilities]
            capability_score = sum(scores) / len(scores)
        else:
            # If no specific capabilities required, use overall success rate
            capability_score = self.success_rate if self.success_rate is not None else 1.0

        # Factor in performance (inverse of latency, normalized)
        if self.average_latency_ms and self.average_latency_ms > 0:
            # Normalize latency (assume 1000ms is baseline)
            latency_score = min(1.0, 1000.0 / self.average_latency_ms)
        else:
            latency_score = 0.5

        # Factor in quality (default to 0.5 if not set)
        quality_score = self.average_quality_score if self.average_quality_score is not None else 0.5

        # Factor in success rate (default to 1.0 if not set - assume success until proven otherwise)
        success_score = self.success_rate if self.success_rate is not None else 1.0

        # Factor in priority (normalized to 0-1 range, assuming max priority of 10)
        priority_score = min(1.0, (self.priority if self.priority is not None else 0) / 10.0)

        # Factor in routing weight (default to 1.0 if not set)
        routing_weight = self.routing_weight if self.routing_weight is not None else 1.0

        # Weighted combination
        final_score = (
            capability_score * 0.35 +
            quality_score * 0.25 +
            success_score * 0.20 +
            latency_score * 0.10 +
            priority_score * 0.10
        ) * routing_weight

        return final_score

    def get_available_context_tokens(self, prompt_tokens: int = 0) -> int:
        """
        Calculate available tokens for context injection.

        Args:
            prompt_tokens: Number of tokens in user's prompt

        Returns:
            Number of tokens available for context
        """
        if not self.max_context_window_tokens:
            return 8192  # Default fallback

        # Total window - output reserve - buffer - prompt
        output_reserve = self.max_output_tokens or 2048
        buffer = self.context_window_buffer or 512

        available = self.max_context_window_tokens - output_reserve - buffer - prompt_tokens

        return max(0, available)  # Never negative

    def supports_large_context(self) -> bool:
        """Check if model supports large context windows (>32K tokens)."""
        return (self.max_context_window_tokens or 0) >= 32000

    def get_tokenizer_info(self) -> Dict[str, Any]:
        """Get tokenizer configuration info."""
        return {
            "type": self.tokenizer_type or "llama",
            "max_context_window": self.max_context_window_tokens or 8192,
            "max_output": self.max_output_tokens or 2048,
            "buffer": self.context_window_buffer or 512,
        }


class RoutingDecision(Base):
    """
    Model for tracking routing decisions and their outcomes.

    Stores information about why a particular model was chosen
    for a request and how well it performed.
    """

    __tablename__ = "routing_decisions"

    # Primary identifier
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Unique identifier for the routing decision"
    )

    # Request information
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="Associated session ID"
    )

    request_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Original request text (for analysis)"
    )

    detected_capabilities: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="Capabilities detected in the request"
    )

    # Routing details
    chosen_model_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Model that was chosen for this request"
    )

    routing_strategy: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="capability_based",
        comment="Strategy used for routing"
    )

    routing_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Routing score that led to this decision"
    )

    alternative_models: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        comment="Alternative models that were considered"
    )

    # Outcome metrics
    latency_ms: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Actual latency for this request"
    )

    tokens_generated: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of tokens generated"
    )

    success: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether the request was successful"
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if request failed"
    )

    quality_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Quality score for the response (if evaluated)"
    )

    # Metadata
    routing_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: {},
        comment="Additional routing metadata"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="When the routing decision was made"
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the request completed"
    )

    def __repr__(self) -> str:
        """String representation of the routing decision."""
        return (
            f"<RoutingDecision(id='{self.id}', "
            f"model='{self.chosen_model_id}', "
            f"success={self.success})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "request_text": self.request_text[:100] + "..." if self.request_text and len(self.request_text) > 100 else self.request_text,
            "detected_capabilities": self.detected_capabilities,
            "chosen_model_id": self.chosen_model_id,
            "routing_strategy": self.routing_strategy,
            "routing_score": self.routing_score,
            "alternative_models": self.alternative_models or [],
            "performance": {
                "latency_ms": self.latency_ms,
                "tokens_generated": self.tokens_generated,
                "success": self.success,
                "error_message": self.error_message,
                "quality_score": self.quality_score,
            },
            "metadata": self.routing_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def complete(
        self,
        success: bool,
        latency_ms: float,
        tokens_generated: Optional[int] = None,
        error_message: Optional[str] = None,
        quality_score: Optional[float] = None
    ) -> None:
        """Mark routing decision as complete with outcome metrics."""
        self.success = success
        self.latency_ms = latency_ms
        self.tokens_generated = tokens_generated
        self.error_message = error_message
        self.quality_score = quality_score
        self.completed_at = datetime.utcnow()
