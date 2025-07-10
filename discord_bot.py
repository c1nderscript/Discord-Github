import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, List

import discord
from discord.ext import commands

from logging_config import setup_logging
from pr_map import load_pr_map, save_pr_map
from config import settings
from github_api import fetch_open_pull_requests
from formatters import format_pull_request_event

setup_logging()
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DEV_CHANNELS: List[int] = [
    settings.channel_commits,
    settings.channel_pull_requests,
    settings.channel_releases,
    settings.channel_code_merges,
    settings.channel_ci_builds,
    settings.channel_deployment_status,
    settings.channel_gollum,
]


class DiscordBot:
    """Minimal Discord bot wrapper used in tests."""

    def __init__(self) -> None:
        self.bot = bot
        self.ready = False

    async def start(self) -> None:
        await self.bot.start(settings.discord_bot_token)

    async def delete_message_from_channel(self, channel_id: int, message_id: int) -> bool:
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return False
        try:
            message = await channel.fetch_message(message_id)
            await message.delete()
            return True
        except Exception as exc:  # pragma: no cover - network errors
            logger.error("Failed to delete message %s from %s: %s", message_id, channel_id, exc)
            return False

    async def purge_channel(self, channel_id: int) -> None:
        channel = self.bot.get_channel(channel_id)
        if channel:
            await channel.purge()

    async def purge_old_messages(self, channel_id: int, days: int) -> None:
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return
        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted = await channel.purge(before=cutoff)
        if channel_id == settings.channel_pull_requests:
            ids = {m.id for m in deleted}
            if ids:
                data = load_pr_map()
                updated = False
                for key, msg_id in list(data.items()):
                    if msg_id in ids:
                        data.pop(key)
                        updated = True
                if updated:
                    save_pr_map(data)

    async def update_channel_name(self, channel_id: int, new_name: str) -> bool:
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return False
        try:
            await channel.edit(name=new_name)
            return True
        except Exception as exc:  # pragma: no cover - network errors
            logger.error("Failed to rename channel %s: %s", channel_id, exc)
            return False

    async def send_to_channel(self, channel_id: int, content: str | None = None, embed: discord.Embed | None = None) -> Optional[discord.Message]:
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return None
        if embed is not None:
            return await channel.send(embed=embed)
        if content is not None:
            return await channel.send(content)
        return None


# Global bot instance
discord_bot_instance = DiscordBot()


async def send_to_discord(channel_id: int, content: str | None = None, embed: discord.Embed | None = None) -> Optional[discord.Message]:
    return await discord_bot_instance.send_to_channel(channel_id, content, embed)


@bot.event
async def on_ready() -> None:
    discord_bot_instance.ready = True
    logger.info("%s connected", bot.user)


@bot.command(name="clear")
async def clear_channels(ctx: commands.Context) -> None:
    for ch in DEV_CHANNELS:
        await discord_bot_instance.purge_channel(ch)
        await discord_bot_instance.purge_old_messages(ch, 0)
    await ctx.send("✅ Channels cleared.")


@bot.command(name="update")
async def update_pull_requests(ctx: commands.Context) -> None:
    prs = await fetch_open_pull_requests()
    pr_map_data = load_pr_map()
    added = 0
    for repo, pr in prs:
        payload = {
            "action": "opened",
            "pull_request": pr,
            "repository": {"full_name": repo},
        }
        embed = format_pull_request_event(payload)
        message = await send_to_discord(settings.channel_pull_requests, embed=embed)
        if message:
            key = f"{repo}#{pr['number']}"
            if key not in pr_map_data:
                pr_map_data[key] = message.id
                added += 1
    if added:
        save_pr_map(pr_map_data)
    await ctx.send(f"Added {added} pull request{'s' if added != 1 else ''}.")
