import asyncio
from typing import Dict
from discord import Embed

from config import settings
from discord_bot import discord_bot_instance
from formatters import format_pull_request_event, format_merge_event
from pr_map import load_pr_map, save_pr_map


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
