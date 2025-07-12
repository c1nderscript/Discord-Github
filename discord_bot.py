"""Discord bot client for handling GitHub webhook events with development management features."""

import discord
from discord.ext import commands
import logging
from typing import Optional, List
from datetime import datetime, timedelta
import aiohttp

from logging_config import setup_logging
from pr_map import load_pr_map, save_pr_map
from config import settings

from utils.embed_utils import split_embed_fields

from github_api import fetch_open_pull_requests
from commands.setup import setup_channels

import formatters

# Setup logging
setup_logging()
logger = logging.getLogger("discord_bot")

# Discord bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True  # Required for emoji reactions

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)
bot.add_command(setup_channels)


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

    async def clear_all_dynamic_channels(self) -> int:
        """Clear all dynamic channels and return count of channels cleared."""
        cleared_count = 0
        for channel_id in settings.all_dynamic_channels:
            try:
                await self.purge_channel(channel_id)
                cleared_count += 1
                logger.info(f"Cleared dynamic channel {channel_id}")
            except Exception as e:
                logger.error(f"Failed to clear channel {channel_id}: {e}")
        return cleared_count

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

            messages: List[discord.Message] = []
            embed_chunks = split_embed_fields(embed) if embed else [None]

            for index, chunk in enumerate(embed_chunks):
                msg_content = content if index == 0 else None
                message = await channel.send(content=msg_content, embed=chunk)
                messages.append(message)

            return messages[-1] if messages else None

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


# Global bot instance
discord_bot_instance = DiscordBot()


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
                title="🤖 GitHub Development Bot Online",
                description="Bot has successfully connected and is ready to manage development workflows.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="Features Active",
                value="• Hourly statistics updates\n• Dynamic channel management\n• Auto emoji reactions\n• Smart message cleanup",
                inline=False
            )
            await logs_channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Failed to send startup message: {e}")


@bot.event
async def on_reaction_add(reaction, user):
    """Handle emoji reactions for message deletion."""
    # Ignore bot reactions
    if user.bot:
        return
    
    # Check if this is a checkmark emoji
    if str(reaction.emoji) == "✅":
        # Check if this is the second checkmark (failsafe deletion)
        if reaction.count >= 2:
            try:
                await reaction.message.delete()
                logger.info(f"Message deleted via double checkmark failsafe by {user}")
                
                # Update PR map if this was a PR message
                if reaction.message.channel.id == settings.channel_pull_requests:
                    pr_map_data = load_pr_map()
                    for key, msg_id in list(pr_map_data.items()):
                        if msg_id == reaction.message.id:
                            pr_map_data.pop(key)
                            save_pr_map(pr_map_data)
                            break
                
                # Log to bot logs
                logs_channel = bot.get_channel(settings.channel_bot_logs)
                if logs_channel:
                    embed = discord.Embed(
                        title="🗑️ Message Deleted",
                        description=f"Message deleted via double checkmark failsafe",
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="User", value=str(user), inline=True)
                    embed.add_field(name="Channel", value=reaction.message.channel.mention, inline=True)
                    await logs_channel.send(embed=embed)
                    
            except Exception as e:
                logger.error(f"Failed to delete message via emoji: {e}")


@bot.event
async def on_error(event, *args, **kwargs):
    """Handle bot errors."""
    logger.error(f"Bot error in {event}: {args}, {kwargs}")


