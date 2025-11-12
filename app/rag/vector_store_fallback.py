# app/rag/vector_store_fallback.py
"""
Simple NumPy-based vector store fallback.
This implements the same minimal interface used by the FAISSVectorStore:
- add_vectors(vectors, metadata, ids)
- search(query_vector, k=3)
- rebuild_from_cache(embeddings, metadata)
- save(path) / load(path) (no-op or simple serialization)
- get_stats()
- reset()
"""

from __future__ import annotations
import numpy as np
from typing import List, Tuple, Optional
import os
import logging
import json

logger = logging.getLogger(__name__)


class NumpyVectorStore:
    """Lightweight in-memory vector store using NumPy (cosine similarity)."""

    def __init__(self, embedding_dim: int = 384, index_path: Optional[str] = None):
        self.embedding_dim = embedding_dim
        self.index_path = index_path
        self.vectors: Optional[np.ndarray] = None  # shape (N, D)
        self.metadata: List[Tuple[str, int, str]] = []  # (doc_name, chunk_index, chunk_text)
        self.embedding_ids: List[str] = []  # IDs from cache

        # Try to load saved index if available
        if index_path and os.path.exists(index_path):
            try:
                self.load(index_path)
            except Exception:
                logger.warning("Failed to load fallback index; starting empty store.")

    def add_vectors(
        self, vectors: List[np.ndarray], metadata: List[Tuple[str, int, str]], ids: List[str]
    ) -> None:
        """Add vectors with corresponding metadata and ids."""
        if len(vectors) != len(metadata) or len(vectors) != len(ids):
            raise ValueError("Vectors, metadata, and IDs length mismatch")

        vectors_array = np.vstack(vectors).astype(np.float32)
        # Normalize vectors for cosine similarity
        norms = np.linalg.norm(vectors_array, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vectors_array = vectors_array / norms

        if self.vectors is None:
            self.vectors = vectors_array
        else:
            self.vectors = np.vstack([self.vectors, vectors_array])

        self.metadata.extend(metadata)
        self.embedding_ids.extend(ids)

        logger.info(f"Added {len(vectors)} vectors to fallback store (total: {self.count()})")

    def search(self, query_vector: np.ndarray, k: int = 3) -> List[Tuple[int, float, str, int, str]]:
        """
        Search for similar vectors using cosine similarity.
        Returns list of (index, score, doc_name, chunk_index, chunk_text).
        """
        if self.vectors is None or self.vectors.shape[0] == 0:
            logger.warning("Fallback vector store is empty")
            return []

        q = np.asarray(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            q_norm = 1.0
        q = q / q_norm

        # vectors are normalized, so dot product is cosine similarity
        scores = (self.vectors @ q).squeeze()
        if scores.ndim == 0:
            scores = np.array([float(scores)])
        idx_sorted = np.argsort(-scores)[:k]

        results = []
        for idx in idx_sorted:
            score = float(scores[int(idx)])
            doc_name, chunk_index, chunk_text = self.metadata[int(idx)]
            results.append((int(idx), score, doc_name, int(chunk_index), chunk_text))
        return results

    def rebuild_from_cache(self, embeddings: List[Tuple[str, np.ndarray]], metadata: List[Tuple[str, str, int, str]]) -> None:
        """
        Rebuild index from cached embeddings/metadata.
        embeddings: list of (id, vector)
        metadata: list of (id, doc_name, chunk_index, chunk_text)
        """
        # Clear existing
        self.reset()

        if not embeddings:
            logger.info("No embeddings available to rebuild fallback store")
            return

        ids = [em[0] for em in embeddings]
        vectors = [em[1] for em in embeddings]

        # Build metadata map
        metadata_map = {row[0]: (row[1], row[2], row[3]) for row in metadata}

        # Add them
        metas_list = []
        for embedding_id, vec in zip(ids, vectors):
            if embedding_id in metadata_map:
                doc_name, chunk_index, chunk_text = metadata_map[embedding_id]
            else:
                doc_name, chunk_index, chunk_text = ("unknown", -1, "")
            metas_list.append((doc_name, chunk_index, chunk_text))

        self.add_vectors(vectors, metas_list, ids)

    def save(self, path: str) -> None:
        """Save minimal index (vectors and metadata) to disk as npz + json."""
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            base = os.path.splitext(path)[0]
            vec_path = base + "_vectors.npz"
            meta_path = base + "_meta.json"
            if self.vectors is not None:
                np.savez_compressed(vec_path, vectors=self.vectors)
            with open(meta_path, "w", encoding="utf-8") as fh:
                json.dump({"metadata": self.metadata, "ids": self.embedding_ids}, fh)
            logger.info(f"Saved fallback index to {vec_path} and {meta_path}")
        except Exception:
            logger.exception("Failed to save fallback index")

    def load(self, path: str) -> None:
        """Load saved vectors + metadata if present (expects same naming convention as save)."""
        base = os.path.splitext(path)[0]
        vec_path = base + "_vectors.npz"
        meta_path = base + "_meta.json"
        if os.path.exists(vec_path):
            arr = np.load(vec_path)
            self.vectors = arr["vectors"].astype(np.float32)
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                self.metadata = [tuple(x) for x in data.get("metadata", [])]
                self.embedding_ids = data.get("ids", [])

    def count(self) -> int:
        """Return the number of vectors in the store."""
        if self.vectors is None:
            return 0
        return self.vectors.shape[0]

    def get_stats(self) -> dict:
        return {
            "total_vectors": self.count(),
            "embedding_dim": self.embedding_dim,
            "metadata_count": len(self.metadata),
        }

    def reset(self) -> None:
        self.vectors = None
        self.metadata.clear()
        self.embedding_ids.clear()
        logger.info("Reset fallback vector store")
