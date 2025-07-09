"""Handle pull request webhook events with basic state tracking."""

import logging
from typing import Dict

from config import settings
from discord_bot import discord_bot_instance
from formatters import format_pull_request_event
from pr_map import load_pr_map, save_pr_map

logger = logging.getLogger(__name__)


async def handle_pull_request_event_with_retry(payload: Dict) -> bool:
    """Process pull request events and update Discord messages."""
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    repo_name = repo.get("full_name")
    number = pr.get("number")
    if not repo_name or number is None:
        logger.error("Missing PR information in payload")
        return False

    key = f"{repo_name}#{number}"
    pr_map = load_pr_map()

    if action == "opened":
        from main import send_to_discord  # imported here to avoid circular import
        embed = format_pull_request_event(payload)
        message = await send_to_discord(settings.channel_pull_requests, embed=embed)
        if message:
            pr_map[key] = message.id
            save_pr_map(pr_map)
        return True

    if action == "closed":
        message_id = pr_map.pop(key, None)
        if message_id:
            await discord_bot_instance.delete_message_from_channel(
                settings.channel_pull_requests,
                message_id,
            )
            save_pr_map(pr_map)
        return True

    # For other actions, just post the embed without tracking
    from main import send_to_discord
    embed = format_pull_request_event(payload)
    await send_to_discord(settings.channel_pull_requests, embed=embed)
    return True
