import asyncio
import logging
from typing import Dict

from config import settings
from discord_bot import discord_bot_instance
from formatters import format_pull_request_event, format_merge_event
from pr_map import load_pr_map, save_pr_map

logger = logging.getLogger(__name__)

# Retry configuration
_MAX_RETRIES = 3
_INITIAL_DELAY = 2


def _get_pr_key(payload: Dict[str, dict]) -> str:
    pr = payload.get("pull_request", {})
    number = pr.get("number")
    repo = payload.get("repository", {}).get("full_name")
    return f"{repo}#{number}"


async def _process_pull_request_event(payload: Dict[str, dict]) -> bool:
    """Handle a single pull_request event."""
    try:
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})

        if action == "closed" and pr.get("merged"):
            embed = format_merge_event(payload)
            channel_id = settings.channel_code_merges
        else:
            embed = format_pull_request_event(payload)
            channel_id = settings.channel_pull_requests

        # Import inside the function to avoid circular dependency with main
        from main import send_to_discord

        message = await send_to_discord(channel_id, embed=embed)

        pr_key = _get_pr_key(payload)
        pr_map_data: Dict[str, int] = load_pr_map()

        if action in {"opened", "ready_for_review"}:
            if message:
                pr_map_data[pr_key] = message.id
                save_pr_map(pr_map_data)
        elif action == "closed":
            message_id = pr_map_data.pop(pr_key, None)
            if message_id:
                await discord_bot_instance.delete_message_from_channel(
                    settings.channel_pull_requests, message_id
                )
                save_pr_map(pr_map_data)
        return True
    except Exception as exc:  # pragma: no cover - unexpected errors
        logger.error(f"Error handling pull_request event: {exc}")
        return False


async def handle_pull_request_event_with_retry(payload: Dict[str, dict]) -> bool:
    """Process a pull_request event with retry logic."""
    delay = _INITIAL_DELAY
    for attempt in range(1, _MAX_RETRIES + 1):
        if await _process_pull_request_event(payload):
            return True
        logger.warning(
            "Pull request handling failed, retry %s/%s in %ss",
            attempt,
            _MAX_RETRIES,
            delay,
        )
        await asyncio.sleep(delay)
        delay *= 2
    return False
