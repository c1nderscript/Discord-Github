import asyncio
import logging
from typing import Any, Dict

from config import settings
from discord_bot import send_to_discord, discord_bot_instance
from formatters import format_pull_request_event, format_merge_event
from pr_map import load_pr_map, save_pr_map

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
INITIAL_DELAY = 2


def _get_pr_key(payload: Dict[str, Any]) -> str:
    """Return a unique key for a pull request payload."""
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {}).get("full_name", "")
    return f"{repo}#{pr.get('number')}"


async def _process_pull_request_event(payload: Dict[str, Any]) -> bool:
    """Handle a single pull_request event.

    The function sends the formatted embed to Discord and updates the
    pull request message map. It returns ``True`` on success and ``False``
    if the payload is invalid or an unexpected error occurs.
    """
    try:
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {}).get("full_name", "")

        if not repo or pr.get("number") is None:
            logger.error("Invalid pull request payload")
            return False

        if action == "closed" and pr.get("merged"):
            embed = format_merge_event(payload)
            channel_id = settings.channel_code_merges
        else:
            embed = format_pull_request_event(payload)
            channel_id = settings.channel_pull_requests

        message = await send_to_discord(channel_id, embed=embed)

        pr_key = _get_pr_key(payload)
        pr_map_data: Dict[str, int] = load_pr_map()

        if action in {"opened", "ready_for_review"} and message:
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
        logger.error("Error handling pull_request event: %s", exc)
        return False


async def handle_pull_request_event_with_retry(
    payload: Dict[str, Any], retries: int = MAX_RETRIES, delay: float = INITIAL_DELAY
) -> bool:
    """Process a pull request event with retry logic.

    ``retries`` specifies how many attempts should be made if processing
    fails. ``delay`` is the initial wait time between retries which is
    doubled after each failure.
    """
    current_delay = delay
    for attempt in range(1, retries + 1):
        if await _process_pull_request_event(payload):
            return True
        if attempt < retries:
            logger.warning(
                "Pull request handling failed, retry %s/%s in %ss",
                attempt,
                retries,
                current_delay,
            )
            await asyncio.sleep(current_delay)
            current_delay *= 2
    return False


# Backwards compatibility for tests
process_pull_request_event = _process_pull_request_event
