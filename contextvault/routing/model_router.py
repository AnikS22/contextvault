"""Core multi-model routing engine."""

import re
import logging
import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..database import get_db_context
from ..models import ModelCapabilityProfile, RoutingDecision, ModelCapabilityType, RoutingStrategy
from .model_profiles import ModelProfileService

logger = logging.getLogger(__name__)


class ModelRouter:
    """
    Core router for directing requests to appropriate AI models.

    Routes requests based on detected capabilities, model performance,
    and configured routing strategies.
    """

    def __init__(self, profile_service: Optional[ModelProfileService] = None):
        """Initialize the model router."""
        self.profile_service = profile_service or ModelProfileService()

        # Keyword patterns for capability detection
        self.capability_patterns = {
            ModelCapabilityType.LOGICAL: [
                r'\b(analyze|reason|logic|deduce|infer|prove|argue|calculate)\b',
                r'\b(because|therefore|thus|hence|consequently)\b',
                r'\b(if.*then|premise|conclusion|syllogism)\b',
                r'\b(problem|solve|solution|algorithm)\b',
            ],
            ModelCapabilityType.CREATIVE: [
                r'\b(create|imagine|design|invent|brainstorm|generate)\b',
                r'\b(story|poem|creative|original|novel|artistic)\b',
                r'\b(metaphor|analogy|imagery|narrative)\b',
                r'\b(what if|imagine if|pretend|roleplay)\b',
            ],
            ModelCapabilityType.FACTUAL: [
                r'\b(fact|information|data|statistic|research|study)\b',
                r'\b(what is|who is|when|where|define|explain)\b',
                r'\b(history|science|geography|biology|physics)\b',
                r'\b(according to|source|reference|citation)\b',
            ],
            ModelCapabilityType.CONVERSATIONAL: [
                r'\b(chat|talk|discuss|conversation|dialogue)\b',
                r'\b(how are you|hello|hi|thanks|please)\b',
                r'\b(opinion|feel|think|believe)\b',
                r'\b(friendly|casual|informal)\b',
            ],
            ModelCapabilityType.CODE: [
                r'\b(code|program|function|class|method|variable)\b',
                r'\b(python|javascript|java|c\+\+|rust|go)\b',
                r'\b(debug|bug|error|syntax|compile|execute)\b',
                r'\b(implement|write.*code|develop|build)\b',
                r'```[\s\S]*?```',  # Code blocks
            ],
            ModelCapabilityType.MATHEMATICAL: [
                r'\b(math|calculate|compute|equation|formula)\b',
                r'\b(add|subtract|multiply|divide|sum|average)\b',
                r'\b(algebra|calculus|geometry|statistics)\b',
                r'\d+\s*[+\-*/]\s*\d+',  # Math expressions
            ],
        }

        # Default routing strategy
        self.default_strategy = RoutingStrategy.CAPABILITY_BASED

    def detect_capabilities(self, text: str) -> List[str]:
        """
        Detect required capabilities from input text.

        Args:
            text: Input text to analyze

        Returns:
            List of detected capability types
        """
        if not text:
            return []

        text_lower = text.lower()
        detected = []

        for capability, patterns in self.capability_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    detected.append(capability.value)
                    break  # Move to next capability once found

        # Default to conversational if nothing else detected
        if not detected:
            detected.append(ModelCapabilityType.CONVERSATIONAL.value)

        logger.debug(f"Detected capabilities: {detected}")
        return detected

    def route_request(
        self,
        request_text: str,
        session_id: Optional[str] = None,
        strategy: Optional[str] = None,
        required_capabilities: Optional[List[str]] = None,
        exclude_models: Optional[List[str]] = None,
        prefer_models: Optional[List[str]] = None,
    ) -> Tuple[Optional[str], RoutingDecision]:
        """
        Route a request to the most appropriate model.

        Args:
            request_text: The request text to route
            session_id: Optional session ID for tracking
            strategy: Routing strategy to use
            required_capabilities: Explicitly required capabilities
            exclude_models: Models to exclude from routing
            prefer_models: Models to prefer (will be considered first)

        Returns:
            Tuple of (selected_model_id, routing_decision)

        Raises:
            RuntimeError: If no suitable model found
        """
        try:
            # Detect required capabilities
            if required_capabilities is None:
                required_capabilities = self.detect_capabilities(request_text)

            # Determine routing strategy
            if strategy is None:
                strategy = self.default_strategy.value

            # Create routing decision record
            routing_decision = RoutingDecision(
                session_id=session_id,
                request_text=request_text,
                detected_capabilities=required_capabilities,
                routing_strategy=strategy,
            )

            # Get candidate models based on strategy
            selected_model = None

            if strategy == RoutingStrategy.ROUND_ROBIN.value:
                selected_model = self._route_round_robin(
                    required_capabilities,
                    exclude_models,
                    prefer_models
                )

            elif strategy == RoutingStrategy.CAPABILITY_BASED.value:
                selected_model = self._route_capability_based(
                    required_capabilities,
                    exclude_models,
                    prefer_models
                )

            elif strategy == RoutingStrategy.PERFORMANCE_BASED.value:
                selected_model = self._route_performance_based(
                    required_capabilities,
                    exclude_models,
                    prefer_models
                )

            elif strategy == RoutingStrategy.LOAD_BALANCED.value:
                selected_model = self._route_load_balanced(
                    required_capabilities,
                    exclude_models,
                    prefer_models
                )

            elif strategy == RoutingStrategy.SPECIALIZED.value:
                selected_model = self._route_specialized(
                    required_capabilities,
                    exclude_models,
                    prefer_models
                )

            else:
                # Default to capability-based
                selected_model = self._route_capability_based(
                    required_capabilities,
                    exclude_models,
                    prefer_models
                )

            if selected_model is None:
                error_msg = f"No suitable model found for capabilities: {required_capabilities}"
                logger.error(error_msg)
                routing_decision.routing_score = 0.0
                routing_decision.error_message = error_msg
                raise RuntimeError(error_msg)

            # Update routing decision with selected model
            routing_decision.chosen_model_id = selected_model.model_id
            routing_decision.routing_score = selected_model.get_routing_score(required_capabilities)

            # Get alternative models for reference
            alternatives = self._get_alternative_models(
                required_capabilities,
                exclude_models=[selected_model.model_id] + (exclude_models or []),
                limit=3
            )
            routing_decision.alternative_models = [
                {
                    "model_id": alt.model_id,
                    "model_name": alt.model_name,
                    "score": alt.get_routing_score(required_capabilities)
                }
                for alt in alternatives
            ]

            # Save routing decision to database
            with get_db_context() as db:
                db.add(routing_decision)
                db.commit()
                db.refresh(routing_decision)

            logger.info(
                f"Routed request to {selected_model.model_id} "
                f"with score {routing_decision.routing_score:.2f} "
                f"using strategy {strategy}"
            )

            return selected_model.model_id, routing_decision

        except Exception as e:
            logger.error(f"Failed to route request: {str(e)}", exc_info=True)
            raise

    def _route_capability_based(
        self,
        required_capabilities: List[str],
        exclude_models: Optional[List[str]] = None,
        prefer_models: Optional[List[str]] = None
    ) -> Optional[ModelCapabilityProfile]:
        """Route based on capability match and scores."""
        # Check preferred models first
        if prefer_models:
            for model_id in prefer_models:
                profile = self.profile_service.get_profile(model_id)
                if profile and profile.is_active:
                    if profile.is_capable_for_task(required_capabilities):
                        return profile

        # Get best model for capabilities
        return self.profile_service.get_best_model_for_capabilities(
            required_capabilities=required_capabilities,
            exclude_models=exclude_models
        )

    def _route_performance_based(
        self,
        required_capabilities: List[str],
        exclude_models: Optional[List[str]] = None,
        prefer_models: Optional[List[str]] = None
    ) -> Optional[ModelCapabilityProfile]:
        """Route based on performance metrics (latency, success rate)."""
        # Get all capable models
        profiles = self.profile_service.list_profiles(active_only=True)

        if exclude_models:
            profiles = [p for p in profiles if p.model_id not in exclude_models]

        # Filter by capability
        capable_profiles = []
        for profile in profiles:
            if profile.is_capable_for_task(required_capabilities):
                # Calculate performance score (lower latency + higher success rate)
                latency_score = 1.0
                if profile.average_latency_ms and profile.average_latency_ms > 0:
                    latency_score = min(1.0, 1000.0 / profile.average_latency_ms)

                performance_score = (latency_score * 0.5 + profile.success_rate * 0.5)
                capable_profiles.append((profile, performance_score))

        if not capable_profiles:
            return None

        # Sort by performance score
        capable_profiles.sort(key=lambda x: x[1], reverse=True)

        return capable_profiles[0][0]

    def _route_round_robin(
        self,
        required_capabilities: List[str],
        exclude_models: Optional[List[str]] = None,
        prefer_models: Optional[List[str]] = None
    ) -> Optional[ModelCapabilityProfile]:
        """Route using round-robin among capable models."""
        profiles = self.profile_service.list_profiles(active_only=True)

        if exclude_models:
            profiles = [p for p in profiles if p.model_id not in exclude_models]

        # Filter by capability
        capable_profiles = [p for p in profiles if p.is_capable_for_task(required_capabilities)]

        if not capable_profiles:
            return None

        # Sort by last_used_at (ascending, so least recently used first)
        capable_profiles.sort(
            key=lambda p: p.last_used_at if p.last_used_at else datetime.min
        )

        return capable_profiles[0]

    def _route_load_balanced(
        self,
        required_capabilities: List[str],
        exclude_models: Optional[List[str]] = None,
        prefer_models: Optional[List[str]] = None
    ) -> Optional[ModelCapabilityProfile]:
        """Route based on current load and routing weights."""
        profiles = self.profile_service.list_profiles(active_only=True)

        if exclude_models:
            profiles = [p for p in profiles if p.model_id not in exclude_models]

        # Filter by capability
        capable_profiles = [p for p in profiles if p.is_capable_for_task(required_capabilities)]

        if not capable_profiles:
            return None

        # Calculate weighted random selection based on routing weights
        # (Models with higher weights are more likely to be selected)
        total_weight = sum(p.routing_weight for p in capable_profiles)

        if total_weight == 0:
            # Fall back to random if all weights are 0
            return random.choice(capable_profiles)

        # Weighted random selection
        rand = random.uniform(0, total_weight)
        cumulative = 0

        for profile in capable_profiles:
            cumulative += profile.routing_weight
            if rand <= cumulative:
                return profile

        # Fallback (shouldn't reach here)
        return capable_profiles[0]

    def _route_specialized(
        self,
        required_capabilities: List[str],
        exclude_models: Optional[List[str]] = None,
        prefer_models: Optional[List[str]] = None
    ) -> Optional[ModelCapabilityProfile]:
        """
        Route to most specialized model (highest capability score for required capabilities).

        Prioritizes depth over breadth - prefers models that are highly specialized
        in the required capabilities even if they have fewer overall capabilities.
        """
        profiles = self.profile_service.list_profiles(active_only=True)

        if exclude_models:
            profiles = [p for p in profiles if p.model_id not in exclude_models]

        # Filter by capability and calculate specialization score
        specialized_profiles = []
        for profile in profiles:
            if profile.is_capable_for_task(required_capabilities):
                # Specialization score = average of capability scores + penalty for extra capabilities
                capability_scores = [
                    profile.get_capability_score(cap)
                    for cap in required_capabilities
                ]
                avg_score = sum(capability_scores) / len(capability_scores) if capability_scores else 0

                # Penalty for having many other capabilities (less specialized)
                extra_capabilities = len(profile.capabilities) - len(required_capabilities)
                specialization_penalty = max(0, extra_capabilities * 0.05)

                specialization_score = max(0, avg_score - specialization_penalty)

                specialized_profiles.append((profile, specialization_score))

        if not specialized_profiles:
            return None

        # Sort by specialization score
        specialized_profiles.sort(key=lambda x: x[1], reverse=True)

        return specialized_profiles[0][0]

    def _get_alternative_models(
        self,
        required_capabilities: List[str],
        exclude_models: Optional[List[str]] = None,
        limit: int = 3
    ) -> List[ModelCapabilityProfile]:
        """Get alternative models for the given capabilities."""
        profiles = self.profile_service.list_profiles(active_only=True)

        if exclude_models:
            profiles = [p for p in profiles if p.model_id not in exclude_models]

        # Filter and score
        scored_profiles = []
        for profile in profiles:
            if profile.is_capable_for_task(required_capabilities):
                score = profile.get_routing_score(required_capabilities)
                scored_profiles.append((profile, score))

        # Sort by score
        scored_profiles.sort(key=lambda x: x[1], reverse=True)

        # Return top N alternatives
        return [p[0] for p in scored_profiles[:limit]]

    def complete_routing_decision(
        self,
        decision_id: str,
        success: bool,
        latency_ms: float,
        tokens_generated: Optional[int] = None,
        error_message: Optional[str] = None,
        quality_score: Optional[float] = None
    ) -> bool:
        """
        Complete a routing decision with outcome metrics.

        Args:
            decision_id: Routing decision ID
            success: Whether the request succeeded
            latency_ms: Request latency in milliseconds
            tokens_generated: Number of tokens generated
            error_message: Error message if failed
            quality_score: Quality score (0.0 to 1.0)

        Returns:
            True if updated successfully
        """
        try:
            with get_db_context() as db:
                decision = db.query(RoutingDecision).filter(
                    RoutingDecision.id == decision_id
                ).first()

                if not decision:
                    logger.warning(f"Routing decision {decision_id} not found")
                    return False

                # Update decision
                decision.complete(
                    success=success,
                    latency_ms=latency_ms,
                    tokens_generated=tokens_generated,
                    error_message=error_message,
                    quality_score=quality_score
                )

                db.commit()

                # Update model performance metrics
                if decision.chosen_model_id:
                    tokens_per_second = None
                    if tokens_generated and latency_ms > 0:
                        tokens_per_second = (tokens_generated / latency_ms) * 1000

                    self.profile_service.update_performance(
                        model_id=decision.chosen_model_id,
                        latency_ms=latency_ms,
                        tokens_per_second=tokens_per_second,
                        success=success,
                        quality_score=quality_score
                    )

                logger.debug(f"Completed routing decision {decision_id}")

                return True

        except Exception as e:
            logger.error(f"Failed to complete routing decision: {str(e)}", exc_info=True)
            return False

    def get_routing_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get routing statistics for the specified period.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with routing statistics
        """
        try:
            with get_db_context() as db:
                from datetime import timedelta

                since = datetime.utcnow() - timedelta(days=days)

                # Get all decisions in period
                decisions = db.query(RoutingDecision).filter(
                    RoutingDecision.created_at >= since
                ).all()

                total_decisions = len(decisions)
                successful_decisions = sum(1 for d in decisions if d.success)

                # Group by model
                by_model: Dict[str, Dict[str, Any]] = {}
                for decision in decisions:
                    model_id = decision.chosen_model_id
                    if model_id not in by_model:
                        by_model[model_id] = {
                            "requests": 0,
                            "successes": 0,
                            "failures": 0,
                            "total_latency": 0.0,
                            "latencies": [],
                        }

                    by_model[model_id]["requests"] += 1
                    if decision.success:
                        by_model[model_id]["successes"] += 1
                    else:
                        by_model[model_id]["failures"] += 1

                    if decision.latency_ms:
                        by_model[model_id]["latencies"].append(decision.latency_ms)

                # Calculate averages
                model_stats = {}
                for model_id, stats in by_model.items():
                    latencies = stats["latencies"]
                    model_stats[model_id] = {
                        "total_requests": stats["requests"],
                        "successful_requests": stats["successes"],
                        "failed_requests": stats["failures"],
                        "success_rate": stats["successes"] / stats["requests"] if stats["requests"] > 0 else 0.0,
                        "average_latency_ms": sum(latencies) / len(latencies) if latencies else None,
                        "min_latency_ms": min(latencies) if latencies else None,
                        "max_latency_ms": max(latencies) if latencies else None,
                    }

                # Group by capability
                by_capability: Dict[str, int] = {}
                for decision in decisions:
                    for capability in decision.detected_capabilities:
                        by_capability[capability] = by_capability.get(capability, 0) + 1

                # Group by strategy
                by_strategy: Dict[str, int] = {}
                for decision in decisions:
                    strategy = decision.routing_strategy
                    by_strategy[strategy] = by_strategy.get(strategy, 0) + 1

                return {
                    "period_days": days,
                    "total_decisions": total_decisions,
                    "successful_decisions": successful_decisions,
                    "failed_decisions": total_decisions - successful_decisions,
                    "overall_success_rate": successful_decisions / total_decisions if total_decisions > 0 else 0.0,
                    "by_model": model_stats,
                    "by_capability": by_capability,
                    "by_strategy": by_strategy,
                }

        except Exception as e:
            logger.error(f"Failed to get routing stats: {str(e)}", exc_info=True)
            return {"error": str(e)}


# Global router instance
model_router = ModelRouter()
