"""Discord bot client for handling GitHub webhook events."""

import discord
from discord.ext import commands
import asyncio
import logging
from typing import Optional

from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Discord bot intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance
bot = commands.Bot(command_prefix='!', intents=intents)


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
    
    async def send_to_channel(self, channel_id: int, content: str = None, embed: discord.Embed = None):
        """Send a message to a specific Discord channel."""
        if not self.ready:
            logger.warning("Bot is not ready yet, queuing message...")
            await asyncio.sleep(2)  # Wait a bit for bot to be ready
            
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Channel {channel_id} not found")
                # Try to send to bot logs channel instead
                channel = self.bot.get_channel(settings.channel_bot_logs)
                if channel:
                    await channel.send(f"⚠️ Failed to send message to channel {channel_id}. Original message: {content}")
                return
            
            if embed:
                await channel.send(embed=embed)
            else:
                await channel.send(content)
                
        except Exception as e:
            logger.error(f"Failed to send message to channel {channel_id}: {e}")
            # Try to send error to bot logs
            try:
                logs_channel = self.bot.get_channel(settings.channel_bot_logs)
                if logs_channel:
                    await logs_channel.send(f"❌ Error sending message: {str(e)}")
            except:
                pass  # Ignore if we can't even send to logs


@bot.event
async def on_ready():
    """Called when the bot has successfully connected to Discord."""
    logger.info(f'{bot.user} has connected to Discord!')
    discord_bot_instance.ready = True
    
    # Send startup message to bot logs channel
    try:
        logs_channel = bot.get_channel(settings.channel_bot_logs)
        if logs_channel:
            embed = discord.Embed(
                title="🤖 GitHub Discord Bot Online",
                description="Bot has successfully connected and is ready to receive GitHub webhooks.",
                color=discord.Color.green()
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


async def send_to_discord(channel_id: int, content: str = None, embed: discord.Embed = None):
    """Global function to send messages to Discord."""
    await discord_bot_instance.send_to_channel(channel_id, content, embed)
