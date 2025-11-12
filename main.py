# main.py
"""Entry point for running the Telegram RAG bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

import asyncio
import logging
import sys

# Ensure app package is importable
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.logging import setup_logging
from app.bot import main as bot_main


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Avivo Telegram RAG Bot...")
    try:
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
