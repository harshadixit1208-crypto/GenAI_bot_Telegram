# app/utils/history.py
"""
User interaction history management.
Maintains last 3 interactions per user for summarization and context.
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Interaction:
    """A single user interaction."""

    timestamp: datetime
    interaction_type: str  # "image", "chat", "ask"
    content: str
    metadata: Optional[Dict] = None


class HistoryManager:
    """Manages user interaction history."""

    def __init__(self, max_per_user: int = 3):
        """Initialize history manager.

        Args:
            max_per_user: Maximum interactions to keep per user.
        """
        self.max_per_user = max_per_user
        self.history: Dict[int, List[Interaction]] = {}

    def add_interaction(
        self, user_id: int, interaction_type: str, content: str, metadata: Optional[Dict] = None
    ) -> None:
        """Add an interaction to user history.

        Args:
            user_id: Telegram user ID.
            interaction_type: Type of interaction (image, chat, ask).
            content: The interaction content.
            metadata: Optional metadata (e.g., image filename, tags).
        """
        if user_id not in self.history:
            self.history[user_id] = []

        interaction = Interaction(
            timestamp=datetime.now(),
            interaction_type=interaction_type,
            content=content,
            metadata=metadata,
        )

        self.history[user_id].append(interaction)

        # Keep only the last N interactions
        if len(self.history[user_id]) > self.max_per_user:
            self.history[user_id] = self.history[user_id][-self.max_per_user :]

        logger.debug(f"Added {interaction_type} interaction for user {user_id}")

    def get_last_image(self, user_id: int) -> Optional[Interaction]:
        """Get the last image interaction for a user.

        Args:
            user_id: Telegram user ID.

        Returns:
            Last image interaction or None.
        """
        if user_id not in self.history:
            return None

        for interaction in reversed(self.history[user_id]):
            if interaction.interaction_type == "image":
                return interaction

        return None

    def get_last_interactions(self, user_id: int, count: int = 3) -> List[Interaction]:
        """Get the last N interactions for a user.

        Args:
            user_id: Telegram user ID.
            count: Number of interactions to return.

        Returns:
            List of last interactions (most recent first).
        """
        if user_id not in self.history:
            return []

        return list(reversed(self.history[user_id]))[:count]

    def get_context_for_summarization(self, user_id: int) -> str:
        """Get context string for summarization.

        Args:
            user_id: Telegram user ID.

        Returns:
            Formatted context string.
        """
        interactions = self.get_last_interactions(user_id, self.max_per_user)
        if not interactions:
            return ""

        context_lines = []
        for i, interaction in enumerate(interactions, 1):
            timestamp = interaction.timestamp.strftime("%H:%M")
            context_lines.append(f"{i}. [{timestamp}] {interaction.interaction_type}: {interaction.content[:100]}")

        return "\n".join(context_lines)

    def clear_user_history(self, user_id: int) -> None:
        """Clear all history for a user.

        Args:
            user_id: Telegram user ID.
        """
        if user_id in self.history:
            del self.history[user_id]
            logger.debug(f"Cleared history for user {user_id}")
