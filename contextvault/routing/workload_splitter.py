"""Workload splitter for decomposing complex tasks into sub-problems."""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..models import ModelCapabilityType

logger = logging.getLogger(__name__)


@dataclass
class SubTask:
    """Represents a sub-task from workload decomposition."""

    task_id: str
    description: str
    required_capabilities: List[str]
    dependencies: List[str]  # IDs of tasks that must complete first
    priority: int  # Higher = more important
    estimated_complexity: float  # 0.0 to 1.0
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "required_capabilities": self.required_capabilities,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "estimated_complexity": self.estimated_complexity,
            "metadata": self.metadata,
        }


@dataclass
class WorkloadDecomposition:
    """Represents the full decomposition of a workload."""

    original_task: str
    sub_tasks: List[SubTask]
    execution_strategy: str  # sequential, parallel, hybrid
    estimated_total_complexity: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "original_task": self.original_task,
            "sub_tasks": [st.to_dict() for st in self.sub_tasks],
            "execution_strategy": self.execution_strategy,
            "estimated_total_complexity": self.estimated_total_complexity,
            "metadata": self.metadata,
        }

    def get_executable_tasks(self, completed_task_ids: Optional[List[str]] = None) -> List[SubTask]:
        """
        Get tasks that can be executed now (dependencies met).

        Args:
            completed_task_ids: List of already completed task IDs

        Returns:
            List of sub-tasks ready for execution
        """
        completed = set(completed_task_ids or [])
        executable = []

        for task in self.sub_tasks:
            # Skip if already completed
            if task.task_id in completed:
                continue

            # Check if all dependencies are met
            if all(dep in completed for dep in task.dependencies):
                executable.append(task)

        # Sort by priority
        executable.sort(key=lambda t: t.priority, reverse=True)

        return executable


