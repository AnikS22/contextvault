"""Model capability profile management service."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..database import get_db_context
from ..models import ModelCapabilityProfile, ModelCapabilityType, RoutingDecision

logger = logging.getLogger(__name__)


class ModelProfileService:
    """Service for managing model capability profiles."""

    def __init__(self, db_session: Optional[Session] = None):
        """Initialize the model profile service."""
        self.db_session = db_session

    def _get_session(self) -> Session:
        """Get database session."""
        if self.db_session:
            return self.db_session
        return next(get_db_context())

    def register_model(
        self,
        model_id: str,
        model_name: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        capability_scores: Optional[Dict[str, float]] = None,
        estimated_memory_mb: Optional[int] = None,
        requires_gpu: bool = False,
        max_concurrent_requests: int = 1,
        priority: int = 0,
        tags: Optional[List[str]] = None,
    ) -> ModelCapabilityProfile:
        """
        Register a new model or update existing profile.

        Args:
            model_id: Unique model identifier
            model_name: Human-readable model name
            capabilities: List of capability types
            capability_scores: Scores for each capability (0.0 to 1.0)
            estimated_memory_mb: Memory requirement in MB
            requires_gpu: Whether GPU is required
            max_concurrent_requests: Max concurrent requests
            priority: Priority level for routing
            tags: Tags for categorization

        Returns:
            ModelCapabilityProfile: Created or updated profile

        Raises:
            ValueError: If model_id is invalid
            RuntimeError: If database operation fails
        """
        if not model_id or not model_id.strip():
            raise ValueError("model_id cannot be empty")

        capabilities = capabilities or []
        capability_scores = capability_scores or {}
        tags = tags or []

        try:
            with get_db_context() as db:
                # Check if profile already exists
                profile = db.query(ModelCapabilityProfile).filter(
                    ModelCapabilityProfile.model_id == model_id
                ).first()

                if profile:
                    # Update existing profile
                    if model_name:
                        profile.model_name = model_name
                    if capabilities:
                        profile.capabilities = capabilities
                    if capability_scores:
                        profile.capability_scores = capability_scores
                    if estimated_memory_mb is not None:
                        profile.estimated_memory_mb = estimated_memory_mb
                    if requires_gpu is not None:
                        profile.requires_gpu = requires_gpu
                    if max_concurrent_requests is not None:
                        profile.max_concurrent_requests = max_concurrent_requests
                    if priority is not None:
                        profile.priority = priority
                    if tags:
                        profile.tags = tags

                    profile.updated_at = datetime.utcnow()

                    logger.info(f"Updated model profile: {model_id}")
                else:
                    # Create new profile
                    profile = ModelCapabilityProfile(
                        model_id=model_id,
                        model_name=model_name or model_id,
                        capabilities=capabilities,
                        capability_scores=capability_scores,
                        estimated_memory_mb=estimated_memory_mb,
                        requires_gpu=requires_gpu,
                        max_concurrent_requests=max_concurrent_requests,
                        priority=priority,
                        tags=tags,
                    )

                    db.add(profile)
                    logger.info(f"Registered new model profile: {model_id}")

                db.commit()
                db.refresh(profile)

                return profile

        except Exception as e:
            logger.error(f"Failed to register model {model_id}: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to register model: {str(e)}")

    def get_profile(self, model_id: str) -> Optional[ModelCapabilityProfile]:
        """
        Get model capability profile by ID.

        Args:
            model_id: Model identifier

        Returns:
            ModelCapabilityProfile if found, None otherwise
        """
        try:
            db = self._get_session()
            profile = db.query(ModelCapabilityProfile).filter(
                ModelCapabilityProfile.model_id == model_id
            ).first()

            return profile

        except Exception as e:
            logger.error(f"Failed to get profile for {model_id}: {str(e)}", exc_info=True)
            return None

    def list_profiles(
        self,
        active_only: bool = True,
        has_capability: Optional[str] = None,
        requires_gpu: Optional[bool] = None,
        min_priority: Optional[int] = None,
    ) -> List[ModelCapabilityProfile]:
        """
        List model capability profiles with optional filtering.

        Args:
            active_only: Only return active profiles
            has_capability: Filter by capability type
            requires_gpu: Filter by GPU requirement
            min_priority: Minimum priority level

        Returns:
            List of matching profiles
        """
        try:
            db = self._get_session()
            query = db.query(ModelCapabilityProfile)

            if active_only:
                query = query.filter(ModelCapabilityProfile.is_active == True)

            if has_capability:
                query = query.filter(
                    ModelCapabilityProfile.capabilities.contains([has_capability])
                )

            if requires_gpu is not None:
                query = query.filter(ModelCapabilityProfile.requires_gpu == requires_gpu)

            if min_priority is not None:
                query = query.filter(ModelCapabilityProfile.priority >= min_priority)

            # Order by priority (descending) and then by success rate
            query = query.order_by(
                desc(ModelCapabilityProfile.priority),
                desc(ModelCapabilityProfile.success_rate)
            )

            profiles = query.all()

            return profiles

        except Exception as e:
            logger.error(f"Failed to list profiles: {str(e)}", exc_info=True)
            return []

    def update_performance(
        self,
        model_id: str,
        latency_ms: float,
        tokens_per_second: Optional[float] = None,
        success: bool = True,
        quality_score: Optional[float] = None
    ) -> bool:
        """
        Update performance metrics for a model.

        Args:
            model_id: Model identifier
            latency_ms: Response latency in milliseconds
            tokens_per_second: Tokens generated per second
            success: Whether the request was successful
            quality_score: Quality score (0.0 to 1.0)

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            with get_db_context() as db:
                profile = db.query(ModelCapabilityProfile).filter(
                    ModelCapabilityProfile.model_id == model_id
                ).first()

                if not profile:
                    logger.warning(f"Profile not found for model {model_id}")
                    return False

                profile.update_performance_metrics(
                    latency_ms=latency_ms,
                    tokens_per_second=tokens_per_second,
                    success=success,
                    quality_score=quality_score
                )

                db.commit()

                logger.debug(
                    f"Updated performance for {model_id}: "
                    f"latency={latency_ms}ms, success={success}"
                )

                return True

        except Exception as e:
            logger.error(f"Failed to update performance for {model_id}: {str(e)}", exc_info=True)
            return False

    def update_capability_score(
        self,
        model_id: str,
        capability: str,
        score: float
    ) -> bool:
        """
        Update capability score for a model.

        Args:
            model_id: Model identifier
            capability: Capability type
            score: New score (0.0 to 1.0)

        Returns:
            True if updated successfully, False otherwise
        """
        if score < 0.0 or score > 1.0:
            raise ValueError("Score must be between 0.0 and 1.0")

        try:
            with get_db_context() as db:
                profile = db.query(ModelCapabilityProfile).filter(
                    ModelCapabilityProfile.model_id == model_id
                ).first()

                if not profile:
                    logger.warning(f"Profile not found for model {model_id}")
                    return False

                if not profile.capability_scores:
                    profile.capability_scores = {}

                profile.capability_scores[capability] = score
                profile.updated_at = datetime.utcnow()

                db.commit()

                logger.info(f"Updated capability score for {model_id}.{capability} = {score}")

                return True

        except Exception as e:
            logger.error(
                f"Failed to update capability score for {model_id}: {str(e)}",
                exc_info=True
            )
            return False

    def get_best_model_for_capabilities(
        self,
        required_capabilities: List[str],
        min_score: float = 0.5,
        exclude_models: Optional[List[str]] = None
    ) -> Optional[ModelCapabilityProfile]:
        """
        Get the best model for given required capabilities.

        Args:
            required_capabilities: List of required capabilities
            min_score: Minimum capability score threshold
            exclude_models: List of model IDs to exclude

        Returns:
            Best matching ModelCapabilityProfile or None if no suitable model
        """
        exclude_models = exclude_models or []

        try:
            profiles = self.list_profiles(active_only=True)

            # Filter out excluded models
            profiles = [p for p in profiles if p.model_id not in exclude_models]

            # Filter by capability and score
            suitable_profiles = []
            for profile in profiles:
                if profile.is_capable_for_task(required_capabilities, min_score):
                    score = profile.get_routing_score(required_capabilities)
                    suitable_profiles.append((profile, score))

            if not suitable_profiles:
                logger.warning(
                    f"No suitable model found for capabilities: {required_capabilities}"
                )
                return None

            # Sort by routing score (highest first)
            suitable_profiles.sort(key=lambda x: x[1], reverse=True)

            best_profile = suitable_profiles[0][0]

            logger.info(
                f"Selected model {best_profile.model_id} "
                f"for capabilities {required_capabilities} "
                f"with score {suitable_profiles[0][1]:.2f}"
            )

            return best_profile

        except Exception as e:
            logger.error(
                f"Failed to get best model for capabilities: {str(e)}",
                exc_info=True
            )
            return None

    def deactivate_model(self, model_id: str) -> bool:
        """
        Deactivate a model (make it unavailable for routing).

        Args:
            model_id: Model identifier

        Returns:
            True if deactivated successfully, False otherwise
        """
        try:
            with get_db_context() as db:
                profile = db.query(ModelCapabilityProfile).filter(
                    ModelCapabilityProfile.model_id == model_id
                ).first()

                if not profile:
                    logger.warning(f"Profile not found for model {model_id}")
                    return False

                profile.is_active = False
                profile.updated_at = datetime.utcnow()

                db.commit()

                logger.info(f"Deactivated model {model_id}")

                return True

        except Exception as e:
            logger.error(f"Failed to deactivate model {model_id}: {str(e)}", exc_info=True)
            return False

    def activate_model(self, model_id: str) -> bool:
        """
        Activate a model (make it available for routing).

        Args:
            model_id: Model identifier

        Returns:
            True if activated successfully, False otherwise
        """
        try:
            with get_db_context() as db:
                profile = db.query(ModelCapabilityProfile).filter(
                    ModelCapabilityProfile.model_id == model_id
                ).first()

                if not profile:
                    logger.warning(f"Profile not found for model {model_id}")
                    return False

                profile.is_active = True
                profile.updated_at = datetime.utcnow()

                db.commit()

                logger.info(f"Activated model {model_id}")

                return True

        except Exception as e:
            logger.error(f"Failed to activate model {model_id}: {str(e)}", exc_info=True)
            return False

    def get_performance_stats(self, model_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Get performance statistics for a model over a time period.

        Args:
            model_id: Model identifier
            days: Number of days to analyze

        Returns:
            Dictionary with performance statistics
        """
        try:
            with get_db_context() as db:
                profile = db.query(ModelCapabilityProfile).filter(
                    ModelCapabilityProfile.model_id == model_id
                ).first()

                if not profile:
                    return {"error": f"Profile not found for model {model_id}"}

                # Get routing decisions for this model in the time period
                since = datetime.utcnow() - timedelta(days=days)
                decisions = db.query(RoutingDecision).filter(
                    RoutingDecision.chosen_model_id == model_id,
                    RoutingDecision.created_at >= since
                ).all()

                # Calculate statistics
                total_requests = len(decisions)
                successful_requests = sum(1 for d in decisions if d.success)
                failed_requests = total_requests - successful_requests

                latencies = [d.latency_ms for d in decisions if d.latency_ms is not None]
                avg_latency = sum(latencies) / len(latencies) if latencies else None
                min_latency = min(latencies) if latencies else None
                max_latency = max(latencies) if latencies else None

                quality_scores = [d.quality_score for d in decisions if d.quality_score is not None]
                avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None

                return {
                    "model_id": model_id,
                    "model_name": profile.model_name,
                    "period_days": days,
                    "total_requests": total_requests,
                    "successful_requests": successful_requests,
                    "failed_requests": failed_requests,
                    "success_rate": successful_requests / total_requests if total_requests > 0 else 0.0,
                    "latency": {
                        "average_ms": avg_latency,
                        "min_ms": min_latency,
                        "max_ms": max_latency,
                    },
                    "quality": {
                        "average_score": avg_quality,
                    },
                    "overall_metrics": {
                        "average_latency_ms": profile.average_latency_ms,
                        "average_tokens_per_second": profile.average_tokens_per_second,
                        "total_lifetime_requests": profile.total_requests,
                        "lifetime_success_rate": profile.success_rate,
                        "average_quality_score": profile.average_quality_score,
                    }
                }

        except Exception as e:
            logger.error(
                f"Failed to get performance stats for {model_id}: {str(e)}",
                exc_info=True
            )
            return {"error": str(e)}

    def auto_tune_capability_scores(self, model_id: str, days: int = 30) -> bool:
        """
        Automatically tune capability scores based on recent performance.

        Analyzes routing decisions and outcomes to adjust capability scores.

        Args:
            model_id: Model identifier
            days: Number of days to analyze

        Returns:
            True if tuning was successful, False otherwise
        """
        try:
            with get_db_context() as db:
                profile = db.query(ModelCapabilityProfile).filter(
                    ModelCapabilityProfile.model_id == model_id
                ).first()

                if not profile:
                    logger.warning(f"Profile not found for model {model_id}")
                    return False

                # Get routing decisions for this model in the time period
                since = datetime.utcnow() - timedelta(days=days)
                decisions = db.query(RoutingDecision).filter(
                    RoutingDecision.chosen_model_id == model_id,
                    RoutingDecision.created_at >= since,
                    RoutingDecision.success == True
                ).all()

                if not decisions:
                    logger.info(f"No decisions found for {model_id} in the last {days} days")
                    return False

                # Analyze capability performance
                capability_performance: Dict[str, List[float]] = {}

                for decision in decisions:
                    for capability in decision.detected_capabilities:
                        if capability not in capability_performance:
                            capability_performance[capability] = []

                        # Use quality score if available, otherwise use success as 1.0
                        score = decision.quality_score if decision.quality_score is not None else 1.0
                        capability_performance[capability].append(score)

                # Update capability scores (weighted average with existing scores)
                if not profile.capability_scores:
                    profile.capability_scores = {}

                for capability, scores in capability_performance.items():
                    avg_score = sum(scores) / len(scores)

                    # If capability already has a score, blend it with new data
                    if capability in profile.capability_scores:
                        existing_score = profile.capability_scores[capability]
                        # 70% new data, 30% existing
                        blended_score = 0.7 * avg_score + 0.3 * existing_score
                        profile.capability_scores[capability] = blended_score
                    else:
                        profile.capability_scores[capability] = avg_score

                    logger.info(
                        f"Auto-tuned {model_id}.{capability} = {profile.capability_scores[capability]:.2f} "
                        f"(based on {len(scores)} samples)"
                    )

                profile.updated_at = datetime.utcnow()
                db.commit()

                return True

        except Exception as e:
            logger.error(
                f"Failed to auto-tune capability scores for {model_id}: {str(e)}",
                exc_info=True
            )
            return False


# Global service instance
model_profile_service = ModelProfileService()
