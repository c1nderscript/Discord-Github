#!/usr/bin/env python3
"""Utility to clean up stale pull request messages on Discord."""

import asyncio
import logging

from discord_bot import discord_bot_instance
from cleanup import cleanup_pr_messages

logger = logging.getLogger(__name__)


async def main() -> None:
    """Start the bot, run cleanup, then shut down."""
    bot_task = asyncio.create_task(discord_bot_instance.start())
    try:
        await cleanup_pr_messages()
    finally:
        await discord_bot_instance.bot.close()
        await bot_task


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
