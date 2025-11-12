# app/utils/logging.py
"""
Logging configuration for the application.
Provides structured logging with configurable levels.
"""
import logging
import sys
from app.utils.config import config


def setup_logging() -> None:
    """Configure logging for the application."""
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Suppress overly verbose logs from dependencies
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Module name (typically __name__).

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
