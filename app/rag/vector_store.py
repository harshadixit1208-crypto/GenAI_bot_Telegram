# app/rag/vector_store.py
"""
FAISS-based vector store.
Manages FAISS index and metadata mapping for efficient similarity search.

Auto-detects faiss availability. If faiss is not installed, we alias
FAISSVectorStore to the NumPy fallback provided in
`app.rag.vector_store_fallback.NumpyVectorStore` so the rest of the codebase
can continue to import `FAISSVectorStore` unchanged.
"""
from __future__ import annotations

import logging
import os
from typing import List, Tuple, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Try to import faiss. If available, use the FAISS-backed implementation.
# If not, fall back to the numpy-based implementation in vector_store_fallback.py.
try:
    import faiss  # type: ignore

    HAS_FAISS = True
except Exception:
    faiss = None  # type: ignore
    HAS_FAISS = False


if HAS_FAISS:
    # --- FAISS-backed implementation (unchanged) ---
    class FAISSVectorStore:
        """FAISS-based vector store for similarity search."""

        def __init__(self, embedding_dim: int = 384, index_path: Optional[str] = None):
            """Initialize FAISS vector store.

            Args:
                embedding_dim: Dimension of embeddings (384 for all-MiniLM-L6-v2).
                index_path: Path to save/load FAISS index.
            """
            self.embedding_dim = embedding_dim
            self.index_path = index_path
            # Use IndexFlatIP (inner product) and ensure vectors are normalized before adding.
            self.index = faiss.IndexFlatIP(embedding_dim)  # type: ignore
            self.metadata: List[Tuple[str, int, str]] = []  # (doc_name, chunk_index, chunk_text)
            self.embedding_ids: List[str] = []  # IDs from cache

            if index_path and os.path.exists(index_path):
                try:
                    self.load(index_path)
                except Exception:
                    logger.exception("Failed to load FAISS index from path; starting with empty index.")

        def add_vectors(
            self, vectors: List[np.ndarray], metadata: List[Tuple[str, int, str]], ids: List[str]
        ) -> None:
            """Add vectors to index with metadata.

            Args:
                vectors: List of normalized embedding vectors.
                metadata: List of (doc_name, chunk_index, chunk_text) tuples.
                ids: List of embedding IDs from cache.
            """
            if len(vectors) != len(metadata) or len(vectors) != len(ids):
                raise ValueError("Vectors, metadata, and IDs length mismatch")

            # Stack vectors into matrix
            vectors_array = np.vstack(vectors).astype(np.float32)

            # Add to index
            self.index.add(vectors_array)
            self.metadata.extend(metadata)
            self.embedding_ids.extend(ids)

            logger.info(f"Added {len(vectors)} vectors to FAISS index (total: {self.index.ntotal})")

        def search(self, query_vector: np.ndarray, k: int = 3) -> List[Tuple[int, float, str, int, str]]:
            """Search for similar vectors.

            Args:
                query_vector: Query embedding vector (should be normalized).
                k: Number of results to return.

            Returns:
                List of (index, score, doc_name, chunk_index, chunk_text) tuples.
            """
            if self.index.ntotal == 0:
                logger.warning("FAISS index is empty")
                return []

            query_array = np.array([query_vector], dtype=np.float32)

            # FAISS returns distances and indices
            distances, indices = self.index.search(query_array, min(k, self.index.ntotal))

            results = []
            for i, (distance, index) in enumerate(zip(distances[0], indices[0])):
                if index == -1:  # Invalid result
                    continue

                doc_name, chunk_index, chunk_text = self.metadata[index]
                results.append((index, float(distance), doc_name, chunk_index, chunk_text))

            return results

        def rebuild_from_cache(self, embeddings: List[Tuple[str, np.ndarray]], metadata: List[Tuple[str, str, int, str]]) -> None:
            """Rebuild index from cache data.

            Args:
                embeddings: List of (id, vector) tuples from cache.
                metadata: List of (id, doc_name, chunk_index, chunk_text) tuples from cache.
            """
            # Clear existing index
            self.index.reset()
            self.metadata.clear()
            self.embedding_ids.clear()

            if not embeddings:
                logger.info("No embeddings to rebuild index")
                return

            # Extract vectors and IDs
            ids = [em[0] for em in embeddings]
            vectors = [em[1] for em in embeddings]

            # Build metadata lookup
            metadata_map = {row[0]: row[1:] for row in metadata}

            # Add vectors with corresponding metadata
            vectors_array = np.vstack(vectors).astype(np.float32)
            self.index.add(vectors_array)

            for embedding_id, vector in embeddings:
                if embedding_id in metadata_map:
                    doc_name, chunk_index, chunk_text = metadata_map[embedding_id]
                    self.metadata.append((doc_name, chunk_index, chunk_text))
                    self.embedding_ids.append(embedding_id)

            logger.info(f"Rebuilt FAISS index with {self.index.ntotal} vectors")

        def save(self, path: str) -> None:
            """Save FAISS index to disk.

            Args:
                path: Path to save index.
            """
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            faiss.write_index(self.index, path)  # type: ignore
            logger.info(f"Saved FAISS index to {path}")

        def load(self, path: str) -> None:
            """Load FAISS index from disk.

            Args:
                path: Path to load index.
            """
            if not os.path.exists(path):
                logger.warning(f"Index file not found: {path}")
                return

            self.index = faiss.read_index(path)  # type: ignore
            logger.info(f"Loaded FAISS index from {path} (ntotal: {self.index.ntotal})")

        def get_stats(self) -> dict:
            """Get index statistics.

            Returns:
                Dictionary with index stats.
            """
            return {
                "total_vectors": self.index.ntotal,
                "embedding_dim": self.embedding_dim,
                "metadata_count": len(self.metadata),
            }

        def reset(self) -> None:
            """Reset index and clear all data."""
            self.index.reset()
            self.metadata.clear()
            self.embedding_ids.clear()
            logger.info("Reset FAISS vector store")


