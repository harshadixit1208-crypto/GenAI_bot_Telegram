# app/tests/test_faiss_retrieval.py
"""
Unit tests for FAISS vector store and retrieval.
"""
import tempfile
import os
import numpy as np
import pytest
from app.rag.vector_store import FAISSVectorStore


class TestFAISSVectorStore:
    """Tests for FAISS vector store."""

    def setup_method(self):
        """Set up test fixtures."""
        self.embedding_dim = 384
        self.vector_store = FAISSVectorStore(embedding_dim=self.embedding_dim)

    def test_vector_store_initialization(self):
        """Test vector store is initialized properly."""
        assert self.vector_store.index.ntotal == 0
        assert len(self.vector_store.metadata) == 0

    def test_add_vectors(self):
        """Test adding vectors to store."""
        vectors = [np.random.randn(self.embedding_dim) for _ in range(3)]
        metadata = [
            ("doc1.md", 0, "chunk1"),
            ("doc1.md", 1, "chunk2"),
            ("doc2.md", 0, "chunk3"),
        ]
        ids = ["id1", "id2", "id3"]

        self.vector_store.add_vectors(vectors, metadata, ids)

        assert self.vector_store.index.ntotal == 3
        assert len(self.vector_store.metadata) == 3

    def test_search_vectors(self):
        """Test searching for similar vectors."""
        # Add some vectors
        vectors = [
            np.array([1.0, 0.0, 0.0] + [0.0] * 381),  # Vector 1
            np.array([0.0, 1.0, 0.0] + [0.0] * 381),  # Vector 2
            np.array([0.0, 0.0, 1.0] + [0.0] * 381),  # Vector 3
        ]
        # Normalize
        vectors = [v / (np.linalg.norm(v) + 1e-9) for v in vectors]

        metadata = [
            ("doc1.md", 0, "chunk1"),
            ("doc1.md", 1, "chunk2"),
            ("doc2.md", 0, "chunk3"),
        ]
        ids = ["id1", "id2", "id3"]

        self.vector_store.add_vectors(vectors, metadata, ids)

        # Query with first vector
        query_vector = vectors[0]
        results = self.vector_store.search(query_vector, k=2)

        assert len(results) == 2
        # First result should be the query vector itself (distance ~1.0)
        index, score, doc_name, chunk_index, chunk_text = results[0]
        assert chunk_text == "chunk1"
        assert score > 0.9  # High similarity to itself

    def test_search_empty_store(self):
        """Test searching in empty store."""
        query_vector = np.random.randn(self.embedding_dim)
        results = self.vector_store.search(query_vector, k=3)

        assert len(results) == 0

    def test_reset_vector_store(self):
        """Test resetting vector store."""
        vectors = [np.random.randn(self.embedding_dim) for _ in range(3)]
        metadata = [("doc.md", i, f"chunk{i}") for i in range(3)]
        ids = [f"id{i}" for i in range(3)]

        self.vector_store.add_vectors(vectors, metadata, ids)
        assert self.vector_store.index.ntotal == 3

        self.vector_store.reset()

        assert self.vector_store.index.ntotal == 0
        assert len(self.vector_store.metadata) == 0

    def test_save_and_load_index(self):
        """Test saving and loading FAISS index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "test_index.bin")

            # Add vectors and save
            vectors = [np.random.randn(self.embedding_dim) for _ in range(3)]
            metadata = [("doc.md", i, f"chunk{i}") for i in range(3)]
            ids = [f"id{i}" for i in range(3)]

            self.vector_store.add_vectors(vectors, metadata, ids)
            self.vector_store.save(index_path)

            assert os.path.exists(index_path)

            # Create new store and load
            new_store = FAISSVectorStore(embedding_dim=self.embedding_dim, index_path=index_path)
            assert new_store.index.ntotal == 3

    def test_get_stats(self):
        """Test getting vector store statistics."""
        vectors = [np.random.randn(self.embedding_dim) for _ in range(2)]
        metadata = [("doc.md", i, f"chunk{i}") for i in range(2)]
        ids = [f"id{i}" for i in range(2)]

        self.vector_store.add_vectors(vectors, metadata, ids)

        stats = self.vector_store.get_stats()

        assert stats["total_vectors"] == 2
        assert stats["embedding_dim"] == self.embedding_dim
        assert stats["metadata_count"] == 2

    def test_cosine_similarity(self):
        """Test that FAISS uses cosine similarity (normalized vectors)."""
        # Create orthogonal vectors
        v1 = np.array([1.0, 0.0] + [0.0] * 382)
        v2 = np.array([0.0, 1.0] + [0.0] * 382)
        v3 = np.array([1.0, 0.0] + [0.0] * 382)  # Same as v1

        # Normalize
        vectors = [v / (np.linalg.norm(v) + 1e-9) for v in [v1, v2, v3]]

        metadata = [("doc.md", i, f"chunk{i}") for i in range(3)]
        ids = [f"id{i}" for i in range(3)]

        self.vector_store.add_vectors(vectors, metadata, ids)

        # Query with v1
        query_vector = vectors[0]
        results = self.vector_store.search(query_vector, k=3)

        # v1 and v3 should have highest similarity, v2 should be different
        scores = [r[1] for r in results]
        assert scores[0] > scores[1]  # v1 similar to itself
