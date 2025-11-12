# app/bot.py
"""
Main Telegram bot implementation.
Handles all Telegram commands and interactions.
"""
import asyncio
import logging
import os
import tempfile
from typing import Optional

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telegram.constants import ParseMode

from app.utils.config import config
from app.utils.history import HistoryManager
from app.rag.rag_service import RAGService
from app.llm.client import LLMClient
from app.vision.blip_service import BLIPCaptioningService

logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_IMAGE = 1


class TelegramRAGBot:
    """Main Telegram bot application."""

    def __init__(self):
        """Initialize bot."""
        self.config = config
        self.history_manager = HistoryManager(max_per_user=3)

        # Initialize RAG service
        self.rag_service = RAGService(
            embedding_model=config.embedding_model,
            db_path=config.database_path,
            faiss_index_path=config.faiss_index_path,
            chunk_size_tokens=config.chunk_size_tokens,
            chunk_overlap_tokens=config.chunk_overlap_tokens,
            top_k=config.rag_top_k,
            max_context_tokens=config.rag_max_context_tokens,
        )

        # Initialize LLM client
        self.llm_client = LLMClient(
            openai_api_key=config.openai_api_key,
            ollama_url=config.ollama_url,
            timeout_seconds=config.llm_timeout_seconds,
        )

        # Initialize vision service
        self.vision_service = BLIPCaptioningService(model_name=config.vision_model)

        # Will be set in main
        self.app: Optional[Application] = None

    async def initialize(self, data_dir: str = "data") -> None:
        """Initialize bot services.

        Args:
            data_dir: Directory with documents for RAG.
        """
        logger.info("Initializing bot services...")
        self.rag_service.initialize(data_dir)
        logger.info("Bot services initialized")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command.

        Args:
            update: Telegram update.
            context: Context.
        """
        welcome_message = """
Welcome to Avivo RAG Bot! 🤖

I can help you with:
• <b>Text Search</b> - Ask questions about documents (/ask)
• <b>Image Captioning</b> - Get captions for images (/image)
• <b>Summarization</b> - Summarize previous interactions (/summarize)

