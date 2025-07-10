import asyncio
import logging
from typing import Any, Dict

from config import settings
from formatters import format_pull_request_event, format_merge_event
from pr_map import load_pr_map, save_pr_map


async def send_to_discord(*args, **kwargs):
    """Proxy send_to_discord to avoid importing discord_bot at module load."""
    from discord_bot import send_to_discord as _send
    return await _send(*args, **kwargs)


def _bot_instance():
    """Return the discord bot instance lazily."""
    from discord_bot import discord_bot_instance
    return discord_bot_instance

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 2.0


def _get_pr_key(payload: Dict[str, Any]) -> str:
    """Return the map key for the given pull request payload."""
    repo = payload.get("repository", {}).get("full_name", "")
    number = payload.get("pull_request", {}).get("number")
    return f"{repo}#{number}"


async def _process_pull_request_event(payload: Dict[str, Any]) -> bool:
    """Handle a single pull_request event and update the message map."""
    try:
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})
        merged = pr.get("merged", False)

        if action == "closed" and merged:
            embed = format_merge_event(payload)
            channel_id = settings.channel_code_merges
        else:
            embed = format_pull_request_event(payload)
            channel_id = settings.channel_pull_requests

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
                await _bot_instance().delete_message_from_channel(
                    settings.channel_pull_requests,
                    message_id,
                )
                save_pr_map(pr_map_data)
        return True
    except Exception as exc:  # pragma: no cover - unexpected errors
        logger.error("Error handling pull_request event: %s", exc)
        return False


async def handle_pull_request_event_with_retry(
    payload: Dict[str, Any],
    retries: int = DEFAULT_MAX_RETRIES,
    delay: float = DEFAULT_RETRY_DELAY,
) -> bool:
    """Process a pull_request event with retry logic."""
    for attempt in range(1, retries + 1):
        try:
            result = await _process_pull_request_event(payload)
            success = result is not False
        except Exception as exc:  # pragma: no cover - unexpected errors
            logger.error("Error processing pull_request event: %s", exc)
            success = False

        if success:
            return True

        if attempt < retries:
            logger.warning(
                "Pull request handling failed, retry %s/%s in %ss",
                attempt,
                retries,
                delay,
            )
            await asyncio.sleep(delay)
            delay *= 2
    return False
