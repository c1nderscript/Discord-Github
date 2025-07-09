"""Handler for GitHub pull request events."""

import logging
from typing import Any

from config import settings
from discord_bot import discord_bot_instance
from formatters import format_pull_request_event, format_merge_event
from pr_map import load_pr_map, save_pr_map

logger = logging.getLogger(__name__)


async def handle_pull_request_event_with_retry(payload: dict) -> bool:
    """Process pull request events with basic retry logic."""
    from main import send_to_discord
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {}).get("full_name", "")
    key = f"{repo}#{pr.get('number')}"

    pr_map = load_pr_map()

    if action == "opened":
        embed = format_pull_request_event(payload)
        message = await send_to_discord(settings.channel_pull_requests, embed=embed)
        if message:
            pr_map[key] = message.id
            save_pr_map(pr_map)
        return True

    if action == "closed" and pr.get("merged"):
        message_id = pr_map.pop(key, None)
        if message_id:
            await discord_bot_instance.delete_message_from_channel(
                settings.channel_pull_requests, message_id
            )
            save_pr_map(pr_map)
        embed = format_merge_event(payload)
        await send_to_discord(settings.channel_code_merges, embed=embed)
        return True

    embed = format_pull_request_event(payload)
    await send_to_discord(settings.channel_pull_requests, embed=embed)
    return True
