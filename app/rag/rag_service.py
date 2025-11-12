# app/rag/rag_service.py
"""
RAG (Retrieval-Augmented Generation) service.
Orchestrates document retrieval and prompt building for LLM generation.
"""
from typing import List, Tuple, Dict, Optional
import numpy as np
import logging

from app.rag.extractor import DocumentExtractor
from app.rag.embedder import SentenceTransformerEmbedder, EmbeddingCache
from app.rag.vector_store import FAISSVectorStore

logger = logging.getLogger(__name__)


def truncate_context(context_text: str, max_tokens: int = 3000) -> str:
    """Truncate context to fit token limit.

    Simple heuristic: assume 1 token ≈ 4 characters.

    Args:
        context_text: Context text to truncate.
        max_tokens: Maximum tokens allowed.

    Returns:
        Truncated context.
    """
    max_chars = max_tokens * 4
    if len(context_text) <= max_chars:
        return context_text

    # Truncate and add ellipsis
    truncated = context_text[:max_chars].rsplit(" ", 1)[0] + "..."
    logger.debug(f"Truncated context from {len(context_text)} to {len(truncated)} characters")
    return truncated


class RAGService:
    """Retrieval-Augmented Generation service."""

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        db_path: str = "./data/embeddings.db",
        faiss_index_path: Optional[str] = None,
        chunk_size_tokens: int = 400,
        chunk_overlap_tokens: int = 100,
        top_k: int = 3,
        max_context_tokens: int = 3000,
    ):
        """Initialize RAG service.

        Args:
            embedding_model: Embedding model name.
            db_path: Path to embeddings SQLite database.
            faiss_index_path: Path to FAISS index file.
            chunk_size_tokens: Chunk size in tokens.
            chunk_overlap_tokens: Chunk overlap in tokens.
            top_k: Number of results to retrieve.
            max_context_tokens: Maximum context tokens for LLM.
        """
        self.embedding_model = embedding_model
        self.db_path = db_path
        self.faiss_index_path = faiss_index_path
        self.top_k = top_k
        self.max_context_tokens = max_context_tokens

        # Initialize components
        self.extractor = DocumentExtractor(chunk_size_tokens, chunk_overlap_tokens)
        self.cache = EmbeddingCache(db_path)
        self.embedder = SentenceTransformerEmbedder(embedding_model, cache=self.cache)

        # FAISS index dimension for all-MiniLM-L6-v2 is 384
        embedding_dim = 384 if embedding_model == "all-MiniLM-L6-v2" else 768
        self.vector_store = FAISSVectorStore(embedding_dim=embedding_dim, index_path=faiss_index_path)

        self._initialized = False

    def initialize(self, data_dir: str = "data") -> None:
        """Initialize RAG service with documents from directory.

        Args:
            data_dir: Directory containing documents.
        """
        logger.info("Initializing RAG service...")

        # Extract and chunk documents
        chunked_docs = self.extractor.extract_and_chunk_documents(data_dir)

        if not chunked_docs:
            logger.warning("No documents found to index")
            self._initialized = True
            return

        # Embed and cache
        doc_names = list(set(doc[0] for doc in chunked_docs))
        for doc_name in doc_names:
            chunks = [chunk[2] for chunk in chunked_docs if chunk[0] == doc_name]
            embeddings, newly_created = self.embedder.embed_and_cache(doc_name, chunks)

        # Rebuild FAISS index from cache
        embeddings = self.cache.get_all_vectors()
        metadata = self.cache.get_all_metadata()

        if embeddings:
            self.vector_store.rebuild_from_cache(embeddings, metadata)
            if self.faiss_index_path:
                self.vector_store.save(self.faiss_index_path)

        logger.info(f"RAG service initialized with {len(metadata)} chunks")
        self._initialized = True

    def retrieve(self, query: str, k: Optional[int] = None) -> List[Dict]:
        """Retrieve relevant chunks for a query.

        Args:
            query: Query string.
            k: Number of results (uses self.top_k if None).

        Returns:
            List of dicts with keys: chunk_text, doc_name, chunk_index, score.
        """
        if not self._initialized:
            logger.error("RAG service not initialized")
            return []

        k = k or self.top_k

        # Embed query
        query_embedding = self.embedder.embed_texts([query])[0]

        # Search FAISS
        results = self.vector_store.search(query_embedding, k=k)

        # Format results
        retrieved = []
        for index, score, doc_name, chunk_index, chunk_text in results:
            retrieved.append(
                {
                    "chunk_text": chunk_text,
                    "doc_name": doc_name,
                    "chunk_index": chunk_index,
                    "score": score,
                }
            )

        logger.debug(f"Retrieved {len(retrieved)} chunks for query: {query[:50]}")
        return retrieved

    def build_prompt(self, query: str, retrieved: List[Dict], include_sources: bool = True) -> str:
        """Build a prompt with safety instructions and retrieved context.

        Args:
            query: Original query.
            retrieved: List of retrieved chunks.
            include_sources: Include source information.

        Returns:
            Formatted prompt for LLM.
        """
        # Build sources section
        sources = []
        for i, result in enumerate(retrieved, 1):
            source_line = (
                f"{i}) {result['doc_name']} (chunk {result['chunk_index']}): "
                f'"{result["chunk_text"][:100]}..." (similarity: {result["score"]:.2f})'
            )
            sources.append(source_line)

        sources_section = "\n".join(sources)

        # Build context section
        context_chunks = "\n\n---\n\n".join([r["chunk_text"] for r in retrieved])

        # Truncate context if needed
        context_chunks = truncate_context(context_chunks, self.max_context_tokens)

        # Build prompt with safety instructions
        prompt = f"""You are a helpful assistant. Use ONLY the provided context to answer the user's question. 
If the answer is not found in the context, say "I don't know" and show the retrieved sources.
Always cite your sources.

## Context:

{context_chunks}

## Sources:

{sources_section}

## Question:

{query}

## Answer:

"""
        return prompt

    def get_stats(self) -> Dict:
        """Get service statistics.

        Returns:
            Dictionary with stats.
        """
        return {
            "vector_store": self.vector_store.get_stats(),
            "initialized": self._initialized,
        }
