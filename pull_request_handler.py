import logging
from typing import Dict, Any

from config import settings
from discord_bot import discord_bot_instance
import pr_map
from formatters import format_pull_request_event

logger = logging.getLogger(__name__)


async def handle_pull_request_event_with_retry(payload: Dict[str, Any]) -> bool:
    """Simplified pull request handler for tests."""
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    repo_name = repo.get("full_name")
    number = pr.get("number")
    key = f"{repo_name}#{number}"

    from main import send_to_discord

    embed = format_pull_request_event(payload)
    message = await send_to_discord(settings.channel_pull_requests, embed=embed)

    if action == "opened":
        if hasattr(message, "id"):
            data = pr_map.load_pr_map()
            data[key] = message.id
            pr_map.save_pr_map(data)
    elif action == "closed":
        data = pr_map.load_pr_map()
        message_id = data.pop(key, None)
        if message_id:
            await discord_bot_instance.delete_message_from_channel(
                settings.channel_pull_requests,
                message_id,
            )
            pr_map.save_pr_map(data)
    return True
