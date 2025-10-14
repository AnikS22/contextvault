"""Document ingestion pipeline for processing and storing documents in vector database."""

import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
import hashlib

logger = logging.getLogger(__name__)


class DocumentChunker:
    """Intelligent document chunking with semantic awareness."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100
    ):
        """
        Initialize document chunker.

        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks for continuity
            min_chunk_size: Minimum chunk size (discard smaller chunks)
        """
        self.chunk_size = max(100, chunk_size)  # Minimum 100 chars
        self.chunk_overlap = max(0, min(chunk_overlap, chunk_size // 2))  # Max 50% overlap
        self.min_chunk_size = max(50, min_chunk_size)

    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk text into overlapping segments.

        Uses semantic boundaries (paragraphs, sentences) when possible.

        Args:
            text: Text to chunk
            metadata: Metadata to attach to each chunk

        Returns:
            List of chunk dicts with content and metadata
        """
        if not text or len(text) < self.min_chunk_size:
            return []

        metadata = metadata or {}
        chunks = []

        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        current_chunk = ""
        chunk_index = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If adding this paragraph exceeds chunk size, save current chunk
            if len(current_chunk) + len(para) > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(self._create_chunk(
                    current_chunk,
                    chunk_index,
                    metadata
                ))
                chunk_index += 1

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + para
            else:
                # Add to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        # Save final chunk
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(self._create_chunk(
                current_chunk,
                chunk_index,
                metadata
            ))

        return chunks

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize metadata to ensure compatibility with vector databases.

        ChromaDB only accepts str, int, float, or bool values.
        Converts lists/dicts to strings.

        Args:
            metadata: Raw metadata dict

        Returns:
            Sanitized metadata dict
        """
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                sanitized[key] = value
            elif isinstance(value, list):
                # Convert list to comma-separated string
                sanitized[key] = ", ".join(str(v) for v in value)
            elif isinstance(value, dict):
                # Convert dict to JSON string
                import json
                sanitized[key] = json.dumps(value)
            else:
                # Convert other types to string
                sanitized[key] = str(value)

        return sanitized

    def _create_chunk(
        self,
        content: str,
        index: int,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create chunk dict with metadata."""
        chunk_metadata = self._sanitize_metadata(metadata.copy())
        chunk_metadata.update({
            "chunk_index": index,
            "chunk_length": len(content),
            "created_at": datetime.utcnow().isoformat(),
        })

        return {
            "id": str(uuid4()),
            "content": content.strip(),
            "metadata": chunk_metadata
        }

    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from end of current chunk."""
        if len(text) <= self.chunk_overlap:
            return text + " "

        # Try to get complete sentences for overlap
        overlap_start = len(text) - self.chunk_overlap
        overlap_text = text[overlap_start:]

        # Find sentence boundary
        sentence_end = overlap_text.find('. ')
        if sentence_end > 0:
            overlap_text = overlap_text[sentence_end + 2:]

        return overlap_text + " " if overlap_text else ""


class DocumentReader:
    """Read documents from various file formats."""

    def __init__(self):
        """Initialize document reader."""
        self._pdf_available = self._check_pdf_support()
        self._docx_available = self._check_docx_support()

    def _check_pdf_support(self) -> bool:
        """Check if PDF reading is available."""
        try:
            import PyPDF2
            return True
        except ImportError:
            try:
                import pdfplumber
                return True
            except ImportError:
                logger.warning("PDF support not available. Install PyPDF2 or pdfplumber")
                return False

    def _check_docx_support(self) -> bool:
        """Check if DOCX reading is available."""
        try:
            import docx
            return True
        except ImportError:
            logger.warning("DOCX support not available. Install python-docx")
            return False

    def read_file(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Read file and extract text content.

        Args:
            file_path: Path to file

        Returns:
            Tuple of (text_content, metadata)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_path = Path(file_path)
        mime_type, _ = mimetypes.guess_type(str(file_path))

        # Extract file metadata
        stat = file_path.stat()
        metadata = {
            "filename": file_path.name,
            "filepath": str(file_path.absolute()),
            "file_size": stat.st_size,
            "mime_type": mime_type or "unknown",
            "extension": file_path.suffix.lower(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

        # Read based on file type
        extension = file_path.suffix.lower()

        if extension == '.pdf':
            content = self._read_pdf(file_path)
        elif extension == '.docx':
            content = self._read_docx(file_path)
        elif extension in ['.txt', '.md', '.markdown', '.rst']:
            content = self._read_text(file_path)
        elif extension in ['.py', '.js', '.java', '.c', '.cpp', '.go', '.rs']:
            content = self._read_text(file_path)
            metadata["content_type"] = "code"
        else:
            # Try reading as text
            try:
                content = self._read_text(file_path)
            except Exception as e:
                logger.error(f"Unsupported file type {extension}: {e}")
                raise ValueError(f"Unsupported file type: {extension}")

        # Add content hash
        metadata["content_hash"] = hashlib.md5(content.encode()).hexdigest()

        return content, metadata

    def _read_text(self, file_path: Path) -> str:
        """Read plain text file."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def _read_pdf(self, file_path: Path) -> str:
        """Read PDF file."""
        if not self._pdf_available:
            raise ValueError("PDF support not available")

        try:
            import PyPDF2
            text = []
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text.append(page.extract_text())
            return "\n\n".join(text)
        except Exception as e:
            logger.warning(f"PyPDF2 failed, trying pdfplumber: {e}")
            try:
                import pdfplumber
                text = []
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text.append(page.extract_text() or "")
                return "\n\n".join(text)
            except Exception as e2:
                logger.error(f"Failed to read PDF: {e2}")
                raise

    def _read_docx(self, file_path: Path) -> str:
        """Read DOCX file."""
        if not self._docx_available:
            raise ValueError("DOCX support not available")

        try:
            import docx
            doc = docx.Document(file_path)
            text = []
            for para in doc.paragraphs:
                text.append(para.text)
            return "\n\n".join(text)
        except Exception as e:
            logger.error(f"Failed to read DOCX: {e}")
            raise