else:
    # --- Faiss not available: use the full fallback implementation from file ---
    try:
        # Import the full fallback implementation you added earlier.
        from app.rag.vector_store_fallback import NumpyVectorStore  # type: ignore

        # Make the name FAISSVectorStore alias the fallback to keep external imports unchanged.
        FAISSVectorStore = NumpyVectorStore  # type: ignore
        logger.info("faiss not available — using NumPy fallback vector store (FAISSVectorStore -> NumpyVectorStore).")
    except Exception as e:
        # If import fails, raise a clear error so the developer can add the fallback file.
        logger.exception("Failed to import fallback vector store. Please ensure app/rag/vector_store_fallback.py exists.")
        raise ImportError("Missing fallback vector store (app.rag.vector_store_fallback)") from e




# # app/rag/vector_store.py
# """
# FAISS-based vector store.
# Manages FAISS index and metadata mapping for efficient similarity search.

# This module auto-detects whether `faiss` is available. If faiss is installed
# the FAISS-backed implementation is defined and used. If faiss is not available
# we fall back to a lightweight NumPy-based in-memory store by aliasing
# FAISSVectorStore to the fallback implementation.

# This keeps the rest of the codebase unchanged — other modules can continue to
# `from app.rag.vector_store import FAISSVectorStore` and get a working store.
# """
# from __future__ import annotations

# import logging
# import os
# from typing import List, Tuple, Optional

# import numpy as np

# logger = logging.getLogger(__name__)

# # Try to import faiss. If unavailable, set HAS_FAISS=False and we will alias
# # FAISSVectorStore to the NumPy fallback implementation at the bottom.
# try:
#     import faiss  # type: ignore

#     HAS_FAISS = True
# except Exception:
#     faiss = None  # type: ignore
#     HAS_FAISS = False


# if HAS_FAISS:

#     class FAISSVectorStore:
#         """FAISS-based vector store for similarity search."""

#         def __init__(self, embedding_dim: int = 384, index_path: Optional[str] = None):
#             """Initialize FAISS vector store.

#             Args:
#                 embedding_dim: Dimension of embeddings (384 for all-MiniLM-L6-v2).
#                 index_path: Path to save/load FAISS index.
#             """
#             self.embedding_dim = embedding_dim
#             self.index_path = index_path
#             # Use IndexFlatIP (inner product) and ensure vectors are normalized before adding.
#             self.index = faiss.IndexFlatIP(embedding_dim)  # type: ignore
#             self.metadata: List[Tuple[str, int, str]] = []  # (doc_name, chunk_index, chunk_text)
#             self.embedding_ids: List[str] = []  # IDs from cache

#             if index_path and os.path.exists(index_path):
#                 try:
#                     self.load(index_path)
#                 except Exception:
#                     logger.exception("Failed to load FAISS index from path; starting with empty index.")

#         def add_vectors(
#             self, vectors: List[np.ndarray], metadata: List[Tuple[str, int, str]], ids: List[str]
#         ) -> None:
#             """Add vectors to index with metadata.

