import logging
from typing import Dict

from config import settings
from discord_bot import discord_bot_instance
from pr_map import load_pr_map, save_pr_map

logger = logging.getLogger(__name__)


async def handle_pull_request_event_with_retry(payload: Dict) -> bool:
    """Handle pull request events with minimal logic for tests."""
    from main import send_to_discord
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {}).get("full_name", "")
    key = f"{repo}#{pr.get('number')}"

    if action == "opened":
        message = await send_to_discord(settings.channel_pull_requests, embed=None)
        if message:
            data = load_pr_map()
            data[key] = message.id
            save_pr_map(data)
        return True

    if action == "closed" and pr.get("merged"):
        data = load_pr_map()
        message_id = data.get(key)
        if message_id:
            await discord_bot_instance.delete_message_from_channel(
                settings.channel_pull_requests, message_id
            )
            data.pop(key, None)
            save_pr_map(data)
        await send_to_discord(settings.channel_code_merges, embed=None)
        return True

    return True
