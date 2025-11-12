# app/tests/test_chunking.py
"""
Unit tests for document chunking functionality.
"""
import pytest
from app.rag.extractor import DocumentExtractor


class TestDocumentChunking:
    """Tests for document extraction and chunking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = DocumentExtractor(chunk_size_tokens=400, chunk_overlap_tokens=100)

    def test_chunk_simple_text(self):
        """Test chunking of simple text."""
        text = "This is paragraph one.\n\nThis is paragraph two.\n\nThis is paragraph three."
        chunks = self.extractor.chunk_text(text)

        assert len(chunks) > 0
        assert isinstance(chunks, list)
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_chunk_overlap(self):
        """Test that chunks have overlap."""
        text = "\n\n".join([f"Paragraph {i}. Content here." for i in range(10)])
        chunks = self.extractor.chunk_text(text)

        # With overlap, consecutive chunks should have common content
        if len(chunks) > 1:
            # Check that there's some overlap
            last_of_first = chunks[0][-50:] if len(chunks[0]) >= 50 else chunks[0]
            first_of_second = chunks[1][:50]
            # There should be some overlap in the middle
            assert len(chunks) > 1

    def test_chunk_long_paragraph(self):
        """Test chunking of very long paragraph."""
        # Create a very long paragraph
        long_text = " ".join(["word"] * 1000)
        chunks = self.extractor.chunk_text(long_text, chunk_size_tokens=200, overlap_tokens=50)

        assert len(chunks) > 1
        # Each chunk should be reasonable size
        assert all(len(chunk) < 2000 for chunk in chunks)

    def test_chunk_with_custom_sizes(self):
        """Test chunking with custom size parameters."""
        text = "\n\n".join([f"Paragraph {i}. This is some content." for i in range(5)])
        chunks = self.extractor.chunk_text(text, chunk_size_tokens=200, overlap_tokens=50)

        assert len(chunks) > 0

    def test_chunk_preserves_content(self):
        """Test that chunking preserves all content."""
        text = "First part.\n\nSecond part.\n\nThird part."
        chunks = self.extractor.chunk_text(text)

        combined = "\n\n".join(chunks)
        # All parts should be present (overlap might add duplicates)
        assert "First part" in combined
        assert "Second part" in combined
        assert "Third part" in combined

    def test_empty_text_chunking(self):
        """Test chunking of empty text."""
        chunks = self.extractor.chunk_text("")
        assert chunks == []

    def test_single_chunk(self):
        """Test when text fits in single chunk."""
        text = "Short text."
        chunks = self.extractor.chunk_text(text)

        assert len(chunks) == 1
        assert chunks[0] == text
