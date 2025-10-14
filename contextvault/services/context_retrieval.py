"""Smart context retrieval service."""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..database import get_db_context
from ..models import ContextEntry, ContextType
from ..config import settings
from .permissions import permission_service
from .vault import vault_service
from .semantic_search import get_semantic_search_service

logger = logging.getLogger(__name__)

# Optional Graph RAG import
try:
    from ..storage.graph_db import GraphRAGDatabase
    GRAPH_RAG_AVAILABLE = True
except ImportError:
    GRAPH_RAG_AVAILABLE = False
    GraphRAGDatabase = None
    logger.warning("Graph RAG not available - install neo4j and spacy to enable")


class ContextRetrievalService:
    """Service for intelligent context retrieval and ranking."""
    
    def __init__(self, db_session: Optional[Session] = None, use_graph_rag: bool = False):
        """Initialize the context retrieval service.

        Args:
            db_session: Optional database session
            use_graph_rag: Whether to use Graph RAG for retrieval
        """
        self.db_session = db_session
        self.use_graph_rag = use_graph_rag and GRAPH_RAG_AVAILABLE

        # Initialize Graph RAG if available and requested
        self.graph_rag_db = None
        if self.use_graph_rag and GRAPH_RAG_AVAILABLE:
            try:
                self.graph_rag_db = GraphRAGDatabase()
                if not self.graph_rag_db.is_available():
                    logger.warning("Graph RAG initialized but Neo4j is not available")
                    self.use_graph_rag = False
                else:
                    logger.info("Graph RAG initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Graph RAG: {e}")
                self.use_graph_rag = False

        # Create session-specific services to avoid detached instance errors
        if db_session:
            from .permissions import PermissionService
            from .vault import VaultService
            self.permission_service = PermissionService(db_session)
            self.vault_service = VaultService(db_session)
        else:
            self.permission_service = permission_service
            self.vault_service = vault_service
    
    def get_relevant_context(
        self,
        model_id: str,
        query_context: Optional[str] = None,
        limit: int = 50,
        context_types: Optional[List[ContextType]] = None,
        tags: Optional[List[str]] = None,
        include_recent: bool = True,
        max_age_days: Optional[int] = None,
    ) -> Tuple[List[ContextEntry], Dict[str, Any]]:
        """
        Get relevant context for an AI model with intelligent ranking.
        
        Args:
            model_id: The AI model requesting context
            query_context: Optional query context to find relevant entries
            limit: Maximum number of entries to return
            context_types: Filter by specific context types
            tags: Filter by specific tags
            include_recent: Whether to boost recent entries
            max_age_days: Maximum age of entries to consider
            
        Returns:
            Tuple of (context_entries, metadata)
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate model access
            allowed, reason, modified_query = self.permission_service.validate_model_access(
                model_id, {
                    "limit": limit,
                    "context_types": context_types,
                    "tags": tags,
                }
            )
            
            if not allowed:
                logger.warning(f"Model {model_id} access denied for context retrieval: {reason}")
                return [], {"error": reason, "access_denied": True}
            
            # Use modified query parameters
            limit = modified_query.get("limit", limit)
            context_types = modified_query.get("context_types", context_types)
            
            # Build search filters
            filters = {}
            
            if context_types:
                filters["context_types"] = context_types
            
            if tags:
                filters["tags"] = tags
            
            if max_age_days:
                filters["since"] = datetime.utcnow() - timedelta(days=max_age_days)
            
            # Perform initial retrieval
            entries = []
            semantic_scores = {}
            graph_rag_metadata = {}

            if query_context and query_context.strip():
                # Try Graph RAG first if enabled
                if self.use_graph_rag and self.graph_rag_db:
                    logger.info(f"Using Graph RAG for query: {query_context[:50]}...")

                    graph_results, graph_rag_metadata = self._get_graph_rag_context(
                        query=query_context.strip(),
                        limit=limit * 2
                    )

                    if graph_results and graph_rag_metadata.get("graph_rag_used"):
                        # Convert Graph RAG results to ContextEntry objects
                        entries = self._convert_graph_results_to_entries(graph_results)
                        total = len(entries)

                        # Extract relevance scores from Graph RAG results
                        semantic_scores = {
                            entries[i].id: graph_results[i].get('relevance_score', 0.0)
                            for i in range(len(entries))
                            if i < len(graph_results)
                        }

                        logger.info(f"Graph RAG retrieved {total} results")
                    else:
                        # Graph RAG failed, fallback to traditional search
                        logger.warning("Graph RAG query failed, falling back to semantic search")
                        self.use_graph_rag = False

                # If Graph RAG not used, try semantic search
                if not entries:
                    semantic_service = get_semantic_search_service()
                    if semantic_service.is_available():
                        logger.info(f"Using semantic search for query: {query_context[:50]}...")

                        # Get semantic search results with hybrid scoring
                        semantic_results = semantic_service.search_with_hybrid_scoring(
                            query=query_context.strip(),
                            db_session=self.db_session,
                            max_results=limit * 2
                        )

                        # Extract entries and metadata
                        entries = [result[0] for result in semantic_results]
                        total = len(entries)

                        # Add semantic scores to metadata
                        semantic_scores = {result[0].id: result[2] for result in semantic_results}

                    else:
                        logger.info("Semantic search not available, falling back to keyword search")
                        # Fallback to keyword search
                        entries, total = self.vault_service.search_context(
                            query=query_context.strip(),
                            limit=limit * 2,
                            context_types=context_types,
                            tags=tags,
                        )
            else:
                # Get recent entries
                entries, total = self.vault_service.get_context(
                    filters=filters,
                    limit=limit * 2,
                    order_by="created_at" if include_recent else "access_count",
                    order_desc=True,
                )
                semantic_scores = {}
            
            # Apply permission filtering
            filtered_entries = self.permission_service.apply_permission_filters(entries, model_id)
            
            # Score and rank entries (incorporate semantic scores if available)
            scored_entries = self._score_entries(
                filtered_entries,
                query_context=query_context,
                include_recent=include_recent,
                semantic_scores=semantic_scores,
            )
            
            # Apply final limit
            final_entries = scored_entries[:limit]
            
            # Record access for returned entries
            with get_db_context() as db:
                for entry in final_entries:
                    entry.record_access()
                db.commit()
            
            # Generate metadata
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            metadata = {
                "model_id": model_id,
                "query_context": query_context,
                "total_found": len(entries),
                "after_permissions": len(filtered_entries),
                "returned": len(final_entries),
                "processing_time_ms": round(processing_time * 1000),
                "filters_applied": filters,
                "permission_summary": self.permission_service.get_permission_summary(model_id),
            }

            # Add Graph RAG metadata if used
            if graph_rag_metadata:
                metadata["graph_rag"] = graph_rag_metadata
            
            logger.info(f"Context retrieval completed for model {model_id}: {len(final_entries)} entries in {metadata['processing_time_ms']}ms")
            
            return final_entries, metadata
            
        except Exception as e:
            logger.error(f"Error in context retrieval for model {model_id}: {str(e)}", exc_info=True)
            return [], {"error": str(e), "processing_failed": True}
    
    def _score_entries(
        self,
        entries: List[ContextEntry],
        query_context: Optional[str] = None,
        include_recent: bool = True,
        semantic_scores: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> List[ContextEntry]:
        """
        Score and rank context entries by relevance.
        
        Args:
            entries: List of context entries to score
            query_context: Query context for relevance scoring
            include_recent: Whether to boost recent entries
            
        Returns:
            List of entries sorted by relevance score (highest first)
        """
        if not entries:
            return []
        
        scored_entries = []
        
        for entry in entries:
            # Use semantic score if available, otherwise calculate traditional score
            if semantic_scores and entry.id in semantic_scores:
                # Use pre-calculated semantic hybrid score
                semantic_score_data = semantic_scores[entry.id]
                score = semantic_score_data.get('total', 0.0)
                logger.debug(f"Using semantic score for entry {entry.id}: {score}")
            else:
                # Fallback to traditional scoring
                score = self._calculate_relevance_score(
                    entry,
                    query_context=query_context,
                    include_recent=include_recent,
                )
            
            # Update relevance score in the entry for potential caching
            entry.relevance_score = score
            
            scored_entries.append((entry, score))
        
        # Sort by score (highest first)
        scored_entries.sort(key=lambda x: x[1], reverse=True)
        
        return [entry for entry, score in scored_entries]
    
    def _calculate_relevance_score(
        self,
        entry: ContextEntry,
        query_context: Optional[str] = None,
        include_recent: bool = True,
    ) -> float:
        """
        Calculate relevance score for a context entry.
        
        Args:
            entry: The context entry to score
            query_context: Query context for relevance
            include_recent: Whether to include recency in scoring
            
        Returns:
            Relevance score (higher = more relevant)
        """
        score = 0.0
        
        # Base score from access count (popularity)
        access_score = min(entry.access_count or 0, 100) / 100.0  # Normalize to 0-1
        score += access_score * 0.3
        
        # Content type scoring (preferences and notes are often more relevant)
        type_scores = {
            ContextType.PREFERENCE: 0.9,
            ContextType.NOTE: 0.8,
            ContextType.TEXT: 0.7,
            ContextType.EVENT: 0.6,
            ContextType.FILE: 0.5,
        }
        score += type_scores.get(entry.context_type, 0.5) * 0.2
        
        # Recency scoring
        if include_recent and entry.created_at:
            days_old = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days
            if days_old <= 1:
                recency_score = 1.0
            elif days_old <= 7:
                recency_score = 0.8
            elif days_old <= 30:
                recency_score = 0.6
            elif days_old <= 90:
                recency_score = 0.4
            else:
                recency_score = 0.2
            
            score += recency_score * 0.2
        
        # Query relevance scoring
        if query_context and query_context.strip():
            relevance_score = self._calculate_text_relevance(entry.content, query_context)
            
            # Also check tags and source for relevance
            if entry.tags:
                tag_relevance = self._calculate_text_relevance(" ".join(entry.tags), query_context)
                relevance_score = max(relevance_score, tag_relevance * 0.8)
            
            if entry.source:
                source_relevance = self._calculate_text_relevance(entry.source, query_context)
                relevance_score = max(relevance_score, source_relevance * 0.6)
            
            score += relevance_score * 0.3
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _calculate_text_relevance(self, text: str, query: str) -> float:
        """
        Calculate text relevance using simple keyword matching.
        
        In a production system, this would use more sophisticated
        methods like TF-IDF, embeddings, or semantic search.
        
        Args:
            text: The text to score
            query: The query to match against
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        if not text or not query:
            return 0.0
        
        # Normalize text
        text_lower = text.lower()
        query_lower = query.lower()
        
        # Exact match gets highest score
        if query_lower in text_lower:
            return 1.0
        
        # Split into words and check for matches
        query_words = re.findall(r'\w+', query_lower)
        text_words = re.findall(r'\w+', text_lower)
        
        if not query_words:
            return 0.0
        
        # Calculate word overlap
        matched_words = 0
        for query_word in query_words:
            if len(query_word) >= 3:  # Skip very short words
                for text_word in text_words:
                    if query_word in text_word or text_word in query_word:
                        matched_words += 1
                        break
        
        word_score = matched_words / len(query_words)
        
        # Boost score for longer matches
        if word_score > 0:
            # Check for phrase matches
            query_phrases = query_lower.split()
            for i in range(len(query_phrases)):
                for j in range(i + 2, len(query_phrases) + 1):
                    phrase = " ".join(query_phrases[i:j])
                    if phrase in text_lower:
                        word_score = min(word_score + 0.2, 1.0)
        
        return word_score
    
    def filter_by_recency(
        self,
        entries: List[ContextEntry],
        days: int = 30,
    ) -> List[ContextEntry]:
        """
        Filter context entries by recency.
        
        Args:
            entries: List of context entries to filter
            days: Number of days to consider recent
            
        Returns:
            Filtered list of recent entries
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        recent_entries = []
        for entry in entries:
            if entry.created_at and entry.created_at.replace(tzinfo=None) >= cutoff_date:
                recent_entries.append(entry)
        
        return recent_entries
    
    def deduplicate_context(
        self,
        entries: List[ContextEntry],
        similarity_threshold: float = 0.8,
    ) -> List[ContextEntry]:
        """
        Remove duplicate or very similar context entries.
        
        Args:
            entries: List of context entries to deduplicate
            similarity_threshold: Similarity threshold for deduplication
            
        Returns:
            Deduplicated list of entries
        """
        if not entries:
            return []
        
        deduplicated = []
        
        for entry in entries:
            is_duplicate = False
            
            for existing in deduplicated:
                # Check for exact content match
                if entry.content.strip() == existing.content.strip():
                    is_duplicate = True
                    break
                
                # Check for high similarity (simple approach)
                similarity = self._calculate_content_similarity(entry.content, existing.content)
                if similarity >= similarity_threshold:
                    # Keep the more recent or more accessed entry
                    if (entry.created_at and existing.created_at and 
                        entry.created_at > existing.created_at) or \
                       (entry.access_count or 0) > (existing.access_count or 0):
                        # Replace existing with current entry
                        deduplicated.remove(existing)
                        deduplicated.append(entry)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(entry)
        
        return deduplicated
    
    def _calculate_content_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings.
        
        This is a simple implementation. In production, you might use
        more sophisticated similarity measures or embeddings.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def get_context_for_prompt(
        self,
        model_id: str,
        user_prompt: str,
        max_context_length: Optional[int] = None,
        context_template: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get formatted context for injection into a prompt.
        
        Args:
            model_id: The AI model requesting context
            user_prompt: The user's prompt/query
            max_context_length: Maximum character length for context
            context_template: Template for formatting context
            
        Returns:
            Dictionary with formatted context and metadata
        """
        if max_context_length is None:
            max_context_length = settings.max_context_length
        
        try:
            # Get relevant context
            entries, metadata = self.get_relevant_context(
                model_id=model_id,
                query_context=user_prompt,
                limit=settings.max_context_entries,
            )
            
            if not entries:
                return {
                    "formatted_context": "",
                    "context_entries": [],
                    "metadata": metadata,
                    "total_length": 0,
                }
            
            # Format context entries
            formatted_entries = []
            total_length = 0
            
            for entry in entries:
                # Format individual entry
                entry_text = self._format_context_entry(entry)
                
                # Check if adding this entry would exceed length limit
                if total_length + len(entry_text) > max_context_length:
                    break
                
                formatted_entries.append(entry_text)
                total_length += len(entry_text)
            
            # Apply context template
            if context_template is None:
                from ..config import get_context_template
                context_template = get_context_template()
            
            formatted_context = context_template.format(
                context_entries="\n\n".join(formatted_entries),
                user_prompt=user_prompt,
            )
            
            return {
                "formatted_context": formatted_context,
                "context_entries": [entry.to_dict(include_metadata=False) for entry in entries[:len(formatted_entries)]],
                "metadata": {
                    **metadata,
                    "entries_used": len(formatted_entries),
                    "total_context_length": total_length,
                    "template_used": True,
                },
                "total_length": len(formatted_context),
            }
            
        except Exception as e:
            logger.error(f"Error formatting context for prompt for model {model_id}: {str(e)}", exc_info=True)
            return {
                "formatted_context": "",
                "context_entries": [],
                "metadata": {"error": str(e)},
                "total_length": 0,
            }
    
    def _get_graph_rag_context(
        self,
        query: str,
        limit: int = 10
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get context from Graph RAG.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            Tuple of (graph_results, metadata)
        """
        if not self.use_graph_rag or not self.graph_rag_db:
            return [], {"graph_rag_used": False, "reason": "not_available"}

        try:
            logger.info(f"Querying Graph RAG for: {query[:50]}...")

            results = self.graph_rag_db.search(
                query=query,
                limit=limit,
                use_graph=True,
                min_relevance=0.3
            )

            logger.info(f"Graph RAG returned {len(results)} results")

            return results, {
                "graph_rag_used": True,
                "total_results": len(results),
                "search_method": "hybrid_graph_vector"
            }

        except Exception as e:
            logger.error(f"Graph RAG search failed: {e}", exc_info=True)
            return [], {"graph_rag_used": False, "error": str(e)}

    def _convert_graph_results_to_entries(
        self,
        graph_results: List[Dict[str, Any]]
    ) -> List[ContextEntry]:
        """
        Convert Graph RAG search results to ContextEntry objects.

        Args:
            graph_results: List of Graph RAG result dictionaries

        Returns:
            List of ContextEntry objects
        """
        entries = []

        for result in graph_results:
            try:
                # Extract fields from Graph RAG result
                content = result.get('content', '')
                document_id = result.get('document_id', '')
                metadata = result.get('metadata', {})
                relevance_score = result.get('relevance_score', 0.0)

                # Try to find existing entry in database by document_id or content
                existing_entry = None
                if document_id:
                    # Try to find by source (we'll use document_id as source)
                    with get_db_context() as db:
                        existing_entry = db.query(ContextEntry).filter(
                            ContextEntry.source == f"graph_rag:{document_id}"
                        ).first()

                if existing_entry:
                    # Use existing entry
                    existing_entry.relevance_score = relevance_score
                    entries.append(existing_entry)
                else:
                    # Create a temporary ContextEntry object
                    # Note: These won't be persisted to the DB automatically
                    entry = ContextEntry(
                        content=content,
                        context_type=ContextType.NOTE,  # Default to NOTE
                        source=f"graph_rag:{document_id}",
                        tags=metadata.get('tags', []) if isinstance(metadata.get('tags'), list) else [],
                        relevance_score=relevance_score
                    )

                    # Add graph-specific metadata
                    if result.get('matched_entity'):
                        entry.metadata_ = {
                            'matched_entity': result['matched_entity'],
                            'entity_type': result.get('entity_type'),
                            'search_type': result.get('search_type'),
                            'related_entities': result.get('related_entities', [])
                        }

                    entries.append(entry)

            except Exception as e:
                logger.warning(f"Failed to convert Graph RAG result to ContextEntry: {e}")
                continue

        return entries

    def _format_context_entry(self, entry: ContextEntry) -> str:
        """
        Format a single context entry for inclusion in prompts.

        Args:
            entry: The context entry to format

        Returns:
            Formatted string representation
        """
        # Basic formatting based on context type
        if entry.context_type == ContextType.PREFERENCE:
            prefix = "Preference:"
        elif entry.context_type == ContextType.NOTE:
            prefix = "Note:"
        elif entry.context_type == ContextType.FILE:
            prefix = f"File ({entry.source}):" if entry.source else "File:"
        elif entry.context_type == ContextType.EVENT:
            prefix = "Event:"
        else:
            prefix = "Context:"

        # Add tags if present
        tag_suffix = ""
        if entry.tags:
            tag_suffix = f" [Tags: {', '.join(entry.tags)}]"

        return f"{prefix} {entry.content}{tag_suffix}"


# Global context retrieval service instance
context_retrieval_service = ContextRetrievalService()
