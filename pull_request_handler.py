import asyncio
import logging
from typing import Any, Dict

from config import settings
from formatters import format_pull_request_event, format_merge_event
from pr_map import load_pr_map, save_pr_map


async def send_to_discord(*args, **kwargs):
    """Placeholder patched in tests."""
    raise NotImplementedError


class DummyDiscordBot:
    async def delete_message_from_channel(
        self, channel_id: int, message_id: int
    ) -> None:
        """Placeholder that does nothing."""
        return None


discord_bot_instance = DummyDiscordBot()

logger = logging.getLogger(__name__)


async def process_pull_request_event(payload: Dict[str, Any]) -> None:
    """Handle a single GitHub pull request event.

    This function formats the event, sends it to the appropriate Discord channel
    and updates the persisted message map. A ``ValueError`` is raised if the
    payload is missing required information.
    """

    action = payload.get("action", "")
    pr = payload.get("pull_request", {})
    repo_name = payload.get("repository", {}).get("full_name", "")
    number = pr.get("number")
    if not repo_name or number is None:
        raise ValueError("Invalid pull request payload")

    key = f"{repo_name}#{number}"
    pr_map_data = load_pr_map()

    if action == "closed" and pr.get("merged"):
        embed = format_merge_event(payload)
        channel = settings.channel_code_merges
    else:
        embed = format_pull_request_event(payload)
        channel = settings.channel_pull_requests

    message = await send_to_discord(channel, embed=embed)

    if action in {"opened", "ready_for_review"} and message:
        pr_map_data[key] = message.id
        save_pr_map(pr_map_data)
    elif action == "closed":
        message_id = pr_map_data.pop(key, None)
        if message_id:
            await discord_bot_instance.delete_message_from_channel(
                settings.channel_pull_requests, message_id
            )
            save_pr_map(pr_map_data)


async def handle_pull_request_event_with_retry(
    payload: Dict[str, Any], retries: int = 3, delay: float = 1.0
) -> bool:
    """Process a pull request event with retries.

    ``process_pull_request_event`` is invoked and, on failure, retried up to
    ``retries`` times. The wait time between attempts grows linearly based on
    ``delay``. ``True`` is returned on success, otherwise ``False``.
    """

    for attempt in range(1, retries + 1):
        try:
            await process_pull_request_event(payload)
            return True
        except Exception as exc:  # pragma: no cover - unexpected failures
            logger.error("Error processing pull_request event: %s", exc)
            if attempt < retries:
                wait = delay * attempt
                logger.info(
                    "Retrying pull_request event in %s seconds (attempt %s/%s)",
                    wait,
                    attempt,
                    retries,
                )
                await asyncio.sleep(wait)
    return False
