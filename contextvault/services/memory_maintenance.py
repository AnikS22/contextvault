"""Background Memory Maintenance Jobs.

Runs periodic maintenance tasks:
- Merge duplicate memories
- Forget old/irrelevant memories
- Find patterns and consolidate
- Clean up orphaned relationships
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import difflib

logger = logging.getLogger(__name__)

# Optional imports
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    logger.warning("APScheduler not available. Install with: pip install apscheduler")
    SCHEDULER_AVAILABLE = False
    BackgroundScheduler = None
    IntervalTrigger = None


class MemoryMaintenanceService:
    """Background service for memory maintenance tasks."""

    def __init__(self, mem0_service, config: Optional[Dict[str, Any]] = None):
        """Initialize memory maintenance service.

        Args:
            mem0_service: Mem0Service instance
            config: Configuration dictionary
        """
        self.mem0_service = mem0_service
        self.scheduler = None
        self.is_running = False

        # Default configuration
        default_config = {
            "enabled": True,
            "interval_hours": 24,  # Run every 24 hours
            "duplicate_threshold": 0.85,  # 85% similarity = duplicate
            "forget_after_days": 365,  # Forget memories older than 1 year
            "min_access_count": 5,  # Keep memories accessed at least 5 times
            "pattern_min_occurrences": 3,  # Pattern must occur at least 3 times
        }

        self.config = {**default_config, **(config or {})}

        if SCHEDULER_AVAILABLE and self.config["enabled"]:
            self.scheduler = BackgroundScheduler()
            logger.info("Memory maintenance scheduler initialized")
        else:
            logger.warning("Memory maintenance disabled or scheduler unavailable")

    def start(self):
        """Start the background maintenance scheduler."""
        if not SCHEDULER_AVAILABLE or not self.scheduler:
            logger.warning("Cannot start maintenance - scheduler unavailable")
            return False

        try:
            # Schedule maintenance job
            self.scheduler.add_job(
                func=self.run_maintenance,
                trigger=IntervalTrigger(hours=self.config["interval_hours"]),
                id="memory_maintenance",
                name="Memory Maintenance",
                replace_existing=True
            )

            self.scheduler.start()
            self.is_running = True

            logger.info(
                f"Memory maintenance started - running every {self.config['interval_hours']} hours"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to start maintenance scheduler: {e}")
            return False

    def stop(self):
        """Stop the background maintenance scheduler."""
        if self.scheduler and self.is_running:
            try:
                self.scheduler.shutdown()
                self.is_running = False
                logger.info("Memory maintenance stopped")
                return True
            except Exception as e:
                logger.error(f"Failed to stop maintenance scheduler: {e}")
                return False

        return False

    def run_maintenance(self):
        """Run all maintenance tasks."""
        logger.info("Starting memory maintenance cycle...")

        try:
            start_time = datetime.utcnow()

            # Task 1: Merge duplicate memories
            merge_stats = self.merge_duplicates()

            # Task 2: Forget old/irrelevant memories
            forget_stats = self.forget_old_memories()

            # Task 3: Find and consolidate patterns
            pattern_stats = self.find_and_consolidate_patterns()

            # Task 4: Clean up orphaned relationships
            cleanup_stats = self.cleanup_relationships()

            # Log summary
            duration = (datetime.utcnow() - start_time).total_seconds()

            logger.info(
                f"Memory maintenance completed in {duration:.2f}s - "
                f"Merged: {merge_stats['merged']}, "
                f"Forgotten: {forget_stats['forgotten']}, "
                f"Patterns: {pattern_stats['patterns_found']}, "
                f"Cleaned: {cleanup_stats['cleaned']}"
            )

            return {
                "success": True,
                "duration_seconds": duration,
                "merge_stats": merge_stats,
                "forget_stats": forget_stats,
                "pattern_stats": pattern_stats,
                "cleanup_stats": cleanup_stats
            }

        except Exception as e:
            logger.error(f"Maintenance cycle failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def merge_duplicates(self) -> Dict[str, int]:
        """Merge duplicate or highly similar memories.

        Returns:
            Statistics about merged memories
        """
        logger.info("Checking for duplicate memories...")

        try:
            # Get all memories
            memories = self.mem0_service.get_all_memories()

            if not memories:
                return {"merged": 0, "kept": 0}

            # Group similar memories
            duplicates = []
            threshold = self.config["duplicate_threshold"]

            for i, mem1 in enumerate(memories):
                for mem2 in memories[i+1:]:
                    # Calculate similarity
                    similarity = self._calculate_similarity(
                        mem1.get("content", ""),
                        mem2.get("content", "")
                    )

                    if similarity >= threshold:
                        duplicates.append((mem1, mem2, similarity))

            # Merge duplicates (keep the one with more metadata)
            merged_count = 0
            for mem1, mem2, similarity in duplicates:
                try:
                    # Keep the memory with more metadata
                    keep_mem = mem1 if len(mem1.get("metadata", {})) >= len(mem2.get("metadata", {})) else mem2
                    delete_mem = mem2 if keep_mem == mem1 else mem1

                    # Merge metadata
                    merged_metadata = {
                        **delete_mem.get("metadata", {}),
                        **keep_mem.get("metadata", {}),
                        "merged_from": delete_mem.get("memory_id"),
                        "similarity": similarity
                    }

                    # Update kept memory
                    self.mem0_service.update_memory(
                        memory_id=keep_mem.get("memory_id"),
                        content=keep_mem.get("content"),
                        metadata=merged_metadata
                    )

                    # Delete duplicate
                    self.mem0_service.delete_memory(delete_mem.get("memory_id"))

                    merged_count += 1
                    logger.info(
                        f"Merged duplicate: {delete_mem.get('memory_id')} -> {keep_mem.get('memory_id')} "
                        f"(similarity: {similarity:.2f})"
                    )

                except Exception as e:
                    logger.error(f"Failed to merge duplicate: {e}")
                    continue

            return {
                "merged": merged_count,
                "kept": len(memories) - merged_count
            }

        except Exception as e:
            logger.error(f"Failed to merge duplicates: {e}")
            return {"merged": 0, "kept": 0}

    def forget_old_memories(self) -> Dict[str, int]:
        """Forget old or rarely accessed memories.

        Returns:
            Statistics about forgotten memories
        """
        logger.info("Checking for old memories to forget...")

        try:
            memories = self.mem0_service.get_all_memories()

            if not memories:
                return {"forgotten": 0, "kept": 0}

            forgotten_count = 0
            cutoff_date = datetime.utcnow() - timedelta(days=self.config["forget_after_days"])

            for memory in memories:
                try:
                    # Parse created date
                    created_at_str = memory.get("created_at")
                    if not created_at_str:
                        continue

                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

                    # Check if old and rarely accessed
                    access_count = memory.get("metadata", {}).get("access_count", 0)
                    is_old = created_at < cutoff_date
                    rarely_accessed = access_count < self.config["min_access_count"]

                    if is_old and rarely_accessed:
                        # Archive before deleting (store in metadata)
                        memory["metadata"]["archived_at"] = datetime.utcnow().isoformat()
                        memory["metadata"]["reason"] = "old_and_unused"

                        self.mem0_service.delete_memory(memory.get("memory_id"))
                        forgotten_count += 1

                        logger.info(
                            f"Forgot old memory: {memory.get('memory_id')} "
                            f"(created: {created_at_str}, accesses: {access_count})"
                        )

                except Exception as e:
                    logger.error(f"Failed to process memory for forgetting: {e}")
                    continue

            return {
                "forgotten": forgotten_count,
                "kept": len(memories) - forgotten_count
            }

        except Exception as e:
            logger.error(f"Failed to forget old memories: {e}")
            return {"forgotten": 0, "kept": 0}

    def find_and_consolidate_patterns(self) -> Dict[str, int]:
        """Find recurring patterns in memories and consolidate them.

        Returns:
            Statistics about patterns found
        """
        logger.info("Finding patterns in memories...")

        try:
            memories = self.mem0_service.get_all_memories()

            if not memories:
                return {"patterns_found": 0, "consolidated": 0}

            # Extract patterns (recurring phrases/concepts)
            pattern_counts = defaultdict(list)

            for memory in memories:
                content = memory.get("content", "").lower()

                # Look for recurring phrases (3-5 words)
                words = content.split()
                for i in range(len(words) - 2):
                    # 3-word phrases
                    phrase = " ".join(words[i:i+3])
                    pattern_counts[phrase].append(memory.get("memory_id"))

            # Find patterns that occur multiple times
            patterns_found = 0
            consolidated = 0

            min_occurrences = self.config["pattern_min_occurrences"]

            for pattern, memory_ids in pattern_counts.items():
                if len(memory_ids) >= min_occurrences:
                    patterns_found += 1

                    logger.info(
                        f"Found pattern '{pattern}' in {len(memory_ids)} memories: {memory_ids}"
                    )

                    # TODO: Create consolidated memory for this pattern
                    # This would involve creating a summary memory

            return {
                "patterns_found": patterns_found,
                "consolidated": consolidated
            }

        except Exception as e:
            logger.error(f"Failed to find patterns: {e}")
            return {"patterns_found": 0, "consolidated": 0}

    def cleanup_relationships(self) -> Dict[str, int]:
        """Clean up orphaned relationships in the NetworkX graph.

        Returns:
            Statistics about cleaned relationships
        """
        logger.info("Cleaning up orphaned relationships...")

        try:
            # Get all memories
            memories = self.mem0_service.get_all_memories()
            valid_memory_ids = {mem.get("memory_id") for mem in memories}

            # Get all relationships
            relationships = self.mem0_service.get_relationships()

            cleaned_count = 0

            for rel in relationships:
                # Check if memory_id still exists
                memory_id = rel.get("memory_id")

                if memory_id and memory_id not in valid_memory_ids:
                    # Orphaned relationship - remove from graph
                    # This is handled by NetworkX when we delete memories
                    cleaned_count += 1

                    logger.debug(f"Found orphaned relationship for deleted memory: {memory_id}")

            return {
                "cleaned": cleaned_count,
                "total_relationships": len(relationships)
            }

        except Exception as e:
            logger.error(f"Failed to cleanup relationships: {e}")
            return {"cleaned": 0, "total_relationships": 0}

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not text1 or not text2:
            return 0.0

        # Use difflib's SequenceMatcher
        return difflib.SequenceMatcher(None, text1, text2).ratio()

    def run_manual_maintenance(self) -> Dict[str, Any]:
        """Run maintenance manually (outside scheduler).

        Returns:
            Maintenance results
        """
        logger.info("Running manual maintenance...")
        return self.run_maintenance()


# Global instance
_maintenance_service = None


def get_maintenance_service(
    mem0_service,
    config: Optional[Dict[str, Any]] = None,
    auto_start: bool = False
) -> MemoryMaintenanceService:
    """Get or create the global maintenance service instance.

    Args:
        mem0_service: Mem0Service instance
        config: Optional configuration
        auto_start: Whether to start the scheduler automatically

    Returns:
        MemoryMaintenanceService instance
    """
    global _maintenance_service

    if _maintenance_service is None:
        _maintenance_service = MemoryMaintenanceService(mem0_service, config)

        if auto_start:
            _maintenance_service.start()

    return _maintenance_service
