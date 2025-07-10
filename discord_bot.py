"""Discord bot client for handling GitHub webhook events."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Any

import aiohttp
import discord
from discord.ext import commands

from logging_config import setup_logging
from pr_map import load_pr_map, save_pr_map
from config import settings
import formatters

# Setup logging
setup_logging()
logger = logging.getLogger("discord_bot")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Channels used during development that can be purged with the `!clear` command
DEV_CHANNELS: list[int] = [
    settings.channel_commits,
    settings.channel_pull_requests,
    settings.channel_releases,
    settings.channel_code_merges,
    settings.channel_commits_overview,
    settings.channel_pull_requests_overview,
    settings.channel_merges_overview,
    settings.channel_issues,
    settings.channel_deployment_status,
    settings.channel_ci_builds,
    settings.channel_gollum,
    settings.channel_bot_logs,
]


class DiscordBot:
    """Discord bot wrapper for sending GitHub webhook messages."""

    def __init__(self) -> None:
        self.bot = bot
        self.ready = False

    async def start(self) -> None:
        """Start the Discord bot."""
        try:
            await self.bot.start(settings.discord_bot_token)
        except Exception as exc:
            logger.error("Failed to start Discord bot: %s", exc)
            raise

    async def delete_message_from_channel(self, channel_id: int, message_id: int) -> bool:
        """Delete a specific message from a channel."""
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error("Channel %s not found for deletion", channel_id)
                return False

            try:
                message = await channel.fetch_message(message_id)
            except Exception as fetch_err:
                logger.error(
                    "Failed to fetch message %s from channel %s: %s",
                    message_id,
                    channel_id,
                    fetch_err,
                )
                return False

            try:
                await message.delete()
                return True
            except Exception as delete_err:
                logger.error(
                    "Failed to delete message %s from channel %s: %s",
                    message_id,
                    channel_id,
                    delete_err,
                )
                return False
        except Exception as exc:
            logger.error("Unexpected error deleting message: %s", exc)
            return False

    async def purge_old_messages(self, channel_id: int, days: int) -> None:
        """Purge messages older than ``days`` from a channel."""
        if not self.ready:
            # If the bot isn't running (e.g., during tests) skip purge logic
            return

        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                raise ValueError(f"Channel {channel_id} not found")

            cutoff = datetime.utcnow() - timedelta(days=days)
            deleted = await channel.purge(before=cutoff)

            if channel_id == settings.channel_pull_requests:
                deleted_ids = {msg.id for msg in deleted}
                if deleted_ids:
                    pr_map_data = load_pr_map()
                    updated = False
                    for key, msg_id in list(pr_map_data.items()):
                        if msg_id in deleted_ids:
                            pr_map_data.pop(key)
                            updated = True
                    if updated:
                        save_pr_map(pr_map_data)
        except Exception as exc:
            logger.error("Failed to purge messages in channel %s: %s", channel_id, exc)
            try:
                logs_channel = self.bot.get_channel(settings.channel_bot_logs)
                if logs_channel:
                    await logs_channel.send(f"❌ Failed to purge channel {channel_id}: {exc}")
            except Exception:
                pass

    async def purge_channel(self, channel_id: int) -> None:
        """Delete **all** messages from the specified channel."""
        if not self.ready:
            # If the bot isn't running (e.g., during tests) skip purge logic
            return

        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                raise ValueError(f"Channel {channel_id} not found")

            deleted = await channel.purge()

            if channel_id == settings.channel_pull_requests and deleted:
                save_pr_map({})
        except Exception as exc:
            logger.error("Failed to purge channel %s: %s", channel_id, exc)
            try:
                logs_channel = self.bot.get_channel(settings.channel_bot_logs)
                if logs_channel:
                    await logs_channel.send(f"❌ Failed to purge channel {channel_id}: {exc}")
            except Exception:
                pass

    async def update_channel_name(self, channel_id: int, new_name: str) -> bool:
        """Rename a Discord channel."""
        if not self.ready:
            # If the bot isn't running (e.g., during tests) skip rename logic
            return False

        channel = self.bot.get_channel(channel_id)
        if not channel:
            logger.error("Channel %s not found for rename", channel_id)
            return False
        try:
            await channel.edit(name=new_name)
            return True
        except Exception as exc:
            logger.error("Failed to rename channel %s to %s: %s", channel_id, new_name, exc)
            try:
                logs_channel = self.bot.get_channel(settings.channel_bot_logs)
                if logs_channel:
                    await logs_channel.send(f"❌ Failed to rename channel {channel_id}: {exc}")
            except Exception:
                pass
            return False

    async def send_to_webhook(
        self, url: str, content: str | None = None, embed: discord.Embed | None = None
    ) -> None:
        """Send a message to a Discord webhook URL."""
        headers = {"Content-Type": "application/json"}
        data: dict[str, Any] = {}
        if content:
            data["content"] = content
        if embed:
            data["embeds"] = [embed.to_dict()]

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status != 204:
                        logger.error(
                            "Failed to send message to webhook: %s", response.status
                        )
                        logger.error("Response text: %s", await response.text())
                    else:
                        logger.info("Message sent successfully to webhook")
            except Exception as exc:
                logger.error("Exception occurred while sending to webhook: %s", exc)

    async def send_to_channel(
        self, channel_id: int, content: str | None = None, embed: discord.Embed | None = None
    ) -> Optional[discord.Message]:
        """Send a message to a specific Discord channel and return the sent message."""
        if not self.ready:
            logger.warning("Bot is not ready yet, queuing message...")
            await asyncio.sleep(2)

        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error("Channel %s not found", channel_id)
                channel = self.bot.get_channel(settings.channel_bot_logs)
                if channel:
                    await channel.send(
                        f"⚠️ Failed to send message to channel {channel_id}. Original message: {content}"
                    )
                return None

            if embed:
                message = await channel.send(embed=embed)
            else:
                message = await channel.send(content)
            return message
        except Exception as exc:
            logger.error("Failed to send message to channel %s: %s", channel_id, exc)
            try:
                logs_channel = self.bot.get_channel(settings.channel_bot_logs)
                if logs_channel:
                    await logs_channel.send(f"❌ Error sending message: {exc}")
            except Exception:
                pass
            return None


@bot.event
async def on_ready() -> None:
    """Called when the bot has successfully connected to Discord."""
    logger.info("%s has connected to Discord!", bot.user)
    discord_bot_instance.ready = True

    try:
        logs_channel = bot.get_channel(settings.channel_bot_logs)
        if logs_channel:
            embed = discord.Embed(
                title="🤖 GitHub Discord Bot Online",
                description="Bot has successfully connected and is ready to receive GitHub webhooks.",
                color=discord.Color.green(),
            )
            await logs_channel.send(embed=embed)
    except Exception as exc:
        logger.error("Failed to send startup message: %s", exc)


@bot.event
async def on_error(event: str, *args: Any, **kwargs: Any) -> None:
    """Handle bot errors."""
    logger.error("Bot error in %s: %s, %s", event, args, kwargs)


# Global bot instance
discord_bot_instance = DiscordBot()


async def send_to_discord(
    channel_id: int,
    content: str | None = None,
    embed: discord.Embed | None = None,
    use_webhook: bool = False,
) -> Optional[discord.Message]:
    """Global helper to send messages to Discord."""
    if use_webhook:
        webhook_url = getattr(settings, "discord_webhook_url", None)
        if webhook_url:
            await discord_bot_instance.send_to_webhook(webhook_url, content, embed)
            return None
        return await discord_bot_instance.send_to_channel(channel_id, content, embed)
    return await discord_bot_instance.send_to_channel(channel_id, content, embed)


@bot.command(name="clear")
async def clear_channels(ctx: commands.Context) -> None:
    """Clear all messages from development channels."""
    for channel_id in DEV_CHANNELS:
        await discord_bot_instance.purge_old_messages(channel_id, 0)

    channels_to_purge = [
        settings.channel_commits,
        settings.channel_pull_requests,
        settings.channel_releases,
        settings.channel_code_merges,
        settings.channel_ci_builds,
        settings.channel_deployment_status,
        settings.channel_gollum,
    ]
    for channel_id in channels_to_purge:
        await discord_bot_instance.purge_channel(channel_id)

    await ctx.send("✅ Channels cleared.")


clear = clear_channels


@bot.command(name="update")
async def update_pull_requests(ctx: commands.Context) -> None:
    """Ensure all active pull requests are listed in the pull requests channel."""
    from github_api import fetch_open_pull_requests

    pr_map_data = load_pr_map()
    open_prs = await fetch_open_pull_requests()
    added = 0
    for repo, pr in open_prs:
        key = f"{repo}#{pr.get('number')}"
        if key in pr_map_data:
            continue
        payload = {
            "action": "opened",
            "pull_request": pr,
            "repository": {"full_name": repo},
        }
        embed = formatters.format_pull_request_event(payload)
        message = await send_to_discord(settings.channel_pull_requests, embed=embed)
        if message:
            pr_map_data[key] = message.id
            added += 1
    if added:
        save_pr_map(pr_map_data)
    await ctx.send(f"Added {added} pull request{'s' if added != 1 else ''}.")


update = update_pull_requests
