import asyncio
import logging
from typing import Any, Dict

from discord_bot import send_to_discord, discord_bot_instance
from formatters import format_pull_request_event, format_merge_event
from pr_map import load_pr_map, save_pr_map
from config import settings

logger = logging.getLogger(__name__)


async def process_pull_request_event(payload: Dict[str, Any]) -> None:
    """Process a pull_request event and update message map."""
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    is_merged = pr.get("merged", False)
    repo = payload.get("repository", {})
    repo_name = repo.get("full_name", "")
    number = pr.get("number")
    pr_key = f"{repo_name}#{number}"

    if action in ("opened", "ready_for_review"):
        embed = format_pull_request_event(payload)
        message = await send_to_discord(settings.channel_pull_requests, embed=embed)
        if message:
            pr_map_data = load_pr_map()
            pr_map_data[pr_key] = message.id
            save_pr_map(pr_map_data)
    elif action == "closed":
        if is_merged:
            embed = format_merge_event(payload)
            await send_to_discord(settings.channel_code_merges, embed=embed)
        else:
            embed = format_pull_request_event(payload)
            await send_to_discord(settings.channel_pull_requests, embed=embed)

        pr_map_data = load_pr_map()
        message_id = pr_map_data.pop(pr_key, None)
        if message_id:
            await discord_bot_instance.delete_message_from_channel(
                settings.channel_pull_requests, message_id
            )
            save_pr_map(pr_map_data)
    else:
        embed = format_pull_request_event(payload)
        await send_to_discord(settings.channel_pull_requests, embed=embed)


async def handle_pull_request_event_with_retry(
    payload: Dict[str, Any], retries: int = 3, delay: float = 1.0
) -> bool:
    """Process a pull_request event with retry logic."""
    for attempt in range(1, retries + 1):
        try:
            await process_pull_request_event(payload)
            return True
        except Exception as exc:  # pragma: no cover - unexpected
            logger.error(f"Error processing pull_request event: {exc}")
            if attempt < retries:
                wait = delay * attempt
                logger.info(
                    f"Retrying pull_request event in {wait} seconds (attempt {attempt}/{retries})"
                )
                await asyncio.sleep(wait)
    return False

