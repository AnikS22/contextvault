"""Tests for document ingestion pipeline."""

import pytest
import tempfile
import os
from pathlib import Path

from contextvault.storage.document_ingestion import (
    DocumentChunker,
    DocumentReader,
    DocumentIngestionPipeline
)
from contextvault.storage.vector_db import VectorDatabase


class TestDocumentChunker:
    """Test document chunking."""

    def test_chunk_short_text(self):
        """Test chunking short text."""
        chunker = DocumentChunker(chunk_size=200, chunk_overlap=20, min_chunk_size=20)

        text = "This is a short text that should create one chunk."
        chunks = chunker.chunk_text(text)

        assert len(chunks) == 1
        assert chunks[0]["content"] == text

    def test_chunk_long_text(self):
        """Test chunking long text into multiple chunks."""
        chunker = DocumentChunker(chunk_size=200, chunk_overlap=50)

        # Create long text with paragraphs
        text = "\n\n".join([
            f"This is paragraph {i}. " * 10
            for i in range(10)
        ])

        chunks = chunker.chunk_text(text)

        assert len(chunks) > 1
        # Verify all chunks have content
        assert all(chunk["content"] for chunk in chunks)
        # Verify metadata
        assert all("chunk_index" in chunk["metadata"] for chunk in chunks)

    def test_chunk_with_metadata(self):
        """Test that metadata is preserved in chunks."""
        chunker = DocumentChunker(chunk_size=200)

        text = "Test content " * 50
        metadata = {"type": "test", "author": "tester"}

        chunks = chunker.chunk_text(text, metadata)

        # Verify metadata in all chunks
        for chunk in chunks:
            assert chunk["metadata"]["type"] == "test"
            assert chunk["metadata"]["author"] == "tester"
            assert "chunk_index" in chunk["metadata"]

    def test_min_chunk_size(self):
        """Test that chunks below minimum size are discarded."""
        chunker = DocumentChunker(chunk_size=100, min_chunk_size=50)

        text = "Short"  # Below minimum
        chunks = chunker.chunk_text(text)

        assert len(chunks) == 0


class TestDocumentReader:
    """Test document reader."""

    def test_read_text_file(self):
        """Test reading a text file."""
        reader = DocumentReader()

        # Create temp text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is test content for a text file.")
            temp_path = f.name

        try:
            content, metadata = reader.read_file(temp_path)

            assert "test content" in content
            assert metadata["filename"].endswith(".txt")
            assert metadata["extension"] == ".txt"
            assert "content_hash" in metadata

        finally:
            os.unlink(temp_path)

    def test_read_markdown_file(self):
        """Test reading a markdown file."""
        reader = DocumentReader()

        # Create temp markdown file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Heading\n\nThis is markdown content.\n\n- Item 1\n- Item 2")
            temp_path = f.name

        try:
            content, metadata = reader.read_file(temp_path)

            assert "# Heading" in content
            assert "markdown content" in content
            assert metadata["extension"] == ".md"

        finally:
            os.unlink(temp_path)

    def test_read_code_file(self):
        """Test reading a code file."""
        reader = DocumentReader()

        # Create temp Python file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test_function():\n    return 'Hello World'")
            temp_path = f.name

        try:
            content, metadata = reader.read_file(temp_path)

            assert "def test_function" in content
            assert metadata["extension"] == ".py"
            assert metadata.get("content_type") == "code"

        finally:
            os.unlink(temp_path)

    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for missing files."""
        reader = DocumentReader()

        with pytest.raises(FileNotFoundError):
            reader.read_file("/nonexistent/file.txt")


class TestDocumentIngestionPipeline:
    """Test document ingestion pipeline."""

    def test_pipeline_creation(self):
        """Test creating ingestion pipeline."""
        db = VectorDatabase(collection_name="test_ingestion_pipeline")

        if not db.is_available():
            pytest.skip("ChromaDB not available")

        pipeline = DocumentIngestionPipeline(
            vector_db=db,
            chunk_size=500,
            batch_size=10
        )

        assert pipeline is not None
        assert pipeline.batch_size == 10
        assert pipeline.chunker.chunk_size == 500

    def test_ingest_text(self):
        """Test ingesting raw text."""
        db = VectorDatabase(collection_name="test_ingest_text")

        if not db.is_available():
            pytest.skip("ChromaDB not available")

        db.clear_collection()

        pipeline = DocumentIngestionPipeline(db, chunk_size=200)

        text = "This is a test document. " * 50  # Create long text
        successful, failed, chunk_ids = pipeline.ingest_text(
            text,
            document_id="test-doc-1",
            metadata={"type": "test"}
        )

        assert successful > 0
        assert failed == 0
        assert len(chunk_ids) > 0

        # Verify chunks are searchable
        results = db.search("test document", n_results=5)
        assert len(results) > 0

    def test_ingest_file(self):
        """Test ingesting a file."""
        db = VectorDatabase(collection_name="test_ingest_file")

        if not db.is_available():
            pytest.skip("ChromaDB not available")

        db.clear_collection()

        pipeline = DocumentIngestionPipeline(db, chunk_size=200)

        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Business contract content. " * 100)
            temp_path = f.name

        try:
            successful, failed, chunk_ids = pipeline.ingest_file(
                temp_path,
                document_type="contract"
            )

            assert successful > 0
            assert failed == 0
            assert len(chunk_ids) > 0

            # Verify chunks are stored
            results = db.search("business contract", n_results=5)
            assert len(results) > 0

        finally:
            os.unlink(temp_path)

    def test_ingest_directory(self):
        """Test ingesting a directory of files."""
        db = VectorDatabase(collection_name="test_ingest_directory")

        if not db.is_available():
            pytest.skip("ChromaDB not available")

        db.clear_collection()

        pipeline = DocumentIngestionPipeline(db, chunk_size=200)

        # Create temp directory with files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple test files
            for i in range(5):
                file_path = Path(temp_dir) / f"document_{i}.txt"
                with open(file_path, 'w') as f:
                    f.write(f"Content for document {i}. " * 20)

            # Ingest directory
            stats = pipeline.ingest_directory(
                temp_dir,
                recursive=False,
                document_type="test_batch"
            )

            assert stats["total_files"] == 5
            assert stats["successful_files"] > 0
            assert stats["total_chunks"] > 0

    def test_ingest_batch_mixed(self):
        """Test ingesting a batch of mixed items."""
        db = VectorDatabase(collection_name="test_ingest_batch")

        if not db.is_available():
            pytest.skip("ChromaDB not available")

        db.clear_collection()

        pipeline = DocumentIngestionPipeline(db, chunk_size=200)

        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("File content " * 20)
            temp_path = f.name

        try:
            items = [
                {
                    "type": "text",
                    "content": "Direct text content " * 20,
                    "metadata": {"source": "direct"}
                },
                {
                    "type": "file",
                    "path": temp_path,
                    "document_type": "test"
                }
            ]

            stats = pipeline.ingest_batch(items)

            assert stats["total_items"] == 2
            assert stats["successful_items"] == 2
            assert stats["total_chunks"] > 0

        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