async def send_to_discord(
    channel_id: int,
    content: str = None,
    embed: discord.Embed = None,
    use_webhook: bool = False,
):
    """Global function to send messages to Discord."""
    embed_chunks: List[discord.Embed]
    if embed is not None:
        embed_chunks = split_embed_fields(embed)
    else:
        embed_chunks = [None]

    messages: List[discord.Message] = []
    for index, chunk in enumerate(embed_chunks):
        msg_content = content if index == 0 else None
        if use_webhook:
            webhook_url = getattr(settings, "discord_webhook_url", None)
            if webhook_url:
                await discord_bot_instance.send_to_webhook(
                    webhook_url, msg_content, chunk
                )
            else:
                message = await discord_bot_instance.send_to_channel(
                    channel_id,
                    content=msg_content,
                    embed=chunk,
                )
                if message:
                    messages.append(message)
        else:
            message = await discord_bot_instance.send_to_channel(
                channel_id,
                content=msg_content,
                embed=chunk,
            )
            if message:
                messages.append(message)

    if not messages:
        return None
    if len(messages) == 1:
        return messages[0]
    return messages


@bot.command(name="clear")
async def clear_all_channels(ctx: commands.Context) -> None:
    """Clear all content from all dynamic channels."""
    try:
        await ctx.send("🧹 Clearing all dynamic channels...")
        
        cleared_count = await discord_bot_instance.clear_all_dynamic_channels()
        
        embed = discord.Embed(
            title="✅ Channels Cleared",
            description=f"Successfully cleared {cleared_count} dynamic channels",
            color=discord.Color.green()
        )
        
        # Update channel names after clearing
        from main import update_dynamic_channel_names
        await update_dynamic_channel_names()
        
        await ctx.send(embed=embed)
        
        # Log to bot logs
        logs_channel = bot.get_channel(settings.channel_bot_logs)
        if logs_channel:
            embed = discord.Embed(
                title="🧹 Mass Channel Clear",
                description=f"All dynamic channels cleared by {ctx.author}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Channels Cleared", value=str(cleared_count), inline=True)
            await logs_channel.send(embed=embed)
            
    except Exception as e:
        logger.error(f"Failed to clear all channels: {e}")
        await ctx.send(f"❌ Failed to clear channels: {e}")


@bot.command(name="sync")
async def sync_channels(ctx: commands.Context) -> None:
    """Delete outdated messages, update channel numbers, and ensure only outstanding pull requests are in channels."""
    try:
        await ctx.send("🔄 Syncing channels...")
        
        # Import functions from main
        from main import update_dynamic_channel_names, update_all_statistics
        from cleanup import cleanup_pr_messages
        
        # Clean up closed PR messages
        await cleanup_pr_messages()
        
        # Update channel names based on current message counts
        await update_dynamic_channel_names()
        
        # Update statistics
        await update_all_statistics()
        
        # Refresh open pull requests
        await update_pull_requests(ctx, silent=True)
        
        embed = discord.Embed(
            title="✅ Sync Complete",
            description="All channels have been synchronized",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Actions Performed",
            value="• Cleaned up outdated messages\n• Updated channel numbers\n• Refreshed pull requests\n• Updated statistics",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
        # Log to bot logs
        logs_channel = bot.get_channel(settings.channel_bot_logs)
        if logs_channel:
            embed = discord.Embed(
                title="🔄 Channel Sync",
                description=f"Channels synchronized by {ctx.author}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            await logs_channel.send(embed=embed)
            
    except Exception as e:
        logger.error(f"Failed to sync channels: {e}")
        await ctx.send(f"❌ Failed to sync channels: {e}")


@bot.command(name="update", aliases=["pr"])
async def update_pull_requests(ctx: commands.Context, silent: bool = False) -> None:
    """Ensure all active pull requests are listed in the pull requests channel."""
    try:
        if not silent:
            await ctx.send("🔄 Updating pull requests...")
            
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
                # Add checkmark emoji
                await message.add_reaction("✅")
                pr_map_data[key] = message.id
                added += 1
                
        if added:
            save_pr_map(pr_map_data)
            
        if not silent:
            await ctx.send(f"✅ Added {added} pull request{'s' if added != 1 else ''}.")
            
        return added
        
    except Exception as e:
        logger.error(f"Failed to update pull requests: {e}")
        if not silent:
            await ctx.send(f"❌ Failed to update pull requests: {e}")
        return 0
