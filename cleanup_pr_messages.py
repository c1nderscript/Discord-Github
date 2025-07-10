#!/usr/bin/env python3
"""Utility to clean up stale pull request messages on Discord."""

import asyncio
import logging
from typing import Dict

import aiohttp

from config import settings
from discord_bot import discord_bot_instance
import pr_map

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com"


async def fetch_pr(session: aiohttp.ClientSession, repo: str, number: str) -> Dict:
    """Fetch pull request details from GitHub."""
    url = f"{GITHUB_API_URL}/repos/{repo}/pulls/{number}"
    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"
    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            logger.error("Failed to fetch PR %s#%s: %s", repo, number, resp.status)
            return {}
        return await resp.json()


async def cleanup_pr_messages() -> None:
    """Remove Discord messages for closed or merged pull requests."""
    data = pr_map.load_pr_map()
    if not data:
        logger.info("No PR messages to clean up")
        return

    await discord_bot_instance.bot.wait_until_ready()

    async with aiohttp.ClientSession() as session:
        for pr_key, message_id in list(data.items()):
            repo, number = pr_key.split("#", 1)
            pr = await fetch_pr(session, repo, number)
            if not pr:
                continue
            state = pr.get("state")
            merged = pr.get("merged", False)
            if state == "closed" or merged:
                await discord_bot_instance.delete_message_from_channel(
                    settings.channel_pull_requests,
                    message_id,
                )
                data.pop(pr_key, None)

    pr_map.save_pr_map(data)
    logger.info("PR message cleanup complete")


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
