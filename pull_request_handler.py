
import logging
from typing import Dict

from config import settings
from discord_bot import discord_bot_instance


"""Handler for GitHub pull request events."""

import logging
from typing import Any

"""Simplified pull request event handler used for tests."""


import asyncio
from typing import Dict
from discord import Embed

import asyncio
import logging

from typing import Dict, Any


from config import settings
from discord_bot import discord_bot_instance
import pr_map


async def handle_pull_request_event_with_retry(payload: dict) -> bool:
    """Handle pull request events with basic map management."""
    action = payload.get("action")
    repo = payload["repository"]["full_name"]
    number = payload["pull_request"]["number"]
    key = f"{repo}#{number}"

    from main import send_to_discord

    if action == "opened":
        message = await send_to_discord(settings.channel_pull_requests, embed=None)
        data = pr_map.load_pr_map()
        data[key] = message.id
        pr_map.save_pr_map(data)
    elif action == "closed" and payload["pull_request"].get("merged"):
        data = pr_map.load_pr_map()
        message_id = data.get(key)
        if message_id:
            await discord_bot_instance.delete_message_from_channel(
                settings.channel_pull_requests, message_id
            )
            del data[key]
            pr_map.save_pr_map(data)
    return True

from formatters import format_pull_request_event
from typing import Dict



from config import settings
from discord_bot import discord_bot_instance
from formatters import format_pull_request_event, format_merge_event
from pr_map import load_pr_map, save_pr_map


logger = logging.getLogger(__name__)


async def handle_pull_request_event_with_retry(payload: dict) -> bool:
    """Process pull request events with basic retry logic."""
    from main import send_to_discord
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {}).get("full_name", "")
    key = f"{repo}#{pr.get('number')}"

    pr_map = load_pr_map()



async def handle_pull_request_event_with_retry(payload: Dict, retries: int = 3) -> bool:
    """Handle pull_request events with a simple retry loop."""
    attempt = 0
    while attempt < retries:
        try:
            await _handle_pull_request_event(payload)
            return True
        except Exception:
            attempt += 1
            await asyncio.sleep(1)
    return False


async def _handle_pull_request_event(payload: Dict) -> None:
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo_name = payload.get("repository", {}).get("full_name", "")

    import main as main_module
    embed = format_pull_request_event(payload)
    if action == "closed" and pr.get("merged"):
        await main_module.send_to_discord(settings.channel_code_merges, embed=embed)
        pr_map = load_pr_map()
        key = f"{repo_name}#{pr.get('number')}"
        msg_id = pr_map.pop(key, None)
        if msg_id:
            await discord_bot_instance.delete_message_from_channel(
                settings.channel_pull_requests, msg_id
            )
        save_pr_map(pr_map)
    else:
        message = await main_module.send_to_discord(
            settings.channel_pull_requests, embed=embed
        )
        if action == "opened" and message:
            pr_map = load_pr_map()
            pr_map[f"{repo_name}#{pr.get('number')}"] = message.id
            save_pr_map(pr_map)

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


from pr_map import load_pr_map, save_pr_map
from formatters import format_pull_request_event, format_merge_event

logger = logging.getLogger(__name__)



async def handle_pull_request_event_with_retry(payload: Dict[str, Any]) -> bool:
    """Simplified pull request handler for tests."""
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    repo_name = repo.get("full_name")
    number = pr.get("number")
    key = f"{repo_name}#{number}"

    from main import send_to_discord

    embed = format_pull_request_event(payload)
    message = await send_to_discord(settings.channel_pull_requests, embed=embed)

    if action == "opened":
        if hasattr(message, "id"):
            data = pr_map.load_pr_map()
            data[key] = message.id
            pr_map.save_pr_map(data)
    elif action == "closed":
        data = pr_map.load_pr_map()
        message_id = data.pop(key, None)
        if message_id:
            await discord_bot_instance.delete_message_from_channel(
                settings.channel_pull_requests,
                message_id,
            )
            pr_map.save_pr_map(data)


async def handle_pull_request_event_with_retry(payload: Dict) -> bool:
    """Handle pull request events and maintain message map."""
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {}).get("full_name")
    if not repo or "number" not in pr:
        logger.error("Invalid pull request payload")
        return False

    pr_key = f"{repo}#{pr['number']}"

    # Import here to avoid circular dependency
    from main import send_to_discord

    if action == "opened":
        embed = format_pull_request_event(payload)
        message = await send_to_discord(settings.channel_pull_requests, embed=embed)
        if message:


            pr_map[key] = message.id
            save_pr_map(pr_map)
        return True

    if action == "closed" and pr.get("merged"):
        message_id = pr_map.pop(key, None)


            data = load_pr_map()
            data[pr_key] = message.id
            save_pr_map(data)
        return True

    if action == "closed":
        data = load_pr_map()
        message_id = data.pop(pr_key, None)

        if message_id:
            await discord_bot_instance.delete_message_from_channel(
                settings.channel_pull_requests, message_id
            )


            save_pr_map(pr_map)
        embed = format_merge_event(payload)
        await send_to_discord(settings.channel_code_merges, embed=embed)


        save_pr_map(data)
        if pr.get("merged"):
            embed = format_merge_event(payload)
            await send_to_discord(settings.channel_code_merges, embed=embed)
        else:
            embed = format_pull_request_event(payload)
            await send_to_discord(settings.channel_pull_requests, embed=embed)

        return True

    embed = format_pull_request_event(payload)
    await send_to_discord(settings.channel_pull_requests, embed=embed)
    return True

