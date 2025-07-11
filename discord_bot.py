"""Discord bot client for handling GitHub webhook events."""

import discord
from discord.ext import commands
import asyncio
import logging
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta
import aiohttp

from logging_config import setup_logging
from pr_map import load_pr_map, save_pr_map
from config import settings

from utils.embed_utils import split_embed_fields

from github_api import fetch_open_pull_requests
from formatters import format_pull_request_event
from commands.setup import setup_channels


import formatters

# Setup logging
setup_logging()
logger = logging.getLogger("discord_bot")

# Discord bot intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)
bot.add_command(setup_channels)

# Channels used during development that can be purged with the `!clear` command
# ``!clear`` should only wipe the pull requests channel during normal operation
DEV_CHANNELS: list[int] = [settings.channel_pull_requests]


@bot.command(name="clear")
async def clear_channels(ctx: commands.Context) -> None:
    """Clear messages from the pull requests channel."""
    for channel_id in DEV_CHANNELS:
        await discord_bot_instance.purge_old_messages(channel_id, 0)
    await ctx.send("✅ Pull requests channel cleared.")

# Maintain ``clear`` alias for backward compatibility in tests
clear = clear_channels


class DiscordBot:
    """Discord bot wrapper for sending GitHub webhook messages."""

    def __init__(self):
        self.bot = bot
        self.ready = False

    async def start(self):
        """Start the Discord bot."""
        try:
            await self.bot.start(settings.discord_bot_token)
        except Exception as e:
            logger.error(f"Failed to start Discord bot: {e}")
            raise

    async def delete_message_from_channel(
        self, channel_id: int, message_id: int
    ) -> bool:
        """Delete a specific message from a channel."""
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Channel {channel_id} not found for deletion")
                return False

            try:
                message = await channel.fetch_message(message_id)
            except Exception as fetch_err:
                logger.error(
                    f"Failed to fetch message {message_id} from channel {channel_id}: {fetch_err}"
                )
                return False

            try:
                await message.delete()
                return True
            except Exception as delete_err:
                logger.error(
                    f"Failed to delete message {message_id} from channel {channel_id}: {delete_err}"
                )
                return False
        except Exception as e:
            logger.error(f"Unexpected error deleting message: {e}")
            return False

    async def purge_old_messages(self, channel_id: int, days: int) -> None:
        """Purge messages older than the given number of days from a channel."""
        if not self.ready:
            await self.bot.wait_until_ready()

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
        except Exception as e:
            logger.error(f"Failed to purge messages in channel {channel_id}: {e}")
            try:
                logs_channel = self.bot.get_channel(settings.channel_bot_logs)
                if logs_channel:
                    await logs_channel.send(
                        f"❌ Failed to purge channel {channel_id}: {e}"
                    )
            except Exception:
                pass

    async def purge_channel(self, channel_id: int) -> None:
        """Delete **all** messages from the specified channel."""
        if not self.ready:
            await self.bot.wait_until_ready()

        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                raise ValueError(f"Channel {channel_id} not found")

            deleted = await channel.purge()

            if channel_id == settings.channel_pull_requests:
                if deleted:
                    save_pr_map({})
        except Exception as e:
            logger.error(f"Failed to purge channel {channel_id}: {e}")
            try:
                logs_channel = self.bot.get_channel(settings.channel_bot_logs)
                if logs_channel:
                    await logs_channel.send(f"❌ Failed to purge channel {channel_id}: {e}")
            except Exception:
                pass

    async def update_channel_name(self, channel_id: int, new_name: str) -> bool:
        """Rename a Discord channel."""
        if not self.ready:
            await self.bot.wait_until_ready()

        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Channel {channel_id} not found for rename")
                return False
            await channel.edit(name=new_name)
            return True
        except Exception as e:
            logger.error(f"Failed to rename channel {channel_id} to {new_name}: {e}")
            try:
                logs_channel = self.bot.get_channel(settings.channel_bot_logs)
                if logs_channel:
                    await logs_channel.send(f"❌ Failed to rename channel {channel_id}: {e}")
            except Exception:
                pass
            return False



    async def send_to_webhook(
        self, url: str, content: str = None, embed: discord.Embed = None
    ):

        """Send a message to a Discord webhook URL."""

        headers = {"Content-Type": "application/json"}
        data = {}
        if content:
            data["content"] = content
        if embed:
            data["embeds"] = [embed.to_dict()]

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status != 204:
                        logger.error(
                            f"Failed to send message to webhook: {response.status}"
                        )
                        logger.error(f"Response text: {await response.text()}")
                    else:
                        logger.info("Message sent successfully to webhook")
            except Exception as e:
                logger.error(f"Exception occurred while sending to webhook: {e}")

    async def send_to_channel(
        self, channel_id: int, content: str = None, embed: discord.Embed = None
    ) -> Optional[discord.Message]:
        """Send a message to a specific Discord channel and return the sent message."""
        if not self.ready:
            await self.bot.wait_until_ready()

        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Channel {channel_id} not found")
                # Try to send to bot logs channel instead
                channel = self.bot.get_channel(settings.channel_bot_logs)
                if channel:
                    await channel.send(
                        f"⚠️ Failed to send message to channel {channel_id}. Original message: {content}"
                    )
                return

            if embed:
                message = await channel.send(embed=embed)
            else:
                message = await channel.send(content)
            return message

        except Exception as e:
            logger.error(f"Failed to send message to channel {channel_id}: {e}")
            # Try to send error to bot logs
            try:
                logs_channel = self.bot.get_channel(settings.channel_bot_logs)
                if logs_channel:
                    await logs_channel.send(f"❌ Error sending message: {str(e)}")
            except Exception:
                pass  # Ignore if we can't even send to logs

        return None


