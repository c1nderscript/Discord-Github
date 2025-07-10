"""Simplified Discord bot helpers used in tests."""

from __future__ import annotations

import logging
from typing import Optional


logger = logging.getLogger(__name__)


class DiscordBot:
    """Minimal Discord bot stub with only the features used in tests."""

    async def delete_message_from_channel(self, channel_id: int, message_id: int) -> bool:
        logger.debug("Deleting message %s in channel %s", message_id, channel_id)
        return True


# Global bot instance used by other modules
discord_bot_instance = DiscordBot()


async def send_to_discord(
    channel_id: int,
    content: Optional[str] = None,
    embed: Optional[object] = None,
    use_webhook: bool = False,
) -> Optional[object]:
    """Placeholder function that would send a message to Discord."""
    logger.debug("Sending to channel %s via webhook=%s", channel_id, use_webhook)
    return None