#             Args:
#                 vectors: List of normalized embedding vectors.
#                 metadata: List of (doc_name, chunk_index, chunk_text) tuples.
#                 ids: List of embedding IDs from cache.
#             """
#             if len(vectors) != len(metadata) or len(vectors) != len(ids):
#                 raise ValueError("Vectors, metadata, and IDs length mismatch")

#             # Stack vectors into matrix
#             vectors_array = np.vstack(vectors).astype(np.float32)

#             # Add to index
#             self.index.add(vectors_array)
#             self.metadata.extend(metadata)
#             self.embedding_ids.extend(ids)

#             logger.info(f"Added {len(vectors)} vectors to FAISS index (total: {self.index.ntotal})")

#         def search(self, query_vector: np.ndarray, k: int = 3) -> List[Tuple[int, float, str, int, str]]:
#             """Search for similar vectors.

#             Args:
#                 query_vector: Query embedding vector (should be normalized).
#                 k: Number of results to return.

#             Returns:
#                 List of (index, score, doc_name, chunk_index, chunk_text) tuples.
#             """
#             if self.index.ntotal == 0:
#                 logger.warning("FAISS index is empty")
#                 return []

#             query_array = np.array([query_vector], dtype=np.float32)

#             # FAISS returns distances and indices
#             distances, indices = self.index.search(query_array, min(k, self.index.ntotal))

#             results = []
#             for i, (distance, index) in enumerate(zip(distances[0], indices[0])):
#                 if index == -1:  # Invalid result
#                     continue

#                 doc_name, chunk_index, chunk_text = self.metadata[index]
#                 results.append((index, float(distance), doc_name, chunk_index, chunk_text))

#             return results

#         def rebuild_from_cache(self, embeddings: List[Tuple[str, np.ndarray]], metadata: List[Tuple[str, str, int, str]]) -> None:
#             """Rebuild index from cache data.

#             Args:
#                 embeddings: List of (id, vector) tuples from cache.
#                 metadata: List of (id, doc_name, chunk_index, chunk_text) tuples from cache.
#             """
#             # Clear existing index
#             self.index.reset()
#             self.metadata.clear()
#             self.embedding_ids.clear()

#             if not embeddings:
#                 logger.info("No embeddings to rebuild index")
#                 return

#             # Extract vectors and IDs
#             ids = [em[0] for em in embeddings]
#             vectors = [em[1] for em in embeddings]

#             # Build metadata lookup
#             metadata_map = {row[0]: row[1:] for row in metadata}

#             # Add vectors with corresponding metadata
#             vectors_array = np.vstack(vectors).astype(np.float32)
#             self.index.add(vectors_array)

#             for embedding_id, vector in embeddings:
#                 if embedding_id in metadata_map:
#                     doc_name, chunk_index, chunk_text = metadata_map[embedding_id]
#                     self.metadata.append((doc_name, chunk_index, chunk_text))
#                     self.embedding_ids.append(embedding_id)

#             logger.info(f"Rebuilt FAISS index with {self.index.ntotal} vectors")

#         def save(self, path: str) -> None:
#             """Save FAISS index to disk.

#             Args:
#                 path: Path to save index.
#             """
#             os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
#             faiss.write_index(self.index, path)  # type: ignore
#             logger.info(f"Saved FAISS index to {path}")

#         def load(self, path: str) -> None:
#             """Load FAISS index from disk.

#             Args:
#                 path: Path to load index.
#             """
#             if not os.path.exists(path):
#                 logger.warning(f"Index file not found: {path}")
#                 return

#             self.index = faiss.read_index(path)  # type: ignore
#             logger.info(f"Loaded FAISS index from {path} (ntotal: {self.index.ntotal})")

#         def get_stats(self) -> dict:
#             """Get index statistics.

#             Returns:
#                 Dictionary with index stats.
#             """
#             return {
#                 "total_vectors": self.index.ntotal,
#                 "embedding_dim": self.embedding_dim,
#                 "metadata_count": len(self.metadata),
#             }

#         def reset(self) -> None:
#             """Reset index and clear all data."""
#             self.index.reset()
#             self.metadata.clear()
#             self.embedding_ids.clear()
#             logger.info("Reset FAISS vector store")


# else:
#     # faiss not available: import numpy fallback lazily and alias as FAISSVectorStore
#     try:
#         from app.rag.vector_store_fallback import NumpyVectorStore as _FallbackStore  # type: ignore
#     except Exception:
#         # If the fallback file is missing, define a minimal inline fallback to avoid ImportError.
#         # (This is defensive; ideally you will add app/rag/vector_store_fallback.py as instructed.)
#         class _FallbackStore:  # type: ignore
#             def __init__(self, embedding_dim: int = 384, index_path: Optional[str] = None):
#                 self.embedding_dim = embedding_dim
#                 self.index_path = index_path
#                 self.vectors = None
#                 self.metadata = []
#                 self.embedding_ids = []