class WorkloadSplitter:
    """
    Service for decomposing complex workloads into sub-tasks.

    Analyzes requests to identify multiple sub-problems that can be
    routed to different specialized models.
    """

    def __init__(self):
        """Initialize the workload splitter."""

        # Patterns that indicate multi-part tasks
        self.multi_part_patterns = [
            r'\d+[\)\.]\s+',  # Numbered lists: 1. 2. 3.
            r'^[-*]\s+',  # Bullet points
            r'\b(first|second|third|finally|lastly)\b',  # Sequential indicators
            r'\b(and|also|additionally|furthermore)\b',  # Addition indicators
            r'\b(then|next|after that|subsequently)\b',  # Sequential flow
        ]

        # Keywords indicating complexity
        self.complexity_indicators = {
            "high": [
                r'\b(analyze|evaluate|compare|synthesize|design|architect)\b',
                r'\b(complex|difficult|challenging|intricate|sophisticated)\b',
                r'\b(comprehensive|thorough|detailed|in-depth)\b',
            ],
            "medium": [
                r'\b(explain|describe|discuss|summarize|review)\b',
                r'\b(moderate|standard|typical|normal)\b',
            ],
            "low": [
                r'\b(list|name|identify|define|state)\b',
                r'\b(simple|easy|straightforward|basic)\b',
            ],
        }

    def should_split(self, text: str) -> bool:
        """
        Determine if a task should be split into sub-tasks.

        Args:
            text: Input text to analyze

        Returns:
            True if task should be split, False otherwise
        """
        if not text or len(text.strip()) < 50:
            # Too short to benefit from splitting
            return False

        # Check for multi-part indicators
        for pattern in self.multi_part_patterns:
            if len(re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)) >= 2:
                return True

        # Check for multiple sentences with different capabilities
        sentences = re.split(r'[.!?]+', text)
        if len(sentences) >= 3:
            # Check if sentences require different capabilities
            from .model_router import ModelRouter
            router = ModelRouter()

            capability_sets = []
            for sentence in sentences:
                if sentence.strip():
                    caps = set(router.detect_capabilities(sentence.strip()))
                    if caps:
                        capability_sets.append(caps)

            # If different sentences need different capabilities, consider splitting
            if len(capability_sets) >= 2:
                # Check if capability sets are significantly different
                all_caps = set.union(*capability_sets) if capability_sets else set()
                if len(all_caps) >= 3:
                    return True

        # Check for compound questions
        compound_indicators = [
            r'\bwhat.*and.*how\b',
            r'\bhow.*and.*why\b',
            r'\bwhen.*and.*where\b',
            r'\bwho.*and.*what\b',
        ]
        for pattern in compound_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def decompose(self, text: str, max_sub_tasks: int = 10) -> WorkloadDecomposition:
        """
        Decompose a complex task into sub-tasks.

        Args:
            text: Input text to decompose
            max_sub_tasks: Maximum number of sub-tasks to create

        Returns:
            WorkloadDecomposition with sub-tasks and execution strategy
        """
        logger.info(f"Decomposing workload (length={len(text)})")

        if not self.should_split(text):
            # Create single task
            logger.debug("Task does not require splitting")
            return self._create_single_task_decomposition(text)

        # Try different decomposition strategies
        sub_tasks = []

        # Strategy 1: Split by numbered/bulleted lists
        list_items = self._extract_list_items(text)
        if list_items and len(list_items) >= 2:
            logger.debug(f"Decomposed by list structure: {len(list_items)} items")
            sub_tasks = self._create_tasks_from_list_items(list_items)

        # Strategy 2: Split by sentences if no list structure
        if not sub_tasks:
            sentences = self._split_by_sentences(text)
            if len(sentences) >= 2:
                logger.debug(f"Decomposed by sentences: {len(sentences)} sentences")
                sub_tasks = self._create_tasks_from_sentences(sentences)

        # Strategy 3: Split by logical sections
        if not sub_tasks:
            sections = self._split_by_sections(text)
            if len(sections) >= 2:
                logger.debug(f"Decomposed by sections: {len(sections)} sections")
                sub_tasks = self._create_tasks_from_sections(sections)

        # If still no sub-tasks, create single task
        if not sub_tasks:
            logger.debug("Could not decompose, creating single task")
            return self._create_single_task_decomposition(text)

        # Limit number of sub-tasks
        if len(sub_tasks) > max_sub_tasks:
            logger.warning(f"Too many sub-tasks ({len(sub_tasks)}), merging to {max_sub_tasks}")
            sub_tasks = self._merge_sub_tasks(sub_tasks, max_sub_tasks)

        # Determine execution strategy
        execution_strategy = self._determine_execution_strategy(sub_tasks)

        # Calculate total complexity
        total_complexity = sum(task.estimated_complexity for task in sub_tasks) / len(sub_tasks)

        decomposition = WorkloadDecomposition(
            original_task=text,
            sub_tasks=sub_tasks,
            execution_strategy=execution_strategy,
            estimated_total_complexity=total_complexity,
            metadata={
                "num_sub_tasks": len(sub_tasks),
                "decomposition_method": "auto",
            }
        )

        logger.info(
            f"Decomposed into {len(sub_tasks)} sub-tasks "
            f"with {execution_strategy} execution strategy"
        )

        return decomposition

    def _create_single_task_decomposition(self, text: str) -> WorkloadDecomposition:
        """Create a decomposition with a single task."""
        from .model_router import ModelRouter
        router = ModelRouter()

        capabilities = router.detect_capabilities(text)
        complexity = self._estimate_complexity(text)

        task = SubTask(
            task_id="task_0",
            description=text,
            required_capabilities=capabilities,
            dependencies=[],
            priority=1,
            estimated_complexity=complexity,
            metadata={}
        )

        return WorkloadDecomposition(
            original_task=text,
            sub_tasks=[task],
            execution_strategy="sequential",
            estimated_total_complexity=complexity,
            metadata={"num_sub_tasks": 1, "decomposition_method": "single"}
        )

    def _extract_list_items(self, text: str) -> List[str]:
        """Extract numbered or bulleted list items from text."""
        lines = text.split('\n')
        list_items = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for numbered list (1. 2. 3. or 1) 2) 3))
            if re.match(r'^\d+[\)\.]\s+', line):
                item = re.sub(r'^\d+[\)\.]\s+', '', line)
                list_items.append(item.strip())

            # Check for bulleted list (- or *)
            elif re.match(r'^[-*]\s+', line):
                item = re.sub(r'^[-*]\s+', '', line)
                list_items.append(item.strip())

        return list_items

    def _split_by_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Split by sentence-ending punctuation
        sentences = re.split(r'[.!?]+', text)

        # Filter empty and very short sentences
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

        return sentences

    def _split_by_sections(self, text: str) -> List[str]:
        """Split text by logical sections (paragraphs, line breaks)."""
        # Split by double line breaks (paragraphs)
        sections = re.split(r'\n\s*\n', text)

        # Filter empty sections
        sections = [s.strip() for s in sections if s.strip() and len(s.strip()) > 20]

        return sections

    def _create_tasks_from_list_items(self, items: List[str]) -> List[SubTask]:
        """Create sub-tasks from list items."""
        from .model_router import ModelRouter
        router = ModelRouter()

        sub_tasks = []
        for i, item in enumerate(items):
            capabilities = router.detect_capabilities(item)
            complexity = self._estimate_complexity(item)

            task = SubTask(
                task_id=f"task_{i}",
                description=item,
                required_capabilities=capabilities,
                dependencies=[],  # List items typically independent
                priority=len(items) - i,  # Earlier items higher priority
                estimated_complexity=complexity,
                metadata={"source": "list_item"}
            )
            sub_tasks.append(task)

        return sub_tasks

    def _create_tasks_from_sentences(self, sentences: List[str]) -> List[SubTask]:
        """Create sub-tasks from sentences."""
        from .model_router import ModelRouter
        router = ModelRouter()

        sub_tasks = []
        for i, sentence in enumerate(sentences):
            capabilities = router.detect_capabilities(sentence)
            complexity = self._estimate_complexity(sentence)

            # Sentences may have dependencies (sequential)
            dependencies = [f"task_{i-1}"] if i > 0 else []

            task = SubTask(
                task_id=f"task_{i}",
                description=sentence,
                required_capabilities=capabilities,
                dependencies=dependencies,
                priority=len(sentences) - i,
                estimated_complexity=complexity,
                metadata={"source": "sentence"}
            )
            sub_tasks.append(task)

        return sub_tasks

    def _create_tasks_from_sections(self, sections: List[str]) -> List[SubTask]:
        """Create sub-tasks from sections."""
        from .model_router import ModelRouter
        router = ModelRouter()

        sub_tasks = []
        for i, section in enumerate(sections):
            capabilities = router.detect_capabilities(section)
            complexity = self._estimate_complexity(section)

            task = SubTask(
                task_id=f"task_{i}",
                description=section,
                required_capabilities=capabilities,
                dependencies=[],  # Sections typically independent
                priority=len(sections) - i,
                estimated_complexity=complexity,
                metadata={"source": "section"}
            )
            sub_tasks.append(task)

        return sub_tasks

    def _merge_sub_tasks(self, tasks: List[SubTask], max_tasks: int) -> List[SubTask]:
        """Merge sub-tasks to reduce to maximum number."""
        if len(tasks) <= max_tasks:
            return tasks

        # Group tasks with similar capabilities
        from collections import defaultdict
        by_capabilities = defaultdict(list)

        for task in tasks:
            key = tuple(sorted(task.required_capabilities))
            by_capabilities[key].append(task)

        # Merge groups
        merged_tasks = []
        task_counter = 0

        for cap_key, task_group in by_capabilities.items():
            if len(merged_tasks) >= max_tasks:
                # Add remaining to last group
                if merged_tasks:
                    last_task = merged_tasks[-1]
                    for task in task_group:
                        last_task.description += "\n" + task.description
                    last_task.estimated_complexity = min(1.0, last_task.estimated_complexity * 1.2)
            else:
                # Merge tasks in this group
                merged_description = "\n".join(t.description for t in task_group)
                merged_complexity = sum(t.estimated_complexity for t in task_group) / len(task_group)

                merged_task = SubTask(
                    task_id=f"task_{task_counter}",
                    description=merged_description,
                    required_capabilities=list(cap_key),
                    dependencies=[],
                    priority=max(t.priority for t in task_group),
                    estimated_complexity=min(1.0, merged_complexity),
                    metadata={"merged_from": [t.task_id for t in task_group]}
                )
                merged_tasks.append(merged_task)
                task_counter += 1

        return merged_tasks[:max_tasks]

    def _estimate_complexity(self, text: str) -> float:
        """
        Estimate task complexity (0.0 to 1.0).

        Args:
            text: Task text

        Returns:
            Complexity score between 0.0 and 1.0
        """
        text_lower = text.lower()
        score = 0.5  # Base score

        # Check complexity indicators
        for level, patterns in self.complexity_indicators.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    if level == "high":
                        score += 0.2
                    elif level == "medium":
                        score += 0.1
                    elif level == "low":
                        score -= 0.1
                    break

        # Length factor
        word_count = len(text.split())
        if word_count > 100:
            score += 0.2
        elif word_count > 50:
            score += 0.1
        elif word_count < 10:
            score -= 0.1

        # Clamp to 0.0-1.0
        return max(0.0, min(1.0, score))

    def _determine_execution_strategy(self, tasks: List[SubTask]) -> str:
        """
        Determine execution strategy based on task dependencies.

        Returns:
            "sequential", "parallel", or "hybrid"
        """
        # Check if tasks have dependencies
        has_dependencies = any(task.dependencies for task in tasks)

        if not has_dependencies:
            # All tasks independent - can run in parallel
            return "parallel"

        # Check if tasks form a linear chain
        task_ids = {task.task_id for task in tasks}
        is_linear = True

        for i, task in enumerate(tasks):
            if i == 0:
                # First task should have no dependencies
                if task.dependencies:
                    is_linear = False
                    break
            else:
                # Each task should depend only on previous task
                expected_dep = tasks[i-1].task_id
                if len(task.dependencies) != 1 or task.dependencies[0] != expected_dep:
                    is_linear = False
                    break

        if is_linear:
            return "sequential"
        else:
            return "hybrid"


# Global splitter instance
workload_splitter = WorkloadSplitter()
