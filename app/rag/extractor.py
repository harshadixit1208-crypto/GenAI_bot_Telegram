# app/rag/extractor.py
"""
Document extraction and chunking.
Loads documents from files and performs semantic chunking with overlap.
"""
import re
from typing import List, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DocumentExtractor:
    """Extracts and chunks documents from files."""

    def __init__(self, chunk_size_tokens: int = 400, chunk_overlap_tokens: int = 100):
        """Initialize document extractor.

        Args:
            chunk_size_tokens: Target chunk size in tokens (approximate).
            chunk_overlap_tokens: Overlap between chunks in tokens.
        """
        self.chunk_size_tokens = chunk_size_tokens
        self.chunk_overlap_tokens = chunk_overlap_tokens

    def load_documents(self, data_dir: str = "data") -> List[Tuple[str, str]]:
        """Load all markdown and text files from a directory.

        Args:
            data_dir: Directory containing documents.

        Returns:
            List of (filename, content) tuples.
        """
        data_path = Path(data_dir)
        documents = []

        if not data_path.exists():
            logger.warning(f"Data directory {data_dir} does not exist")
            return documents

        for file_path in sorted(data_path.glob("*.md")) + sorted(data_path.glob("*.txt")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                documents.append((file_path.name, content))
                logger.info(f"Loaded document: {file_path.name}")
            except Exception as e:
                logger.error(f"Error loading {file_path.name}: {e}")

        return documents

    def chunk_text(
        self, text: str, chunk_size_tokens: int = None, overlap_tokens: int = None
    ) -> List[str]:
        """Split text into chunks with semantic awareness and overlap.

        Uses paragraph breaks as primary split points, then character-based fallback.
        Provides deterministic overlap.

        Args:
            text: Text to chunk.
            chunk_size_tokens: Target chunk size in tokens (uses instance default if None).
            overlap_tokens: Overlap in tokens (uses instance default if None).

        Returns:
            List of text chunks.
        """
        chunk_size_tokens = chunk_size_tokens or self.chunk_size_tokens
        overlap_tokens = overlap_tokens or self.chunk_overlap_tokens

        # Estimate: roughly 1 token per 4 characters (conservative)
        chunk_size_chars = chunk_size_tokens * 4
        overlap_chars = overlap_tokens * 4

        # Split on double newlines (paragraphs) first
        paragraphs = re.split(r"\n\n+", text.strip())

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If current chunk + para fits, add it
            if len(current_chunk) + len(para) + 1 <= chunk_size_chars:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                # Save current chunk if not empty
                if current_chunk:
                    chunks.append(current_chunk)

                # If para is longer than chunk_size, split it further
                if len(para) > chunk_size_chars:
                    # Character-based chunking for long paragraphs
                    sub_chunks = self._chunk_long_text(para, chunk_size_chars, overlap_chars)
                    chunks.extend(sub_chunks)
                else:
                    current_chunk = para

        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk)

        # Add overlap between chunks (deterministic)
        if len(chunks) > 1:
            overlapped_chunks = self._add_overlap(chunks, overlap_chars)
            return overlapped_chunks

        return chunks

    def _chunk_long_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split long text into fixed-size character chunks with overlap.

        Args:
            text: Text to chunk.
            chunk_size: Size of each chunk in characters.
            overlap: Overlap size in characters.

        Returns:
            List of overlapped chunks.
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)

            # Move start forward by (chunk_size - overlap)
            start += chunk_size - overlap

        return chunks

    def _add_overlap(self, chunks: List[str], overlap_chars: int) -> List[str]:
        """Add overlap between chunks deterministically.

        Args:
            chunks: List of chunks.
            overlap_chars: Number of characters to overlap.

        Returns:
            List of chunks with overlap appended.
        """
        if len(chunks) <= 1:
            return chunks

        result = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]

            # Add tail of previous chunk to current chunk
            overlap_tail = prev_chunk[-overlap_chars:] if len(prev_chunk) >= overlap_chars else prev_chunk
            overlapped = overlap_tail + "\n\n" + curr_chunk
            result.append(overlapped)

        return result

    def extract_and_chunk_documents(
        self, data_dir: str = "data"
    ) -> List[Tuple[str, int, str]]:
        """Load documents and chunk them.

        Args:
            data_dir: Directory containing documents.

        Returns:
            List of (doc_name, chunk_index, chunk_text) tuples.
        """
        documents = self.load_documents(data_dir)
        chunked = []

        for doc_name, content in documents:
            chunks = self.chunk_text(content)
            for chunk_idx, chunk in enumerate(chunks):
                chunked.append((doc_name, chunk_idx, chunk))
                logger.debug(f"Chunked {doc_name}: chunk {chunk_idx} ({len(chunk)} chars)")

        logger.info(f"Total chunks created: {len(chunked)}")
        return chunked