#             def add_vectors(self, vectors, metadata, ids):
#                 import numpy as _np

#                 vectors_array = _np.vstack(vectors).astype(_np.float32)
#                 norms = _np.linalg.norm(vectors_array, axis=1, keepdims=True)
#                 norms[norms == 0] = 1.0
#                 vectors_array = vectors_array / norms
#                 if self.vectors is None:
#                     self.vectors = vectors_array
#                 else:
#                     self.vectors = _np.vstack([self.vectors, vectors_array])
#                 self.metadata.extend(metadata)
#                 self.embedding_ids.extend(ids)

#             def search(self, query_vector, k=3):
#                 import numpy as _np

#                 if self.vectors is None or self.vectors.shape[0] == 0:
#                     return []
#                 q = _np.asarray(query_vector, dtype=_np.float32)
#                 q_norm = _np.linalg.norm(q)
#                 if q_norm == 0:
#                     q_norm = 1.0
#                 q = q / q_norm
#                 scores = (self.vectors @ q).squeeze()
#                 if scores.ndim == 0:
#                     scores = _np.array([float(scores)])
#                 idx_sorted = _np.argsort(-scores)[:k]
#                 results = []
#                 for idx in idx_sorted:
#                     score = float(scores[int(idx)])
#                     doc_name, chunk_index, chunk_text = self.metadata[int(idx)]
#                     results.append((int(idx), score, doc_name, int(chunk_index), chunk_text))
#                 return results

#             def rebuild_from_cache(self, embeddings, metadata):
#                 # simple rebuild
#                 self.vectors = None
#                 self.metadata = []
#                 self.embedding_ids = []
#                 if not embeddings:
#                     return
#                 ids = [em[0] for em in embeddings]
#                 vectors = [em[1] for em in embeddings]
#                 metadata_map = {row[0]: (row[1], row[2], row[3]) for row in metadata}
#                 metas_list = []
#                 for embedding_id, vec in zip(ids, vectors):
#                     if embedding_id in metadata_map:
#                         doc_name, chunk_index, chunk_text = metadata_map[embedding_id]
#                     else:
#                         doc_name, chunk_index, chunk_text = ("unknown", -1, "")
#                     metas_list.append((doc_name, chunk_index, chunk_text))
#                 self.add_vectors(vectors, metas_list, ids)

#             def save(self, path: str) -> None:
#                 return

#             def load(self, path: str) -> None:
#                 return

#             def get_stats(self):
#                 return {"total_vectors": 0, "embedding_dim": self.embedding_dim, "metadata_count": len(self.metadata)}

#             def reset(self):
#                 self.vectors = None
#                 self.metadata = []
#                 self.embedding_ids = []

#     class FAISSVectorStore(_FallbackStore):  # type: ignore
#         """
#         Backwards-compatible alias: if faiss is not installed, use the NumPy fallback.
#         This subclass simply inherits the fallback implementation so external code
#         that expects FAISSVectorStore still works without changes.
#         """
#         pass





# # # app/rag/vector_store.py
# # """
# # FAISS-based vector store.
# # Manages FAISS index and metadata mapping for efficient similarity search.
# # """
# # import numpy as np
# # import faiss
# # from typing import List, Tuple, Optional
# # import os
# # import logging

# # logger = logging.getLogger(__name__)


# # class FAISSVectorStore:
# #     """FAISS-based vector store for similarity search."""

# #     def __init__(self, embedding_dim: int = 384, index_path: Optional[str] = None):
# #         """Initialize FAISS vector store.

# #         Args:
# #             embedding_dim: Dimension of embeddings (384 for all-MiniLM-L6-v2).
# #             index_path: Path to save/load FAISS index.
# #         """
# #         self.embedding_dim = embedding_dim
# #         self.index_path = index_path
# #         self.index = faiss.IndexFlatIP(embedding_dim)  # Inner product for cosine similarity
# #         self.metadata: List[Tuple[str, int, str]] = []  # (doc_name, chunk_index, chunk_text)
# #         self.embedding_ids: List[str] = []  # IDs from cache

# #         if index_path and os.path.exists(index_path):
# #             self.load(index_path)

