"""Vector database service for unlimited document storage and semantic search."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


class VectorDatabase:
    """
    Vector database service using ChromaDB for unlimited document storage.

    Features:
    - Persistent local storage (no cloud dependencies)
    - Fast semantic search over 100K+ documents
    - Metadata filtering and hybrid search
    - Integration with existing embedding models
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: str = "contextvault_documents",
        embedding_function=None,
    ):
        """
        Initialize vector database.

        Args:
            persist_directory: Where to store the database (defaults to ./contextvault/storage/chroma)
            collection_name: Name of the collection
            embedding_function: Custom embedding function (optional, uses default if not provided)
        """
        self.persist_directory = persist_directory or self._get_default_directory()
        self.collection_name = collection_name
        self._client = None
        self._collection = None
        self._embedding_function = embedding_function
        self._chroma_available = self._check_chromadb()

        if self._chroma_available:
            self._initialize_client()

    def _get_default_directory(self) -> str:
        """Get default storage directory."""
        # Use project root storage directory
        current_dir = Path(__file__).parent
        storage_dir = current_dir / "chroma"
        storage_dir.mkdir(parents=True, exist_ok=True)
        return str(storage_dir)

    def _check_chromadb(self) -> bool:
        """Check if ChromaDB is available."""
        try:
            import chromadb
            return True
        except ImportError:
            logger.error(
                "ChromaDB not installed. Install with: pip install chromadb"
            )
            return False

    def _initialize_client(self):
        """Initialize ChromaDB client and collection."""
        try:
            import chromadb
            from chromadb.config import Settings

            # Create persistent client
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )

            # Get or create collection
            # Use default embedding function if none provided
            if self._embedding_function:
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    embedding_function=self._embedding_function,
                    metadata={"description": "ContextVault document storage"}
                )
            else:
                # Use ChromaDB's default embedding function
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"description": "ContextVault document storage"}
                )

            logger.info(
                f"Initialized ChromaDB collection '{self.collection_name}' "
                f"at {self.persist_directory}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self._chroma_available = False

    def is_available(self) -> bool:
        """Check if vector database is available."""
        return self._chroma_available and self._collection is not None

    def add_document(
        self,
        document_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> bool:
        """
        Add a single document to the vector database.

        Args:
            document_id: Unique document identifier
            content: Document content (text)
            metadata: Document metadata (type, tags, source, etc.)
            embedding: Pre-computed embedding (optional, will be generated if not provided)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.error("Vector database not available")
            return False

        try:
            # Prepare metadata
            doc_metadata = metadata or {}
            doc_metadata["added_at"] = datetime.utcnow().isoformat()

            # Add to collection
            if embedding:
                # Use pre-computed embedding
                self._collection.add(
                    ids=[document_id],
                    documents=[content],
                    metadatas=[doc_metadata],
                    embeddings=[embedding]
                )
            else:
                # Let ChromaDB generate embedding
                self._collection.add(
                    ids=[document_id],
                    documents=[content],
                    metadatas=[doc_metadata]
                )

            logger.debug(f"Added document {document_id} to vector database")
            return True

        except Exception as e:
            logger.error(f"Failed to add document {document_id}: {e}")
            return False

    def add_documents_batch(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> Tuple[int, int]:
        """
        Add multiple documents in batches.

        Args:
            documents: List of document dicts with keys: id, content, metadata, embedding (optional)
            batch_size: Number of documents per batch

        Returns:
            Tuple of (successful_count, failed_count)
        """
        if not self.is_available():
            logger.error("Vector database not available")
            return 0, len(documents)

        successful = 0
        failed = 0

        try:
            # Process in batches
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]

                ids = []
                contents = []
                metadatas = []
                embeddings = []
                has_embeddings = False

                for doc in batch:
                    ids.append(doc["id"])
                    contents.append(doc["content"])

                    # Add timestamp to metadata
                    metadata = doc.get("metadata", {})
                    metadata["added_at"] = datetime.utcnow().isoformat()
                    metadatas.append(metadata)

                    # Collect embeddings if provided
                    if "embedding" in doc and doc["embedding"]:
                        embeddings.append(doc["embedding"])
                        has_embeddings = True

                # Add batch to collection
                try:
                    if has_embeddings and len(embeddings) == len(ids):
                        self._collection.add(
                            ids=ids,
                            documents=contents,
                            metadatas=metadatas,
                            embeddings=embeddings
                        )
                    else:
                        self._collection.add(
                            ids=ids,
                            documents=contents,
                            metadatas=metadatas
                        )

                    successful += len(batch)
                    logger.info(f"Added batch of {len(batch)} documents")

                except Exception as e:
                    logger.error(f"Failed to add batch: {e}")
                    failed += len(batch)

            logger.info(f"Batch ingestion complete: {successful} successful, {failed} failed")
            return successful, failed

        except Exception as e:
            logger.error(f"Batch ingestion error: {e}")
            return successful, len(documents) - successful

    def search(
        self,
        query: str,
        n_results: int = 20,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for documents.

        Args:
            query: Search query
            n_results: Maximum number of results
            where: Metadata filter (e.g., {"type": "contract"})
            where_document: Document content filter

        Returns:
            List of document results with content, metadata, and similarity scores
        """
        if not self.is_available():
            logger.error("Vector database not available")
            return []

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                where_document=where_document
            )

            # Format results
            documents = []
            if results["ids"] and len(results["ids"]) > 0:
                for i, doc_id in enumerate(results["ids"][0]):
                    documents.append({
                        "id": doc_id,
                        "content": results["documents"][0][i] if results["documents"] else None,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else None,
                    })

            logger.debug(f"Search returned {len(documents)} results for query: {query[:50]}...")
            return documents

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific document by ID.

        Args:
            document_id: Document identifier

        Returns:
            Document dict or None if not found
        """
        if not self.is_available():
            return None

        try:
            results = self._collection.get(ids=[document_id])

            if results["ids"] and len(results["ids"]) > 0:
                return {
                    "id": results["ids"][0],
                    "content": results["documents"][0] if results["documents"] else None,
                    "metadata": results["metadatas"][0] if results["metadatas"] else {},
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return None

    def update_document(
        self,
        document_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> bool:
        """
        Update an existing document.

        Args:
            document_id: Document identifier
            content: New content (optional)
            metadata: New metadata (optional)
            embedding: New embedding (optional)

        Returns:
            True if successful
        """
        if not self.is_available():
            return False

        try:
            # Update metadata with timestamp
            if metadata:
                metadata["updated_at"] = datetime.utcnow().isoformat()

            # Build update params
            update_params = {"ids": [document_id]}

            if content:
                update_params["documents"] = [content]
            if metadata:
                update_params["metadatas"] = [metadata]
            if embedding:
                update_params["embeddings"] = [embedding]

            self._collection.update(**update_params)
            logger.debug(f"Updated document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update document {document_id}: {e}")
            return False

    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document.

        Args:
            document_id: Document identifier

        Returns:
            True if successful
        """
        if not self.is_available():
            return False

        try:
            self._collection.delete(ids=[document_id])
            logger.debug(f"Deleted document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False

    def delete_documents_batch(self, document_ids: List[str]) -> Tuple[int, int]:
        """
        Delete multiple documents.

        Args:
            document_ids: List of document identifiers

        Returns:
            Tuple of (successful_count, failed_count)
        """
        if not self.is_available():
            return 0, len(document_ids)

        try:
            self._collection.delete(ids=document_ids)
            logger.info(f"Deleted {len(document_ids)} documents")
            return len(document_ids), 0

        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return 0, len(document_ids)

    def count_documents(self, where: Optional[Dict[str, Any]] = None) -> int:
        """
        Count documents in the collection.

        Args:
            where: Optional metadata filter

        Returns:
            Number of documents
        """
        if not self.is_available():
            return 0

        try:
            if where:
                # Count with filter
                results = self._collection.get(where=where)
                return len(results["ids"]) if results["ids"] else 0
            else:
                # Count all
                return self._collection.count()

        except Exception as e:
            logger.error(f"Failed to count documents: {e}")
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Statistics dict with counts, storage info, etc.
        """
        if not self.is_available():
            return {
                "available": False,
                "error": "Vector database not available"
            }

        try:
            total_docs = self.count_documents()

            # Calculate storage size
            storage_size = 0
            if os.path.exists(self.persist_directory):
                for dirpath, dirnames, filenames in os.walk(self.persist_directory):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        storage_size += os.path.getsize(filepath)

            return {
                "available": True,
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory,
                "total_documents": total_docs,
                "storage_size_bytes": storage_size,
                "storage_size_mb": round(storage_size / (1024 * 1024), 2),
            }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "available": True,
                "error": str(e)
            }

    def clear_collection(self) -> bool:
        """
        Clear all documents from the collection (dangerous!).

        Returns:
            True if successful
        """
        if not self.is_available():
            return False

        try:
            # Get all IDs
            results = self._collection.get()
            if results["ids"]:
                self._collection.delete(ids=results["ids"])

            logger.warning(f"Cleared all documents from collection '{self.collection_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False

    def reset_collection(self) -> bool:
        """
        Delete and recreate the collection (dangerous!).

        Returns:
            True if successful
        """
        if not self._client:
            return False

        try:
            # Delete collection
            self._client.delete_collection(name=self.collection_name)
            logger.warning(f"Deleted collection '{self.collection_name}'")

            # Recreate
            self._initialize_client()
            logger.info(f"Recreated collection '{self.collection_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            return False


# Global vector database instance
vector_db = VectorDatabase()