Use /help for detailed usage instructions.
        """.strip()

        await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)
        logger.info(f"User {update.effective_user.id} started bot")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command.

        Args:
            update: Telegram update.
            context: Context.
        """
        help_text = """
<b>Available Commands:</b>

/ask &lt;query&gt; — Ask a question about documents
Example: /ask What are the company policies?

/image — Upload an image for captioning
Reply with a photo and I'll generate a caption and tags

/summarize — Summarize your recent interactions
I'll create a summary of your last 3 messages or images

/start — Show welcome message
/help — Show this help message

<b>Tips:</b>
• Use clear, specific queries for better results
• Uploaded images should be clear for better captions
• I keep track of your last 3 interactions for summarization
        """.strip()

        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

    async def ask_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /ask command for document retrieval.

        Args:
            update: Telegram update.
            context: Context.
        """
        # Extract query from command
        if not context.args:
            await update.message.reply_text(
                "Please provide a query. Example: /ask What are the policies?",
                parse_mode=ParseMode.HTML,
            )
            return

        query = " ".join(context.args)
        user_id = update.effective_user.id

        # Add to history
        self.history_manager.add_interaction(user_id, "ask", query)

        # Show thinking message
        await update.message.chat.send_action("typing")

        try:
            # Retrieve relevant chunks
            retrieved = self.rag_service.retrieve(query, k=self.config.rag_top_k)

            if not retrieved:
                await update.message.reply_text(
                    "Sorry, I couldn't find any relevant information in the documents.",
                    parse_mode=ParseMode.HTML,
                )
                return

            # Build prompt
            prompt = self.rag_service.build_prompt(query, retrieved)

            # Generate answer
            result = await self.llm_client.generate_async(
                prompt,
                max_tokens=self.config.llm_max_tokens,
                temperature=self.config.llm_temperature,
            )

            # Check if response contains an error
            if "Error" in result.get("text", "") or not result.get("text"):
                error_msg = result.get("text", "Failed to generate response")
                if "quota" in error_msg.lower():
                    await update.message.reply_text(
                        "⚠️ LLM API quota exceeded. Please check your OpenAI account or configure Ollama.\n\n"
                        f"Documents found: {len(retrieved)} chunk(s) with relevant information.\n"
                        "Set OLLAMA_URL environment variable and restart the bot to use local LLM.",
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    await update.message.reply_text(
                        f"Error: {error_msg}",
                        parse_mode=ParseMode.HTML,
                    )
                return

            # Format response
            response_text = f"<b>Answer:</b>\n{result['text']}\n\n"
            response_text += "<b>Sources:</b>\n"
            for i, r in enumerate(retrieved, 1):
                source_info = f"{i}. {r['doc_name']} (chunk {r['chunk_index']}) - similarity: {r['score']:.2f}"
                response_text += source_info + "\n"

            # Send response
            await update.message.reply_text(response_text, parse_mode=ParseMode.HTML)
            logger.info(f"User {user_id} asked: {query[:50]}")

        except Exception as e:
            logger.error(f"Error in /ask command: {e}")
            await update.message.reply_text(
                f"Error: {str(e)[:100]}",
                parse_mode=ParseMode.HTML,
            )

    async def image_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /image command to start image captioning.

        Args:
            update: Telegram update.
            context: Context.
        """
        await update.message.reply_text(
            "Please upload an image and I'll generate a caption and tags for it.",
            parse_mode=ParseMode.HTML,
        )
        return WAITING_FOR_IMAGE

    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle image upload for captioning.

        Args:
            update: Telegram update.
            context: Context.

        Returns:
            State (WAITING_FOR_IMAGE to continue or ConversationHandler.END).
        """
        user_id = update.effective_user.id

        if not update.message.photo:
            await update.message.reply_text(
                "Please send a valid image.",
                parse_mode=ParseMode.HTML,
            )
            return WAITING_FOR_IMAGE

        await update.message.chat.send_action("upload_photo")

        try:
            # Download image
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            # Download file to path
            await file.download_to_drive(tmp_path)

            await update.message.chat.send_action("typing")

            # Generate caption
            result = await self.vision_service.caption_image_async(tmp_path)

            # Add to history
            self.history_manager.add_interaction(
                user_id,
                "image",
                result["caption"],
                metadata={"tags": result["tags"], "file": tmp_path},
            )

            # Format response
            if result["success"]:
                caption = result["caption"]
                tags = ", ".join(result["tags"])
                response = f"<b>Caption:</b> {caption}\n\n<b>Tags:</b> {tags}"
            else:
                response = f"Error: {result['caption']}"

            await update.message.reply_text(response, parse_mode=ParseMode.HTML)

            # Clean up
            os.unlink(tmp_path)
            logger.info(f"User {user_id} captioned image")

        except Exception as e:
            logger.error(f"Error handling image: {e}")
            await update.message.reply_text(
                f"Error processing image: {str(e)[:100]}",
                parse_mode=ParseMode.HTML,
            )

        return ConversationHandler.END

    async def summarize_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /summarize command.

        Args:
            update: Telegram update.
            context: Context.
        """
        user_id = update.effective_user.id

        # Get last interactions
        interactions = self.history_manager.get_last_interactions(user_id, count=3)

        if not interactions:
            await update.message.reply_text(
                "No recent interactions to summarize.",
                parse_mode=ParseMode.HTML,
            )
            return

        # Build context for summarization
        context_text = self.history_manager.get_context_for_summarization(user_id)

        # Create summarization prompt
        prompt = f"""Summarize the following recent interactions in 2-3 sentences:

{context_text}

Summary:"""

        await update.message.chat.send_action("typing")

        try:
            result = await self.llm_client.generate_async(prompt, max_tokens=100)

            if result.get("text"):
                summary = result["text"]
                await update.message.reply_text(f"<b>Summary:</b>\n{summary}", parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text(
                    "Error generating summary.",
                    parse_mode=ParseMode.HTML,
                )

        except Exception as e:
            logger.error(f"Error in /summarize: {e}")
            await update.message.reply_text(
                f"Error: {str(e)[:100]}",
                parse_mode=ParseMode.HTML,
            )

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors.

        Args:
            update: Update object.
            context: Context.
        """
        logger.error(f"Update {update} caused error: {context.error}")


async def main():
    """Initialize and start the bot."""
    app = None
    try:
        logger.info("Starting Telegram RAG Bot...")
        
        # Create bot instance
        bot = TelegramRAGBot()
        await bot.initialize(data_dir="data")
        
        # Create Telegram application
        app = Application.builder().token(config.telegram_bot_token).build()
        
        # Add command handlers
        app.add_handler(CommandHandler("start", bot.start_command))
        app.add_handler(CommandHandler("help", bot.help_command))
        app.add_handler(CommandHandler("ask", bot.ask_command))
        app.add_handler(CommandHandler("summarize", bot.summarize_command))
        
        # Add image conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("image", bot.image_command)],
            states={
                WAITING_FOR_IMAGE: [
                    MessageHandler(filters.PHOTO, bot.handle_image),
                ],
            },
            fallbacks=[CommandHandler("cancel", bot.start_command)],
        )
        app.add_handler(conv_handler)
        
        # Add error handler
        app.add_error_handler(bot.error_handler)
        
        # Start the bot
        logger.info("Starting bot polling...")
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
        # Keep the bot running indefinitely
        logger.info("Bot is running. Press Ctrl+C to stop.")
        stop_event = asyncio.Event()
        await stop_event.wait()
        
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)
        raise
    finally:
        if app:
            await app.updater.stop()
            await app.stop()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
