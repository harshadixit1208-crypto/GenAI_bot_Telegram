# app/rag/embedder.py
"""
Embedding generation and caching.
Uses sentence-transformers for embeddings with SQLite caching.
"""
import sqlite3
import hashlib
import pickle
from typing import List, Tuple, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """Manages embedding storage and retrieval from SQLite."""

    def __init__(self, db_path: str):
        """Initialize embedding cache.

        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database with embeddings table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                id TEXT PRIMARY KEY,
                doc_name TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                vector BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Index for efficient lookups
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_doc_name ON embeddings(doc_name)
            """
        )

        conn.commit()
        conn.close()
        logger.info(f"Initialized embedding cache at {self.db_path}")

    def _generate_id(self, doc_name: str, chunk_index: int) -> str:
        """Generate unique ID for embedding.

        Args:
            doc_name: Document name.
            chunk_index: Chunk index.

        Returns:
            Unique ID string.
        """
        key = f"{doc_name}#{chunk_index}".encode()
        return hashlib.md5(key).hexdigest()

    def _vector_to_blob(self, vector: np.ndarray) -> bytes:
        """Convert numpy vector to blob for storage.

        Args:
            vector: Numpy array.

        Returns:
            Serialized bytes.
        """
        return pickle.dumps(vector)

    def _blob_to_vector(self, blob: bytes) -> np.ndarray:
        """Convert blob back to numpy vector.

        Args:
            blob: Serialized bytes.

        Returns:
            Numpy array.
        """
        return pickle.loads(blob)

    def add_embeddings(
        self, doc_name: str, chunks: List[str], vectors: List[np.ndarray]
    ) -> int:
        """Add embeddings for chunks to cache.

        Args:
            doc_name: Document name.
            chunks: List of text chunks.
            vectors: List of embedding vectors.

        Returns:
            Number of embeddings added.
        """
        if len(chunks) != len(vectors):
            raise ValueError(f"Chunks and vectors length mismatch: {len(chunks)} vs {len(vectors)}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        added_count = 0
        for chunk_idx, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
            embedding_id = self._generate_id(doc_name, chunk_idx)

            # Check if already exists
            cursor.execute("SELECT id FROM embeddings WHERE id = ?", (embedding_id,))
            if cursor.fetchone():
                logger.debug(f"Embedding {embedding_id} already exists, skipping")
                continue

            vector_blob = self._vector_to_blob(vector)
            cursor.execute(
                """
                INSERT INTO embeddings (id, doc_name, chunk_index, chunk_text, vector)
                VALUES (?, ?, ?, ?, ?)
                """,
                (embedding_id, doc_name, chunk_idx, chunk_text, vector_blob),
            )
            added_count += 1

        conn.commit()
        conn.close()

        logger.info(f"Added {added_count} embeddings for {doc_name}")
        return added_count

    def get_all_vectors(self) -> List[Tuple[str, np.ndarray]]:
        """Get all embeddings and their IDs.

        Returns:
            List of (id, vector) tuples in order.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, vector FROM embeddings ORDER BY ROWID ASC")
        results = cursor.fetchall()
        conn.close()

        return [(row[0], self._blob_to_vector(row[1])) for row in results]

    def get_all_metadata(self) -> List[Tuple[str, str, int, str]]:
        """Get all embedding metadata.

        Returns:
            List of (id, doc_name, chunk_index, chunk_text) tuples.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, doc_name, chunk_index, chunk_text FROM embeddings ORDER BY ROWID ASC"
        )
        results = cursor.fetchall()
        conn.close()

        return results

    def find_chunk_by_index(self, global_index: int) -> Optional[Tuple[str, str, int]]:
        """Find chunk metadata by global index.

        Args:
            global_index: Global index (based on database row order).

        Returns:
            (doc_name, chunk_text, chunk_index) or None.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # SQLite ROWID starts from 1
        cursor.execute(
            "SELECT doc_name, chunk_text, chunk_index FROM embeddings WHERE ROWID = ?",
            (global_index + 1,),
        )
        result = cursor.fetchone()
        conn.close()

        return result

    def get_doc_hash(self, doc_name: str) -> Optional[str]:
        """Get hash of all chunks for a document.

        Args:
            doc_name: Document name.

        Returns:
            Hash of combined chunk text or None if not found.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT chunk_text FROM embeddings WHERE doc_name = ? ORDER BY chunk_index", (doc_name,))
        chunks = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not chunks:
            return None

        combined = "".join(chunks).encode()
        return hashlib.md5(combined).hexdigest()

    def delete_doc(self, doc_name: str) -> int:
        """Delete all embeddings for a document.

        Args:
            doc_name: Document name.

        Returns:
            Number of deleted records.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM embeddings WHERE doc_name = ?", (doc_name,))
        deleted_count = cursor.rowcount

        conn.commit()
        conn.close()

        logger.info(f"Deleted {deleted_count} embeddings for {doc_name}")
        return deleted_count

    def clear_all(self) -> None:
        """Clear all embeddings from cache."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM embeddings")
        conn.commit()
        conn.close()
        logger.info("Cleared all embeddings from cache")


class SentenceTransformerEmbedder:
    """Generates embeddings using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache: Optional[EmbeddingCache] = None):
        """Initialize embedder.

        Args:
            model_name: HuggingFace model name.
            cache: Optional EmbeddingCache instance for persistent storage.
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.cache = cache
        logger.info(f"Loaded embedding model: {model_name}")

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """Generate embeddings for texts.

        Args:
            texts: List of texts to embed.
            batch_size: Batch size for processing.

        Returns:
            List of embedding vectors (normalized for cosine similarity).
        """
        embeddings = self.model.encode(texts, batch_size=batch_size, convert_to_numpy=True, show_progress_bar=False)

        # Normalize for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized_embeddings = embeddings / (norms + 1e-9)

        return [vec for vec in normalized_embeddings]

    def embed_and_cache(
        self, doc_name: str, chunks: List[str], batch_size: int = 32
    ) -> Tuple[List[np.ndarray], bool]:
        """Generate embeddings and cache them.

        Args:
            doc_name: Document name.
            chunks: List of text chunks.
            batch_size: Batch size for processing.

        Returns:
            (embeddings, newly_created) tuple. newly_created=True if embeddings were generated,
            False if loaded from cache.
        """
        if not self.cache:
            # No cache, just embed
            return self.embed_texts(chunks, batch_size), True

        # Check if document already cached
        doc_hash = self.cache.get_doc_hash(doc_name)
        combined_hash = hashlib.md5("".join(chunks).encode()).hexdigest()

        if doc_hash == combined_hash:
            logger.debug(f"Using cached embeddings for {doc_name}")
            # Load from cache - need to fetch by doc_name
            conn = sqlite3.connect(self.cache.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT vector FROM embeddings WHERE doc_name = ? ORDER BY chunk_index",
                (doc_name,),
            )
            vectors = [self.cache._blob_to_vector(row[0]) for row in cursor.fetchall()]
            conn.close()
            return vectors, False

        # Generate embeddings
        embeddings = self.embed_texts(chunks, batch_size)

        # Cache them
        self.cache.add_embeddings(doc_name, chunks, embeddings)

        return embeddings, True
