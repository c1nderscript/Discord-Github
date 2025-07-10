"""Utilities for handling GitHub pull request events."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from config import settings
from discord_bot import send_to_discord, discord_bot_instance
from formatters import format_merge_event, format_pull_request_event
from pr_map import load_pr_map, save_pr_map


logger = logging.getLogger(__name__)


async def process_pull_request_event(payload: Dict[str, Any]) -> None:
    """Handle a single ``pull_request`` event.

    This function sends the appropriate embed to Discord and updates the
    ``pr_map`` used to track open pull requests.
    """

    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})

    repo_name = repo.get("full_name", "")
    number = pr.get("number")
    pr_key = f"{repo_name}#{number}"

    if action in {"opened", "ready_for_review"}:
        embed = format_pull_request_event(payload)
        message = await send_to_discord(settings.channel_pull_requests, embed=embed)
        if message:
            pr_map = load_pr_map()
            pr_map[pr_key] = message.id
            save_pr_map(pr_map)
        return

    if action == "closed":
        if pr.get("merged"):
            embed = format_merge_event(payload)
            await send_to_discord(settings.channel_code_merges, embed=embed)
        else:
            embed = format_pull_request_event(payload)
            await send_to_discord(settings.channel_pull_requests, embed=embed)

        pr_map = load_pr_map()
        message_id = pr_map.pop(pr_key, None)
        if message_id:
            await discord_bot_instance.delete_message_from_channel(
                settings.channel_pull_requests, message_id
            )
            save_pr_map(pr_map)
        return

    embed = format_pull_request_event(payload)
    await send_to_discord(settings.channel_pull_requests, embed=embed)


async def handle_pull_request_event_with_retry(
    payload: Dict[str, Any], retries: int = 3, delay: float = 1.0
) -> bool:
    """Process a pull request event with retry logic.

    Parameters
    ----------
    payload:
        The GitHub pull request event payload.
    retries:
        Total number of attempts before giving up.
    delay:
        Initial delay between retries in seconds.

    Returns
    -------
    bool
        ``True`` if the event was processed successfully, ``False`` otherwise.
    """

    for attempt in range(1, retries + 1):
        try:
            await process_pull_request_event(payload)
            return True
        except Exception as exc:  # pragma: no cover - unexpected failures
            logger.error("Error processing pull_request event: %s", exc)
            if attempt < retries:
                await asyncio.sleep(delay)

    return False