# #     def add_vectors(
# #         self, vectors: List[np.ndarray], metadata: List[Tuple[str, int, str]], ids: List[str]
# #     ) -> None:
# #         """Add vectors to index with metadata.

# #         Args:
# #             vectors: List of normalized embedding vectors.
# #             metadata: List of (doc_name, chunk_index, chunk_text) tuples.
# #             ids: List of embedding IDs from cache.
# #         """
# #         if len(vectors) != len(metadata) or len(vectors) != len(ids):
# #             raise ValueError("Vectors, metadata, and IDs length mismatch")

# #         # Stack vectors into matrix
# #         vectors_array = np.vstack(vectors).astype(np.float32)

# #         # Add to index
# #         self.index.add(vectors_array)
# #         self.metadata.extend(metadata)
# #         self.embedding_ids.extend(ids)

# #         logger.info(f"Added {len(vectors)} vectors to FAISS index (total: {self.index.ntotal})")

# #     def search(self, query_vector: np.ndarray, k: int = 3) -> List[Tuple[int, float, str, int, str]]:
# #         """Search for similar vectors.

# #         Args:
# #             query_vector: Query embedding vector (should be normalized).
# #             k: Number of results to return.

# #         Returns:
# #             List of (index, score, doc_name, chunk_index, chunk_text) tuples.
# #         """
# #         if self.index.ntotal == 0:
# #             logger.warning("FAISS index is empty")
# #             return []

# #         query_array = np.array([query_vector], dtype=np.float32)

# #         # FAISS returns distances and indices
# #         distances, indices = self.index.search(query_array, min(k, self.index.ntotal))

# #         results = []
# #         for i, (distance, index) in enumerate(zip(distances[0], indices[0])):
# #             if index == -1:  # Invalid result
# #                 continue

# #             doc_name, chunk_index, chunk_text = self.metadata[index]
# #             results.append((index, float(distance), doc_name, chunk_index, chunk_text))

# #         return results

# #     def rebuild_from_cache(self, embeddings: List[Tuple[str, np.ndarray]], metadata: List[Tuple[str, str, int, str]]) -> None:
# #         """Rebuild index from cache data.

# #         Args:
# #             embeddings: List of (id, vector) tuples from cache.
# #             metadata: List of (id, doc_name, chunk_index, chunk_text) tuples from cache.
# #         """
# #         # Clear existing index
# #         self.index.reset()
# #         self.metadata.clear()
# #         self.embedding_ids.clear()

# #         if not embeddings:
# #             logger.info("No embeddings to rebuild index")
# #             return

# #         # Extract vectors and IDs
# #         ids = [em[0] for em in embeddings]
# #         vectors = [em[1] for em in embeddings]

# #         # Build metadata lookup
# #         metadata_map = {row[0]: row[1:] for row in metadata}

# #         # Add vectors with corresponding metadata
# #         vectors_array = np.vstack(vectors).astype(np.float32)
# #         self.index.add(vectors_array)

# #         for embedding_id, vector in embeddings:
# #             if embedding_id in metadata_map:
# #                 doc_name, chunk_index, chunk_text = metadata_map[embedding_id]
# #                 self.metadata.append((doc_name, chunk_index, chunk_text))
# #                 self.embedding_ids.append(embedding_id)

# #         logger.info(f"Rebuilt FAISS index with {self.index.ntotal} vectors")

# #     def save(self, path: str) -> None:
# #         """Save FAISS index to disk.

# #         Args:
# #             path: Path to save index.
# #         """
# #         os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
# #         faiss.write_index(self.index, path)
# #         logger.info(f"Saved FAISS index to {path}")

# #     def load(self, path: str) -> None:
# #         """Load FAISS index from disk.

# #         Args:
# #             path: Path to load index.
# #         """
# #         if not os.path.exists(path):
# #             logger.warning(f"Index file not found: {path}")
# #             return

# #         self.index = faiss.read_index(path)
# #         logger.info(f"Loaded FAISS index from {path} (ntotal: {self.index.ntotal})")

# #     def get_stats(self) -> dict:
# #         """Get index statistics.

# #         Returns:
# #             Dictionary with index stats.
# #         """
# #         return {
# #             "total_vectors": self.index.ntotal,
# #             "embedding_dim": self.embedding_dim,
# #             "metadata_count": len(self.metadata),
# #         }

# #     def reset(self) -> None:
# #         """Reset index and clear all data."""
# #         self.index.reset()
# #         self.metadata.clear()
# #         self.embedding_ids.clear()
# #         logger.info("Reset FAISS vector store")
