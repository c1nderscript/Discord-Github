import aiohttp
from config import settings
from pr_map import load_pr_map, save_pr_map
from discord_bot import discord_bot_instance


async def cleanup_pr_messages() -> None:
    """Remove messages for closed PRs and update the map."""
    pr_map = load_pr_map()
    if not pr_map:
        return

    headers = {"Accept": "application/vnd.github.v3+json"}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"

    async with aiohttp.ClientSession() as session:
        for pr_key, message_id in list(pr_map.items()):
            repo, number = pr_key.split("#")
            url = f"https://api.github.com/repos/{repo}/pulls/{number}"
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()

            if data.get("state") == "closed":
                await discord_bot_instance.delete_message_from_channel(
                    settings.channel_pull_requests,
                    message_id,
                )
                pr_map.pop(pr_key)

    save_pr_map(pr_map)
