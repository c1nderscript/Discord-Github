"""Pull request event handler with basic persistence logic for tests."""

import logging
from typing import Dict

from config import settings
from discord_bot import discord_bot_instance
import pr_map
from formatters import format_pull_request_event, format_merge_event

logger = logging.getLogger(__name__)


async def handle_pull_request_event_with_retry(payload: Dict) -> bool:
    """Simplified handler for pull request events used in tests."""
    import main  # Imported here to allow test patching of send_to_discord

    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {}).get("full_name", "")
    pr_key = f"{repo}#{pr.get('number')}"

    if action == "closed" and pr.get("merged"):
        embed = format_merge_event(payload)
        channel = settings.channel_code_merges
        message = await main.send_to_discord(channel, embed=embed)
        # Remove stored message
        data = pr_map.load_pr_map()
        msg_id = data.pop(pr_key, None)
        if msg_id:
            await discord_bot_instance.delete_message_from_channel(
                settings.channel_pull_requests, msg_id
            )
        pr_map.save_pr_map(data)
        return bool(message)

    embed = format_pull_request_event(payload)
    message = await main.send_to_discord(settings.channel_pull_requests, embed=embed)
    if message and action == "opened":
        data = pr_map.load_pr_map()
        data[pr_key] = message.id
        pr_map.save_pr_map(data)
    return bool(message)
