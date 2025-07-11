import asyncio
import logging
from typing import Dict

import aiohttp

from config import settings
from discord_bot import discord_bot_instance
from pr_map import load_pr_map, save_pr_map

__all__ = ["cleanup_pr_messages", "periodic_pr_cleanup"]

logger = logging.getLogger(__name__)
GITHUB_API_BASE = "https://api.github.com"


async def cleanup_pr_messages() -> None:
    """Remove Discord messages for pull requests that are closed."""
    # Wait until the Discord bot is ready so we can delete messages
    while not discord_bot_instance.ready:
        await asyncio.sleep(1)

    pr_map_data: Dict[str, int] = load_pr_map()
    if not pr_map_data:
        logger.info("No pull request messages to clean up")
        return

    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"

    async with aiohttp.ClientSession() as session:
        closed_keys = []
        for key, message_id in list(pr_map_data.items()):
            if "#" not in key:
                logger.error(f"Invalid PR key: {key}")
                continue
            repo, number = key.split("#", 1)
            url = f"{GITHUB_API_BASE}/repos/{repo}/pulls/{number}"
            try:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        logger.warning(
                            f"Failed to fetch PR {key}: {resp.status}"
                        )
                        continue
                    data = await resp.json()
                    if "state" not in data:
                        logger.warning(
                            f"Missing 'state' in PR response for {key}"
                        )
                        continue
            except Exception as exc:
                logger.error(f"Error retrieving PR {key}: {exc}")
                continue

            if data.get("state") != "open":
                deleted = await discord_bot_instance.delete_message_from_channel(
                    settings.channel_pull_requests, message_id
                )
                if deleted:
                    closed_keys.append(key)
                else:
                    logger.error(f"Failed to delete message for {key}")

        for key in closed_keys:
            pr_map_data.pop(key, None)

    save_pr_map(pr_map_data)
    logger.info(f"Removed {len(closed_keys)} closed pull request messages")


async def periodic_pr_cleanup(interval_minutes: int) -> None:
    """Run PR cleanup on a fixed schedule."""
    while True:
        try:
            await cleanup_pr_messages()
        except Exception as exc:  # pragma: no cover - unexpected runtime failure
            logger.error("PR cleanup failed: %s", exc)
        await asyncio.sleep(interval_minutes * 60)
