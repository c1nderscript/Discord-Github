import asyncio
import logging
from typing import Dict

import aiohttp

from config import settings
from discord_bot import discord_bot_instance
from pr_map import load_pr_map, save_pr_map

logger = logging.getLogger(__name__)
GITHUB_API_BASE = "https://api.github.com"


async def fetch_pr_state(session: aiohttp.ClientSession, repo: str, number: int) -> str:
    """Fetch the state of a pull request from GitHub."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"

    url = f"{GITHUB_API_BASE}/repos/{repo}/pulls/{number}"
    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                logger.error(f"Failed to fetch PR {repo}#{number}: {resp.status}")
                return "unknown"
            data = await resp.json()
            return data.get("state", "unknown")
    except Exception as exc:
        logger.error(f"Error fetching PR {repo}#{number}: {exc}")
        return "unknown"


async def cleanup_pr_messages() -> None:
    """Delete channel messages for closed pull requests."""
    pr_map_data: Dict[str, int] = load_pr_map()
    if not pr_map_data:
        logger.info("No PR messages to clean up.")
        return

    async with aiohttp.ClientSession() as session:
        for key, message_id in list(pr_map_data.items()):
            if "#" not in key:
                continue
            repo, num_str = key.split("#", 1)
            state = await fetch_pr_state(session, repo, int(num_str))
            if state == "closed":
                success = await discord_bot_instance.delete_message_from_channel(
                    settings.channel_pull_requests, message_id
                )
                if success:
                    pr_map_data.pop(key)

    save_pr_map(pr_map_data)


async def main() -> None:
    task = asyncio.create_task(discord_bot_instance.start())
    while not discord_bot_instance.ready:
        await asyncio.sleep(1)
    try:
        await cleanup_pr_messages()
    finally:
        await discord_bot_instance.bot.close()
        await task


if __name__ == "__main__":
    asyncio.run(main())
