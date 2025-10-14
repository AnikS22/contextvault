"""Core thinking engine for extended thinking sessions."""

import asyncio
import re
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models.thinking import (
    ThinkingSession,
    Thought,
    SubQuestion,
    ThinkingSynthesis,
    ThinkingStatus,
    ThoughtType,
)
from ..integrations.ollama import OllamaIntegration

logger = logging.getLogger(__name__)


class ThinkingEngine:
    """
    Core engine that drives extended thinking sessions.

    This engine orchestrates the thinking process:
    1. Decides what to think about next
    2. Generates thoughts on that focus
    3. Creates new questions
    4. Synthesizes periodically
    5. Continues until time budget exhausted
    """

    def __init__(self, ollama_integration: Optional[OllamaIntegration] = None):
        """
        Initialize the thinking engine.

        Args:
            ollama_integration: Ollama integration instance (uses global if not provided)
        """
        from ..integrations.ollama import ollama_integration as default_integration
        self.ollama = ollama_integration or default_integration

    async def think(
        self,
        session: ThinkingSession,
        db_session: Session,
        synthesis_interval_seconds: int = 300
    ) -> ThinkingSession:
        """
        Main thinking loop - runs until time budget exhausted.

        Args:
            session: The thinking session to execute
            db_session: Database session for persistence
            synthesis_interval_seconds: How often to synthesize (default: 5 minutes)

        Returns:
            Updated thinking session with final results
        """
        logger.info(f"Starting thinking session {session.id} for {session.thinking_duration_minutes} minutes")

        try:
            # Initialize session
            start_time = datetime.utcnow()
            end_time = start_time + timedelta(minutes=session.thinking_duration_minutes)

            session.status = ThinkingStatus.THINKING.value
            session.started_at = start_time
            session.current_focus = "Initial exploration"
            db_session.commit()

            thoughts_count = 0
            last_synthesis_time = start_time

            # Main thinking loop
            while datetime.utcnow() < end_time:
                # Check if session was paused
                db_session.refresh(session)
                if session.status == ThinkingStatus.PAUSED.value:
                    logger.info(f"Session {session.id} paused by user")
                    break

                # 1. Decide what to think about next
                try:
                    focus = await self._decide_next_focus(session, db_session)
                    session.current_focus = focus
                    db_session.commit()

                    logger.debug(f"Session {session.id} focusing on: {focus[:100]}")

                except Exception as e:
                    logger.error(f"Error deciding next focus: {e}")
                    focus = "Continuing exploration of the original question"

                # 2. Generate thoughts on this focus
                try:
                    thoughts = await self._generate_thoughts(session, focus, db_session)

                    for thought_text, thought_type, confidence in thoughts:
                        thought = Thought(
                            session_id=session.id,
                            sequence_number=thoughts_count,
                            thought_text=thought_text,
                            thought_type=thought_type,
                            confidence=confidence,
                            time_offset_seconds=int((datetime.utcnow() - start_time).total_seconds())
                        )
                        db_session.add(thought)
                        thoughts_count += 1

                    session.total_thoughts = thoughts_count
                    db_session.commit()

                    logger.debug(f"Session {session.id} generated {len(thoughts)} thoughts (total: {thoughts_count})")

                except Exception as e:
                    logger.error(f"Error generating thoughts: {e}")

                # 3. Generate new sub-questions
                try:
                    if thoughts_count > 0 and thoughts_count % 5 == 0:  # Every 5 thoughts
                        new_questions = await self._generate_questions(session, db_session)

                        for q_text, priority in new_questions:
                            sub_q = SubQuestion(
                                session_id=session.id,
                                question_text=q_text,
                                priority=priority,
                                explored=False
                            )
                            db_session.add(sub_q)

                        session.total_questions = db_session.query(SubQuestion).filter(
                            SubQuestion.session_id == session.id
                        ).count()
                        db_session.commit()

                        logger.debug(f"Session {session.id} generated {len(new_questions)} new questions")

                except Exception as e:
                    logger.error(f"Error generating questions: {e}")

                # 4. Synthesize periodically
                try:
                    time_since_last_synthesis = (datetime.utcnow() - last_synthesis_time).total_seconds()
                    if time_since_last_synthesis >= synthesis_interval_seconds:
                        synthesis = await self._synthesize_understanding(session, db_session)
                        db_session.add(synthesis)

                        # Update confidence evolution
                        confidence_list = session.confidence_evolution or []
                        confidence_list.append(synthesis.confidence_level)
                        session.confidence_evolution = confidence_list

                        session.total_syntheses += 1
                        last_synthesis_time = datetime.utcnow()
                        db_session.commit()

                        logger.info(
                            f"Session {session.id} synthesis #{session.total_syntheses}: "
                            f"confidence={synthesis.confidence_level:.2f}"
                        )

                except Exception as e:
                    logger.error(f"Error during synthesis: {e}")

                # Small delay to avoid overwhelming the API
                await asyncio.sleep(3)

            # Final synthesis
            logger.info(f"Session {session.id} completing thinking phase")
            try:
                final_synthesis = await self._final_synthesis(session, db_session)
                db_session.add(final_synthesis)

                session.final_synthesis = final_synthesis.synthesis_text
                session.status = ThinkingStatus.COMPLETED.value
                session.completed_at = datetime.utcnow()

                # Update final confidence
                confidence_list = session.confidence_evolution or []
                confidence_list.append(final_synthesis.confidence_level)
                session.confidence_evolution = confidence_list

                db_session.commit()

                logger.info(
                    f"Session {session.id} completed: {session.total_thoughts} thoughts, "
                    f"{session.total_questions} questions, {session.total_syntheses} syntheses"
                )

            except Exception as e:
                logger.error(f"Error during final synthesis: {e}")
                session.status = ThinkingStatus.COMPLETED.value  # Mark complete even if synthesis failed
                session.completed_at = datetime.utcnow()
                db_session.commit()

            return session

        except Exception as e:
            logger.error(f"Thinking session {session.id} failed: {e}", exc_info=True)
            session.status = ThinkingStatus.FAILED.value
            session.error_message = str(e)
            session.completed_at = datetime.utcnow()
            db_session.commit()
            return session

    async def _decide_next_focus(self, session: ThinkingSession, db_session: Session) -> str:
        """
        Ask AI what aspect to explore next.

        Args:
            session: Current thinking session
            db_session: Database session

        Returns:
            Focus area for next thinking cycle
        """
        # Get recent thoughts
        recent_thoughts = db_session.query(Thought).filter(
            Thought.session_id == session.id
        ).order_by(Thought.sequence_number.desc()).limit(10).all()

        # Get unexplored high-priority questions
        unexplored_questions = db_session.query(SubQuestion).filter(
            SubQuestion.session_id == session.id,
            SubQuestion.explored == False
        ).order_by(SubQuestion.priority.desc()).limit(5).all()

        # Build prompt
        recent_context = "\n".join([f"- {t.thought_text}" for t in recent_thoughts])
        question_context = "\n".join([f"- {q.question_text}" for q in unexplored_questions])

        prompt = f"""Original Question: {session.original_question}

Recent thoughts:
{recent_context if recent_context else "(No recent thoughts yet)"}

Unexplored questions:
{question_context if question_context else "(No unexplored questions yet)"}

Based on what you've thought about so far, what aspect should you explore next to make progress on the original question?

Respond with just the focus area in one clear sentence."""

        try:
            response = await self.ollama.generate_response(
                model_id=session.model_id,
                prompt=prompt,
                inject_context=False
            )

            focus = response.get("response", "").strip()

            # If empty or too long, use default
            if not focus or len(focus) > 500:
                focus = f"Continue exploring: {session.original_question}"

            return focus

        except Exception as e:
            logger.error(f"Error deciding next focus: {e}")
            return f"Explore different aspects of: {session.original_question}"

    async def _generate_thoughts(
        self,
        session: ThinkingSession,
        focus: str,
        db_session: Session
    ) -> List[Tuple[str, str, float]]:
        """
        Generate thoughts about the current focus area.

        Args:
            session: Current thinking session
            focus: What to think about
            db_session: Database session

        Returns:
            List of (thought_text, thought_type, confidence) tuples
        """
        prompt = f"""Original Question: {session.original_question}

Current Focus: {focus}

Think deeply about this aspect. Generate 3-5 distinct thoughts:
- Explore the concept from different angles
- Question your assumptions
- Make connections to other ideas
- Identify potential insights

Format each thought as:
THOUGHT: [your thought here]
TYPE: [exploration/critique/connection/insight]
CONFIDENCE: [0.0-1.0]
---
(repeat for each thought)"""

        try:
            response = await self.ollama.generate_response(
                model_id=session.model_id,
                prompt=prompt,
                inject_context=False,
                temperature=0.8  # Higher temperature for more creative thinking
            )

            thoughts = self._parse_thoughts(response.get("response", ""))

            # If parsing failed, create at least one thought
            if not thoughts:
                thoughts = [(
                    f"Exploring {focus}",
                    ThoughtType.EXPLORATION.value,
                    0.5
                )]

            return thoughts

        except Exception as e:
            logger.error(f"Error generating thoughts: {e}")
            return [(f"Error generating thought: {str(e)}", ThoughtType.EXPLORATION.value, 0.3)]

    def _parse_thoughts(self, response_text: str) -> List[Tuple[str, str, float]]:
        """Parse thoughts from AI response."""
        thoughts = []

        # Split by separator
        thought_blocks = response_text.split("---")

        for block in thought_blocks:
            if not block.strip():
                continue

            # Extract thought, type, and confidence
            thought_match = re.search(r"THOUGHT:\s*(.+?)(?=TYPE:|$)", block, re.DOTALL | re.IGNORECASE)
            type_match = re.search(r"TYPE:\s*(\w+)", block, re.IGNORECASE)
            confidence_match = re.search(r"CONFIDENCE:\s*([\d.]+)", block, re.IGNORECASE)

            if thought_match:
                thought_text = thought_match.group(1).strip()

                # Determine type
                if type_match:
                    thought_type = type_match.group(1).lower()
                    # Validate against enum
                    if thought_type not in [t.value for t in ThoughtType]:
                        thought_type = ThoughtType.EXPLORATION.value
                else:
                    thought_type = ThoughtType.EXPLORATION.value

                # Parse confidence
                if confidence_match:
                    try:
                        confidence = float(confidence_match.group(1))
                        confidence = max(0.0, min(1.0, confidence))
                    except ValueError:
                        confidence = 0.5
                else:
                    confidence = 0.5

                thoughts.append((thought_text, thought_type, confidence))

        return thoughts

    async def _generate_questions(
        self,
        session: ThinkingSession,
        db_session: Session
    ) -> List[Tuple[str, int]]:
        """
        Generate new sub-questions based on recent thinking.

        Args:
            session: Current thinking session
            db_session: Database session

        Returns:
            List of (question_text, priority) tuples
        """
        # Get recent thoughts
        recent_thoughts = db_session.query(Thought).filter(
            Thought.session_id == session.id
        ).order_by(Thought.sequence_number.desc()).limit(15).all()

        if not recent_thoughts:
            return []

        recent_context = "\n".join([f"- {t.thought_text}" for t in recent_thoughts])

        prompt = f"""Original Question: {session.original_question}

Recent thoughts:
{recent_context}

Based on these thoughts, what new questions arise that would help answer the original question?
Generate 2-3 specific questions that explore uncertainties or new angles.

Format:
QUESTION: [question text]
PRIORITY: [1-10, where 10 is most important]
---
(repeat for each question)"""

        try:
            response = await self.ollama.generate_response(
                model_id=session.model_id,
                prompt=prompt,
                inject_context=False
            )

            questions = self._parse_questions(response.get("response", ""))
            return questions

        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            return []

    def _parse_questions(self, response_text: str) -> List[Tuple[str, int]]:
        """Parse questions from AI response."""
        questions = []

        # Split by separator
        question_blocks = response_text.split("---")

        for block in question_blocks:
            if not block.strip():
                continue

            # Extract question and priority
            question_match = re.search(r"QUESTION:\s*(.+?)(?=PRIORITY:|$)", block, re.DOTALL | re.IGNORECASE)
            priority_match = re.search(r"PRIORITY:\s*(\d+)", block, re.IGNORECASE)

            if question_match:
                question_text = question_match.group(1).strip()

                # Parse priority
                if priority_match:
                    try:
                        priority = int(priority_match.group(1))
                        priority = max(1, min(10, priority))
                    except ValueError:
                        priority = 5
                else:
                    priority = 5

                questions.append((question_text, priority))

        return questions

    async def _synthesize_understanding(
        self,
        session: ThinkingSession,
        db_session: Session
    ) -> ThinkingSynthesis:
        """
        Create periodic synthesis of current understanding.

        Args:
            session: Current thinking session
            db_session: Database session

        Returns:
            ThinkingSynthesis object
        """
        # Get all thoughts so far
        all_thoughts = db_session.query(Thought).filter(
            Thought.session_id == session.id
        ).order_by(Thought.sequence_number).all()

        thought_context = "\n".join([
            f"{i+1}. [{t.thought_type}] {t.thought_text}"
            for i, t in enumerate(all_thoughts)
        ])

        prompt = f"""Original Question: {session.original_question}

All thoughts so far:
{thought_context}

Synthesize your current understanding:
1. What have you learned so far?
2. What are 3-5 key insights?
3. What is your confidence level in your current understanding? (0.0-1.0)
4. What important questions remain unanswered?

Format:
SYNTHESIS: [your current understanding summary]
INSIGHTS:
- [insight 1]
- [insight 2]
- [insight 3]
CONFIDENCE: [0.0-1.0]
REMAINING:
- [question 1]
- [question 2]"""

        try:
            response = await self.ollama.generate_response(
                model_id=session.model_id,
                prompt=prompt,
                inject_context=False
            )

            synthesis_text = response.get("response", "")

            # Parse components
            insights = self._extract_insights(synthesis_text)
            confidence = self._extract_confidence(synthesis_text)
            remaining = self._extract_remaining_questions(synthesis_text)

            # Get sequence number
            sequence_num = db_session.query(ThinkingSynthesis).filter(
                ThinkingSynthesis.session_id == session.id
            ).count()

            return ThinkingSynthesis(
                session_id=session.id,
                sequence_number=sequence_num,
                synthesis_text=synthesis_text,
                key_insights=insights,
                confidence_level=confidence,
                remaining_questions=remaining,
                time_offset_seconds=int((datetime.utcnow() - session.started_at).total_seconds())
            )

        except Exception as e:
            logger.error(f"Error creating synthesis: {e}")
            # Return minimal synthesis
            return ThinkingSynthesis(
                session_id=session.id,
                sequence_number=0,
                synthesis_text=f"Synthesis error: {str(e)}",
                key_insights=[],
                confidence_level=0.3,
                remaining_questions=[],
                time_offset_seconds=0
            )

    async def _final_synthesis(
        self,
        session: ThinkingSession,
        db_session: Session
    ) -> ThinkingSynthesis:
        """Create final synthesis - the ultimate answer."""
        synthesis = await self._synthesize_understanding(session, db_session)
        return synthesis

    def _extract_insights(self, text: str) -> List[str]:
        """Extract insights from synthesis text."""
        insights = []

        # Look for INSIGHTS section
        insights_match = re.search(r"INSIGHTS:(.*?)(?=CONFIDENCE:|REMAINING:|$)", text, re.DOTALL | re.IGNORECASE)

        if insights_match:
            insights_text = insights_match.group(1)
            # Extract bullet points
            for line in insights_text.split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    insight = line[1:].strip()
                    if insight:
                        insights.append(insight)

        return insights[:10]  # Limit to 10 insights

    def _extract_confidence(self, text: str) -> float:
        """Extract confidence score from synthesis text."""
        confidence_match = re.search(r"CONFIDENCE:\s*([\d.]+)", text, re.IGNORECASE)

        if confidence_match:
            try:
                confidence = float(confidence_match.group(1))
                return max(0.0, min(1.0, confidence))
            except ValueError:
                pass

        return 0.5  # Default confidence

    def _extract_remaining_questions(self, text: str) -> List[str]:
        """Extract remaining questions from synthesis text."""
        questions = []

        # Look for REMAINING section
        remaining_match = re.search(r"REMAINING:(.*?)$", text, re.DOTALL | re.IGNORECASE)

        if remaining_match:
            remaining_text = remaining_match.group(1)
            # Extract bullet points
            for line in remaining_text.split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    question = line[1:].strip()
                    if question:
                        questions.append(question)

        return questions[:10]  # Limit to 10 questions


# Global thinking engine instance
thinking_engine = ThinkingEngine()