class DocumentIngestionPipeline:
    """
    Complete pipeline for ingesting documents into vector database.

    Handles:
    - File reading
    - Text chunking
    - Embedding generation
    - Vector database storage
    - Batch processing
    """

    def __init__(
        self,
        vector_db,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        batch_size: int = 50
    ):
        """
        Initialize ingestion pipeline.

        Args:
            vector_db: VectorDatabase instance
            chunk_size: Target chunk size
            chunk_overlap: Chunk overlap size
            batch_size: Batch size for vector DB operations
        """
        self.vector_db = vector_db
        self.reader = DocumentReader()
        self.chunker = DocumentChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.batch_size = batch_size

        logger.info(
            f"Initialized DocumentIngestionPipeline: "
            f"chunk_size={chunk_size}, batch_size={batch_size}"
        )

    def ingest_file(
        self,
        file_path: str,
        document_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, int, List[str]]:
        """
        Ingest a single file.

        Args:
            file_path: Path to file
            document_type: Document type (contract, email, report, etc.)
            metadata: Additional metadata

        Returns:
            Tuple of (successful_chunks, failed_chunks, chunk_ids)
        """
        try:
            # Read file
            content, file_metadata = self.reader.read_file(file_path)

            # Merge metadata
            combined_metadata = file_metadata.copy()
            if metadata:
                combined_metadata.update(metadata)
            if document_type:
                combined_metadata["document_type"] = document_type

            # Chunk document
            chunks = self.chunker.chunk_text(content, combined_metadata)

            if not chunks:
                logger.warning(f"No chunks created from {file_path}")
                return 0, 0, []

            # Store chunks in vector DB
            successful, failed = self.vector_db.add_documents_batch(
                chunks,
                batch_size=self.batch_size
            )

            chunk_ids = [chunk["id"] for chunk in chunks]

            logger.info(
                f"Ingested {file_path}: {successful}/{len(chunks)} chunks successful"
            )

            return successful, failed, chunk_ids

        except Exception as e:
            logger.error(f"Failed to ingest {file_path}: {e}")
            return 0, 1, []

    def ingest_directory(
        self,
        directory_path: str,
        recursive: bool = True,
        file_pattern: Optional[str] = None,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest all documents from a directory.

        Args:
            directory_path: Path to directory
            recursive: Recursively process subdirectories
            file_pattern: Glob pattern for file filtering (e.g., "*.pdf")
            document_type: Document type for all files

        Returns:
            Dictionary with ingestion statistics
        """
        directory = Path(directory_path)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        # Find files
        if recursive:
            if file_pattern:
                files = list(directory.rglob(file_pattern))
            else:
                files = [
                    f for f in directory.rglob("*")
                    if f.is_file() and not f.name.startswith('.')
                ]
        else:
            if file_pattern:
                files = list(directory.glob(file_pattern))
            else:
                files = [
                    f for f in directory.glob("*")
                    if f.is_file() and not f.name.startswith('.')
                ]

        logger.info(f"Found {len(files)} files in {directory_path}")

        # Process files
        total_files = len(files)
        successful_files = 0
        failed_files = 0
        total_chunks = 0
        failed_chunks = 0

        for i, file_path in enumerate(files, 1):
            logger.info(f"Processing file {i}/{total_files}: {file_path.name}")

            try:
                successful, failed, chunk_ids = self.ingest_file(
                    str(file_path),
                    document_type=document_type
                )

                if successful > 0:
                    successful_files += 1
                    total_chunks += successful
                else:
                    failed_files += 1

                failed_chunks += failed

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                failed_files += 1

        stats = {
            "directory": str(directory),
            "total_files": total_files,
            "successful_files": successful_files,
            "failed_files": failed_files,
            "total_chunks": total_chunks,
            "failed_chunks": failed_chunks,
            "success_rate": round(successful_files / total_files * 100, 2) if total_files > 0 else 0
        }

        logger.info(
            f"Directory ingestion complete: "
            f"{successful_files}/{total_files} files, "
            f"{total_chunks} chunks stored"
        )

        return stats

    def ingest_text(
        self,
        text: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, int, List[str]]:
        """
        Ingest raw text directly.

        Args:
            text: Text content
            document_id: Document identifier
            metadata: Document metadata

        Returns:
            Tuple of (successful_chunks, failed_chunks, chunk_ids)
        """
        # Create metadata
        doc_metadata = metadata or {}
        doc_metadata.update({
            "source": "direct_text",
            "ingested_at": datetime.utcnow().isoformat(),
        })

        if document_id:
            doc_metadata["document_id"] = document_id

        # Chunk text
        chunks = self.chunker.chunk_text(text, doc_metadata)

        if not chunks:
            logger.warning("No chunks created from text")
            return 0, 0, []

        # Store in vector DB
        successful, failed = self.vector_db.add_documents_batch(
            chunks,
            batch_size=self.batch_size
        )

        chunk_ids = [chunk["id"] for chunk in chunks]

        logger.info(f"Ingested text: {successful}/{len(chunks)} chunks successful")

        return successful, failed, chunk_ids

    def ingest_batch(
        self,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Ingest a batch of mixed items (files and text).

        Args:
            items: List of dicts with keys:
                - type: "file" or "text"
                - path: File path (for type="file")
                - content: Text content (for type="text")
                - document_type: Document type (optional)
                - metadata: Additional metadata (optional)

        Returns:
            Dictionary with batch ingestion statistics
        """
        total_items = len(items)
        successful_items = 0
        failed_items = 0
        total_chunks = 0
        failed_chunks = 0

        for i, item in enumerate(items, 1):
            item_type = item.get("type", "file")

            try:
                if item_type == "file":
                    successful, failed, chunk_ids = self.ingest_file(
                        item["path"],
                        document_type=item.get("document_type"),
                        metadata=item.get("metadata")
                    )
                elif item_type == "text":
                    successful, failed, chunk_ids = self.ingest_text(
                        item["content"],
                        document_id=item.get("document_id"),
                        metadata=item.get("metadata")
                    )
                else:
                    logger.error(f"Unknown item type: {item_type}")
                    failed_items += 1
                    continue

                if successful > 0:
                    successful_items += 1
                    total_chunks += successful
                else:
                    failed_items += 1

                failed_chunks += failed

            except Exception as e:
                logger.error(f"Error processing batch item {i}: {e}")
                failed_items += 1

        stats = {
            "total_items": total_items,
            "successful_items": successful_items,
            "failed_items": failed_items,
            "total_chunks": total_chunks,
            "failed_chunks": failed_chunks,
            "success_rate": round(successful_items / total_items * 100, 2) if total_items > 0 else 0
        }

        logger.info(
            f"Batch ingestion complete: "
            f"{successful_items}/{total_items} items, "
            f"{total_chunks} chunks stored"
        )

        return stats
