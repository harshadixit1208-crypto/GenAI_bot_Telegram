# app/utils/config.py
"""
Configuration loader from environment variables.
Handles loading and validation of all configuration parameters.
"""
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """Application configuration loaded from environment variables."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        # Telegram
        self.telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not self.telegram_bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not set")

        # LLM Configuration
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.ollama_url: Optional[str] = os.getenv("OLLAMA_URL")

        # Database
        self.database_path: str = os.getenv("DATABASE_PATH", "./data/embeddings.db")
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)

        # Models
        self.embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.vision_model: str = os.getenv(
            "VISION_MODEL", "Salesforce/blip-image-captioning-base"
        )

        # Logging
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

        # FAISS
        self.faiss_index_path: str = os.getenv("FAISS_INDEX_PATH", "./data/faiss_index.bin")
        Path(self.faiss_index_path).parent.mkdir(parents=True, exist_ok=True)

        # Chunking
        self.chunk_size_tokens: int = int(os.getenv("CHUNK_SIZE_TOKENS", "400"))
        self.chunk_overlap_tokens: int = int(os.getenv("CHUNK_OVERLAP_TOKENS", "100"))

        # RAG
        self.rag_top_k: int = int(os.getenv("RAG_TOP_K", "3"))
        self.rag_max_context_tokens: int = int(os.getenv("RAG_MAX_CONTEXT_TOKENS", "3000"))

        # LLM Generation
        self.llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "256"))
        self.llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
        self.llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

        # Validate config
        self._validate()

    def _validate(self) -> None:
        """Validate configuration parameters."""
        if not self.openai_api_key and not self.ollama_url:
            logger.warning("Neither OPENAI_API_KEY nor OLLAMA_URL is set; LLM calls may fail")

    def get_llm_provider(self) -> str:
        """Determine which LLM provider to use."""
        if self.openai_api_key:
            return "openai"
        elif self.ollama_url:
            return "ollama"
        return "none"


# Global config instance
config = Config()
