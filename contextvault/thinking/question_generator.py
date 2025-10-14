"""Question generator for extended thinking sessions."""

import re
import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models.thinking import ThinkingSession, Thought, SubQuestion
from ..integrations.ollama import OllamaIntegration

logger = logging.getLogger(__name__)


class QuestionGenerator:
    """
    Generates follow-up questions during thinking.

    As the AI thinks, it discovers new questions that need exploration.
    This component generates those questions based on recent thoughts.
    """

    def __init__(self, ollama_integration: Optional[OllamaIntegration] = None):
        """
        Initialize the question generator.

        Args:
            ollama_integration: Ollama integration instance (uses global if not provided)
        """
        from ..integrations.ollama import ollama_integration as default_integration
        self.ollama = ollama_integration or default_integration

    async def generate_questions(
        self,
        session: ThinkingSession,
        recent_thoughts: List[Thought],
        max_questions: int = 3
    ) -> List[Tuple[str, int]]:
        """
        Generate new questions based on recent thoughts.

        Args:
            session: Current thinking session
            recent_thoughts: Recent thoughts to base questions on
            max_questions: Maximum number of questions to generate

        Returns:
            List of (question_text, priority) tuples where priority is 1-10
        """
        if not recent_thoughts:
            logger.debug("No recent thoughts provided, skipping question generation")
            return []

        # Build context from recent thoughts
        thought_context = "\n".join([
            f"- [{t.thought_type}] {t.thought_text}"
            for t in recent_thoughts
        ])

        prompt = f"""Original Question: {session.original_question}

Recent thoughts:
{thought_context}

Based on these thoughts, what new questions arise that would help answer the original question?
Generate {max_questions} specific, focused questions that:
- Explore uncertainties or gaps in understanding
- Examine assumptions that need validation
- Investigate new angles or connections
- Go deeper into interesting areas

Format each question as:
QUESTION: [clear, specific question text]
PRIORITY: [1-10, where 10 is most critical to answer]
WHY: [brief explanation of why this question matters]
---
(repeat for each question)"""

        try:
            response = await self.ollama.generate_response(
                model_id=session.model_id,
                prompt=prompt,
                inject_context=False,
                temperature=0.7  # Moderate creativity
            )

            questions = self._parse_questions(response.get("response", ""))

            logger.info(f"Generated {len(questions)} questions for session {session.id}")

            return questions[:max_questions]

        except Exception as e:
            logger.error(f"Error generating questions: {e}", exc_info=True)
            return []

    async def generate_followup_question(
        self,
        session: ThinkingSession,
        specific_thought: Thought
    ) -> Optional[Tuple[str, int]]:
        """
        Generate a follow-up question for a specific thought.

        Useful when a particular thought sparks a new line of inquiry.

        Args:
            session: Current thinking session
            specific_thought: The thought that sparked the question

        Returns:
            (question_text, priority) tuple or None
        """
        prompt = f"""Original Question: {session.original_question}

A thought emerged:
"{specific_thought.thought_text}"

What is the most important follow-up question this thought raises?
Generate ONE specific question that would help clarify or expand on this thought.

Format:
QUESTION: [question text]
PRIORITY: [1-10]"""

        try:
            response = await self.ollama.generate_response(
                model_id=session.model_id,
                prompt=prompt,
                inject_context=False,
                temperature=0.6
            )

            questions = self._parse_questions(response.get("response", ""))

            if questions:
                return questions[0]
            return None

        except Exception as e:
            logger.error(f"Error generating follow-up question: {e}")
            return None

    async def prioritize_questions(
        self,
        session: ThinkingSession,
        questions: List[SubQuestion],
        db_session: Session
    ) -> List[SubQuestion]:
        """
        Re-prioritize existing questions based on current understanding.

        As thinking progresses, question priorities may need adjustment.

        Args:
            session: Current thinking session
            questions: Questions to prioritize
            db_session: Database session

        Returns:
            Questions sorted by priority (highest first)
        """
        if not questions:
            return []

        # Get recent thoughts for context
        recent_thoughts = db_session.query(Thought).filter(
            Thought.session_id == session.id
        ).order_by(Thought.sequence_number.desc()).limit(20).all()

        thought_context = "\n".join([
            f"- {t.thought_text}"
            for t in recent_thoughts
        ])

        question_list = "\n".join([
            f"{i+1}. {q.question_text} (current priority: {q.priority})"
            for i, q in enumerate(questions)
        ])

        prompt = f"""Original Question: {session.original_question}

Recent thoughts:
{thought_context}

Questions to prioritize:
{question_list}

Based on current understanding, rank these questions by importance (1-10).
Which questions are most critical to answer next?

Format:
QUESTION_NUMBER: [1, 2, 3, etc.]
NEW_PRIORITY: [1-10]
REASONING: [why this priority]
---
(repeat for each question)"""

        try:
            response = await self.ollama.generate_response(
                model_id=session.model_id,
                prompt=prompt,
                inject_context=False,
                temperature=0.5  # Lower temperature for analytical task
            )

            # Parse reprioritization
            priorities = self._parse_priorities(response.get("response", ""))

            # Update question priorities
            for question_num, new_priority in priorities.items():
                if 0 <= question_num < len(questions):
                    questions[question_num].priority = new_priority

            # Sort by priority
            questions.sort(key=lambda q: q.priority, reverse=True)

            logger.info(f"Reprioritized {len(questions)} questions for session {session.id}")

            return questions

        except Exception as e:
            logger.error(f"Error prioritizing questions: {e}")
            # Return original list sorted by current priority
            return sorted(questions, key=lambda q: q.priority, reverse=True)

    def _parse_questions(self, response_text: str) -> List[Tuple[str, int]]:
        """
        Parse questions from AI response.

        Args:
            response_text: Raw response from AI

        Returns:
            List of (question_text, priority) tuples
        """
        questions = []

        # Split by separator
        question_blocks = response_text.split("---")

        for block in question_blocks:
            if not block.strip():
                continue

            # Extract question and priority
            question_match = re.search(
                r"QUESTION:\s*(.+?)(?=PRIORITY:|WHY:|$)",
                block,
                re.DOTALL | re.IGNORECASE
            )
            priority_match = re.search(r"PRIORITY:\s*(\d+)", block, re.IGNORECASE)

            if question_match:
                question_text = question_match.group(1).strip()

                # Clean up question text
                question_text = question_text.strip('"\'')
                question_text = re.sub(r'\s+', ' ', question_text)

                # Parse priority
                if priority_match:
                    try:
                        priority = int(priority_match.group(1))
                        priority = max(1, min(10, priority))  # Clamp to 1-10
                    except ValueError:
                        priority = 5
                else:
                    priority = 5

                # Only add non-empty questions
                if question_text and len(question_text) > 10:
                    questions.append((question_text, priority))

        return questions

    def _parse_priorities(self, response_text: str) -> Dict[int, int]:
        """
        Parse priority updates from AI response.

        Args:
            response_text: Raw response from AI

        Returns:
            Dict mapping question_number -> new_priority
        """
        priorities = {}

        # Split by separator
        priority_blocks = response_text.split("---")

        for block in priority_blocks:
            if not block.strip():
                continue

            # Extract question number and new priority
            number_match = re.search(r"QUESTION_NUMBER:\s*(\d+)", block, re.IGNORECASE)
            priority_match = re.search(r"NEW_PRIORITY:\s*(\d+)", block, re.IGNORECASE)

            if number_match and priority_match:
                try:
                    question_num = int(number_match.group(1)) - 1  # Convert to 0-indexed
                    new_priority = int(priority_match.group(1))
                    new_priority = max(1, min(10, new_priority))

                    priorities[question_num] = new_priority
                except ValueError:
                    continue

        return priorities

    async def generate_clarifying_questions(
        self,
        session: ThinkingSession,
        ambiguous_area: str
    ) -> List[Tuple[str, int]]:
        """
        Generate clarifying questions for ambiguous or unclear areas.

        Args:
            session: Current thinking session
            ambiguous_area: Description of what's unclear

        Returns:
            List of (question_text, priority) tuples
        """
        prompt = f"""Original Question: {session.original_question}

There's ambiguity or uncertainty around: {ambiguous_area}

Generate 2-3 specific clarifying questions that would help resolve this uncertainty.

Format:
QUESTION: [question text]
PRIORITY: [1-10]
---
(repeat)"""

        try:
            response = await self.ollama.generate_response(
                model_id=session.model_id,
                prompt=prompt,
                inject_context=False,
                temperature=0.6
            )

            return self._parse_questions(response.get("response", ""))

        except Exception as e:
            logger.error(f"Error generating clarifying questions: {e}")
            return []


# Global question generator instance
question_generator = QuestionGenerator()
