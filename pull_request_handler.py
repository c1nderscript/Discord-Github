import asyncio
from config import settings
from discord_bot import discord_bot_instance
import pr_map

async def handle_pull_request_event_with_retry(payload: dict) -> bool:
    """Minimal PR handler used for tests."""
    import main  # Imported here so tests can patch send_to_discord

    action = payload.get("action")
    repo = payload.get("repository", {}).get("full_name")
    number = payload.get("pull_request", {}).get("number")
    if not repo or number is None:
        return False

    if action == "opened":
        message = await main.send_to_discord(settings.channel_pull_requests, embed=None)
        data = pr_map.load_pr_map()
        data[f"{repo}#{number}"] = message.id
        pr_map.save_pr_map(data)
        return True

    if action == "closed" and payload["pull_request"].get("merged"):
        key = f"{repo}#{number}"
        message_id = pr_map.load_pr_map().get(key)
        if message_id:
            await discord_bot_instance.delete_message_from_channel(
                settings.channel_pull_requests, message_id
            )
            data = pr_map.load_pr_map()
            data.pop(key, None)
            pr_map.save_pr_map(data)
        return True

    return True
