# app/tests/test_embedding_cache.py
"""
Unit tests for embedding cache functionality.
"""
import tempfile
import os
import numpy as np
import pytest
from app.rag.embedder import EmbeddingCache


class TestEmbeddingCache:
    """Tests for embedding cache."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.cache = EmbeddingCache(self.temp_db.name)

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_cache_initialization(self):
        """Test cache is initialized properly."""
        # Check that database was created
        assert os.path.exists(self.cache.db_path)

    def test_add_embeddings(self):
        """Test adding embeddings to cache."""
        doc_name = "test.md"
        chunks = ["chunk1", "chunk2", "chunk3"]
        vectors = [np.random.randn(384) for _ in chunks]

        added = self.cache.add_embeddings(doc_name, chunks, vectors)
        assert added == 3

    def test_get_all_vectors(self):
        """Test retrieving all vectors."""
        doc_name = "test.md"
        chunks = ["chunk1", "chunk2"]
        vectors = [np.random.randn(384) for _ in chunks]

        self.cache.add_embeddings(doc_name, chunks, vectors)

        all_vectors = self.cache.get_all_vectors()
        assert len(all_vectors) == 2

        # Check structure
        for embedding_id, vector in all_vectors:
            assert isinstance(embedding_id, str)
            assert isinstance(vector, np.ndarray)
            assert vector.shape == (384,)

    def test_vector_serialization(self):
        """Test vector to blob conversion and back."""
        vector = np.random.randn(384)
        blob = self.cache._vector_to_blob(vector)
        recovered = self.cache._blob_to_vector(blob)

        np.testing.assert_array_almost_equal(vector, recovered)

    def test_get_all_metadata(self):
        """Test retrieving all metadata."""
        chunks_data = [
            ("doc1.md", ["chunk1", "chunk2"]),
            ("doc2.md", ["chunk3"]),
        ]

        for doc_name, chunks in chunks_data:
            vectors = [np.random.randn(384) for _ in chunks]
            self.cache.add_embeddings(doc_name, chunks, vectors)

        metadata = self.cache.get_all_metadata()
        assert len(metadata) == 3

        # Check structure
        for embedding_id, doc_name, chunk_index, chunk_text in metadata:
            assert isinstance(embedding_id, str)
            assert isinstance(doc_name, str)
            assert isinstance(chunk_index, int)
            assert isinstance(chunk_text, str)

    def test_delete_document(self):
        """Test deleting a document from cache."""
        doc_name = "test.md"
        chunks = ["chunk1", "chunk2"]
        vectors = [np.random.randn(384) for _ in chunks]

        self.cache.add_embeddings(doc_name, chunks, vectors)
        metadata_before = self.cache.get_all_metadata()
        assert len(metadata_before) == 2

        deleted = self.cache.delete_doc(doc_name)
        assert deleted == 2

        metadata_after = self.cache.get_all_metadata()
        assert len(metadata_after) == 0

    def test_clear_all(self):
        """Test clearing all embeddings."""
        for i in range(3):
            doc_name = f"doc{i}.md"
            chunks = ["chunk1", "chunk2"]
            vectors = [np.random.randn(384) for _ in chunks]
            self.cache.add_embeddings(doc_name, chunks, vectors)

        all_vectors = self.cache.get_all_vectors()
        assert len(all_vectors) == 6

        self.cache.clear_all()

        all_vectors = self.cache.get_all_vectors()
        assert len(all_vectors) == 0

    def test_duplicate_embedding_prevention(self):
        """Test that duplicate embeddings are not added."""
        doc_name = "test.md"
        chunks = ["chunk1", "chunk2"]
        vectors = [np.random.randn(384) for _ in chunks]

        added_first = self.cache.add_embeddings(doc_name, chunks, vectors)
        added_second = self.cache.add_embeddings(doc_name, chunks, vectors)

        assert added_first == 2
        assert added_second == 0  # No new embeddings added

    def test_find_chunk_by_index(self):
        """Test finding chunk by global index."""
        chunks_data = [("doc1.md", ["chunk1", "chunk2"]), ("doc2.md", ["chunk3"])]

        for doc_name, chunks in chunks_data:
            vectors = [np.random.randn(384) for _ in chunks]
            self.cache.add_embeddings(doc_name, chunks, vectors)

        # Find first chunk (index 0 -> ROWID 1)
        result = self.cache.find_chunk_by_index(0)
        assert result is not None
        doc_name, chunk_text, chunk_index = result
        assert chunk_text == "chunk1"
