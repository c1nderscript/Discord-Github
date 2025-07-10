import asyncio
import logging
from typing import Any, Dict

from config import settings
from discord_bot import discord_bot_instance
from formatters import format_merge_event, format_pull_request_event
from pr_map import load_pr_map, save_pr_map

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


async def process_pull_request_event(payload: Dict[str, Any]) -> bool:
    """Handle a single pull_request event."""
    action = payload.get("action", "")
    pr = payload.get("pull_request", {})
    repo_name = payload.get("repository", {}).get("full_name", "")
    key = f"{repo_name}#{pr.get('number')}"

    import main  # local import so tests can patch send_to_discord

    try:
        if action == "closed" and pr.get("merged"):
            embed = format_merge_event(payload)
            await main.send_to_discord(settings.channel_code_merges, embed=embed)
            data = load_pr_map()
            msg_id = data.pop(key, None)
            if msg_id:
                await discord_bot_instance.delete_message_from_channel(
                    settings.channel_pull_requests, msg_id
                )
                save_pr_map(data)
        else:
            embed = format_pull_request_event(payload)
            message = await main.send_to_discord(
                settings.channel_pull_requests, embed=embed
            )
            if action in {"opened", "ready_for_review"} and message:
                data = load_pr_map()
                data[key] = message.id
                save_pr_map(data)
        return True
    except Exception as exc:  # pragma: no cover
        logger.error("Error handling pull_request event: %s", exc)
        return False


async def handle_pull_request_event_with_retry(
    payload: Dict[str, Any], retries: int = MAX_RETRIES, delay: int = RETRY_DELAY
) -> bool:
    """Process pull_request events with retry logic."""
    for attempt in range(retries):
        if await process_pull_request_event(payload):
            return True
        logger.warning(
            "Pull request handling failed, retry %s/%s in %ss",
            attempt + 1,
            retries,
            delay,
        )
        await asyncio.sleep(delay)
    return False
