import asyncio
import logging
from typing import Any, Dict

from config import settings
from discord_bot import discord_bot_instance
from pr_map import load_pr_map, save_pr_map
from formatters import format_pull_request_event, format_merge_event

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


async def handle_pull_request_event_with_retry(payload: Dict[str, Any]) -> bool:
    """Process pull request events with retry logic.

    The function sends formatted pull request messages to Discord and manages the
    tracking map for open pull requests. It retries on failure up to
    ``MAX_RETRIES`` times.
    """
    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            import main  # Local import so tests can patch send_to_discord

            action = payload.get("action", "")
            pr = payload.get("pull_request", {})
            repo = payload.get("repository", {}).get("full_name", "")
            number = pr.get("number")
            key = f"{repo}#{number}"

            # Determine destination and embed
            if action == "closed" and pr.get("merged"):
                embed = format_merge_event(payload)
                await main.send_to_discord(settings.channel_code_merges, embed=embed)

                # Remove stored message for this PR if present
                pr_map = load_pr_map()
                message_id = pr_map.pop(key, None)
                if message_id:
                    await discord_bot_instance.delete_message_from_channel(
                        settings.channel_pull_requests, message_id
                    )
                    save_pr_map(pr_map)
                return True

            # For all other actions send to pull requests channel
            embed = format_pull_request_event(payload)
            message = await main.send_to_discord(settings.channel_pull_requests, embed=embed)

            if action in {"opened", "ready_for_review"} and message:
                pr_map = load_pr_map()
                pr_map[key] = message.id
                save_pr_map(pr_map)
            elif action == "closed":
                pr_map = load_pr_map()
                message_id = pr_map.pop(key, None)
                if message_id:
                    await discord_bot_instance.delete_message_from_channel(
                        settings.channel_pull_requests, message_id
                    )
                    save_pr_map(pr_map)
            return True
        except Exception as exc:  # pragma: no cover - unexpected failures
            attempt += 1
            logger.error("Error handling pull request event: %s", exc)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)
            else:
                return False

    return False
