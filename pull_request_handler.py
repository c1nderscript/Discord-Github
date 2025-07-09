"""Simplified pull request event handler used for tests."""

from config import settings
from discord_bot import discord_bot_instance
import pr_map

async def handle_pull_request_event_with_retry(payload: dict) -> bool:
    """Handle pull request events with basic map management."""
    action = payload.get("action")
    repo = payload["repository"]["full_name"]
    number = payload["pull_request"]["number"]
    key = f"{repo}#{number}"

    from main import send_to_discord

    if action == "opened":
        message = await send_to_discord(settings.channel_pull_requests, embed=None)
        data = pr_map.load_pr_map()
        data[key] = message.id
        pr_map.save_pr_map(data)
    elif action == "closed" and payload["pull_request"].get("merged"):
        data = pr_map.load_pr_map()
        message_id = data.get(key)
        if message_id:
            await discord_bot_instance.delete_message_from_channel(
                settings.channel_pull_requests, message_id
            )
            del data[key]
            pr_map.save_pr_map(data)
    return True
