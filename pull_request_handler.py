import asyncio
import logging
from typing import Any, Dict

from config import settings
from discord_bot import discord_bot_instance
from formatters import format_pull_request_event, format_merge_event
from pr_map import load_pr_map, save_pr_map

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 1


def _get_pr_key(payload: Dict[str, Any]) -> str:
    repo = payload.get("repository", {}).get("full_name", "")
    number = payload.get("pull_request", {}).get("number")
    return f"{repo}#{number}"


async def process_pull_request_event(payload: Dict[str, Any]) -> None:
    action = payload.get("action")
    pr = payload.get("pull_request", {})

    from main import send_to_discord  # avoid circular import

    if action == "closed" and pr.get("merged"):
        embed = format_merge_event(payload)
        await send_to_discord(settings.channel_code_merges, embed=embed)
    else:
        embed = format_pull_request_event(payload)
        message = await send_to_discord(settings.channel_pull_requests, embed=embed)
        if action in {"opened", "ready_for_review"} and message:
            pr_map = load_pr_map()
            pr_map[_get_pr_key(payload)] = message.id
            save_pr_map(pr_map)
            return

    if action == "closed":
        pr_map = load_pr_map()
        msg_id = pr_map.pop(_get_pr_key(payload), None)
        if msg_id:
            await discord_bot_instance.delete_message_from_channel(settings.channel_pull_requests, msg_id)
            save_pr_map(pr_map)


async def handle_pull_request_event_with_retry(payload: Dict[str, Any], retries: int = MAX_RETRIES, delay: int = RETRY_DELAY) -> bool:
    """Process a pull_request event with simple retry logic."""
    for attempt in range(retries):
        try:
            await process_pull_request_event(payload)
            return True
        except Exception as exc:  # pragma: no cover - unexpected errors
            logger.error("Error handling pull request event: %s", exc)
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
    return False