@bot.event
async def on_ready():
    """Called when the bot has successfully connected to Discord."""
    logger.info(f"{bot.user} has connected to Discord!")
    discord_bot_instance.ready = True

    # Send startup message to bot logs channel
    try:
        logs_channel = bot.get_channel(settings.channel_bot_logs)
        if logs_channel:
            embed = discord.Embed(
                title="🤖 GitHub Discord Bot Online",
                description="Bot has successfully connected and is ready to receive GitHub webhooks.",
                color=discord.Color.green(),
            )
            await logs_channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Failed to send startup message: {e}")


@bot.event
async def on_error(event, *args, **kwargs):
    """Handle bot errors."""
    logger.error(f"Bot error in {event}: {args}, {kwargs}")


# Global bot instance
discord_bot_instance = DiscordBot()


async def send_to_discord(
    channel_id: int,
    content: str = None,
    embed: discord.Embed = None,
    use_webhook: bool = False,
):
    """Global function to send messages to Discord.

    Splits embeds exceeding Discord's 25 field limit into multiple messages.
    """

    embed_chunks: List[discord.Embed]
    if embed is not None:
        embed_chunks = split_embed_fields(embed)
    else:
        embed_chunks = [None]

    last_message = None
    for index, chunk in enumerate(embed_chunks):
        msg_content = content if index == 0 else None
        if use_webhook:
            webhook_url = getattr(settings, "discord_webhook_url", None)
            if webhook_url:
                await discord_bot_instance.send_to_webhook(
                    webhook_url, msg_content, chunk
                )
            else:
                last_message = await discord_bot_instance.send_to_channel(
                    channel_id,
                    content=msg_content,
                    embed=chunk,
                )
        else:
            last_message = await discord_bot_instance.send_to_channel(
                channel_id,
                content=msg_content,
                embed=chunk,
            )

    return last_message


# Duplicate clear command and function removed to fix CommandRegistrationError
# The original clear_channels function with @bot.command(name="clear") decorator
# is already defined above and handles channel clearing




@bot.command(name="update", aliases=["pr"])
async def update_pull_requests(ctx: commands.Context) -> None:
    """Ensure all active pull requests are listed in the pull requests channel."""
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
