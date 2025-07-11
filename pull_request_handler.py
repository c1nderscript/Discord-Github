"""Process `pull_request` webhook events and manage Discord messages.

The handler formats pull request payloads into Discord embeds, posts them
to the appropriate channel, tracks message IDs for later updates, and
removes messages when pull requests are closed.  A retry wrapper is
provided via :func:`handle_pull_request_event_with_retry` to improve
resilience.
"""

import asyncio
import logging
from typing import Any, Dict

from config import settings
from discord_bot import discord_bot_instance
from formatters import format_pull_request_event, format_merge_event
from pr_map import load_pr_map, save_pr_map

logger = logging.getLogger(__name__)

DEFAULT_RETRIES = 3
DEFAULT_DELAY = 1.0


def _get_pr_key(payload: Dict[str, Any]) -> str:
    """Return a unique key for the pull request payload."""
    repo = payload.get("repository", {}).get("full_name", "")
    number = payload.get("pull_request", {}).get("number")
    return f"{repo}#{number}"


async def process_pull_request_event(payload: Dict[str, Any]) -> None:
    """Process a single pull_request event."""
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    pr_key = _get_pr_key(payload)

    if action == "closed" and pr.get("merged"):
        embed = format_merge_event(payload)
        channel_id = settings.channel_code_merges
    else:
        embed = format_pull_request_event(payload)
        channel_id = settings.channel_pull_requests

    # Import inside the function to avoid circular dependency with main
    from main import send_to_discord

    message = await send_to_discord(channel_id, embed=embed)

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


async def handle_pull_request_event_with_retry(
    payload: Dict[str, Any], retries: int = DEFAULT_RETRIES, delay: float = DEFAULT_DELAY
) -> bool:
    """Process a pull_request event with retry logic."""
    for attempt in range(1, retries + 1):
        try:
            await process_pull_request_event(payload)
            return True
        except Exception as exc:  # pragma: no cover - unexpected failures
            logger.error("Error processing pull_request event: %s", exc)
            if attempt < retries:
                await asyncio.sleep(delay * attempt)
    return False
