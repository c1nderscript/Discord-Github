
import asyncio
import logging

"""Cleanup stale pull request messages from Discord."""

import logging
from typing import Dict

import aiohttp

from config import settings

from pr_map import load_pr_map, save_pr_map
from discord_bot import discord_bot_instance

logger = logging.getLogger(__name__)
GITHUB_API = "https://api.github.com"


async def cleanup_pr_messages() -> None:
    """Delete Discord messages for closed pull requests."""
    # Wait for Discord bot to be ready
    while not discord_bot_instance.ready:
        await asyncio.sleep(1)

    pr_map = load_pr_map()
    if not pr_map:
        logger.info("No PR messages to clean up")
        return

    cleaned = 0
    headers = {"Accept": "application/vnd.github+json"}

from discord_bot import discord_bot_instance
from pr_map import load_pr_map, save_pr_map

logger = logging.getLogger(__name__)
GITHUB_API_URL = "https://api.github.com"


async def cleanup_pr_messages() -> None:
    """Delete messages for closed pull requests and update the map."""
    pr_map: Dict[str, int] = load_pr_map()
    if not pr_map:
        logger.info("No pull request messages to clean up")
        return

    headers = {}

    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"

    async with aiohttp.ClientSession() as session:

        for pr_key, message_id in list(pr_map.items()):
            repo, number_str = pr_key.split("#", 1)
            url = f"{GITHUB_API}/repos/{repo}/pulls/{number_str}"
            try:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("state") != "open":
                            if await discord_bot_instance.delete_message_from_channel(
                                settings.channel_pull_requests,
                                message_id,
                            ):
                                cleaned += 1
                            pr_map.pop(pr_key, None)
                    else:
                        logger.warning(f"Failed to fetch PR {pr_key}: {resp.status}")
            except Exception as exc:
                logger.error(f"Error while cleaning {pr_key}: {exc}")

    save_pr_map(pr_map)
    logger.info(f"Cleaned up {cleaned} pull request messages")

        closed_keys = []
        for pr_key, message_id in pr_map.items():
            try:
                repo, number = pr_key.split("#", 1)
            except ValueError:
                logger.error(f"Invalid PR key: {pr_key}")
                continue

            url = f"{GITHUB_API_URL}/repos/{repo}/pulls/{number}"
            try:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to fetch PR {pr_key}: {resp.status}")
                        continue
                    data = await resp.json()
            except Exception as e:
                logger.error(f"Error retrieving PR {pr_key}: {e}")
                continue

            if data.get("state") == "closed":
                try:
                    deleted = await discord_bot_instance.delete_message_from_channel(
                        settings.channel_pull_requests, message_id
                    )
                    if deleted:
                        closed_keys.append(pr_key)
                    else:
                        logger.error(f"Failed to delete message for {pr_key}")
                except Exception as e:
                    logger.error(f"Error deleting message for {pr_key}: {e}")

        for key in closed_keys:
            pr_map.pop(key, None)

    save_pr_map(pr_map)
    logger.info(f"Removed {len(closed_keys)} closed pull request messages")

