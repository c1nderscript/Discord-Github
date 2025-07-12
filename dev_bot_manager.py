"""Development Bot Manager - Central coordination for GitHub development workflow automation.

This module provides centralized management for:
- Hourly statistics updates for GitHub Statistics channels
- Dynamic channel message counting and naming
- Automated emoji reactions and message lifecycle management
- Command channel maintenance and logging coordination
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import discord

from config import settings
from discord_bot import discord_bot_instance, send_to_discord
from github_utils import fetch_detailed_stats, get_repository_count
from stats_map import load_stats_map, save_stats_map
from pull_request_handler import cleanup_resolved_prs, auto_manage_pr_reactions

logger = logging.getLogger(__name__)


class DevelopmentBotManager:
    """Central manager for development bot automation features."""
    
    def __init__(self):
        self.last_stats_update = None
        self.last_commands_update = None
        self.stats_messages = {}
        
    async def start_automation_tasks(self):
        """Start all automation tasks for the development bot."""
        logger.info("Starting development bot automation tasks...")
        
        # Wait for Discord bot to be ready
        while not discord_bot_instance.ready:
            await asyncio.sleep(1)
        
        # Start periodic tasks
        asyncio.create_task(self.run_hourly_statistics_update())
        asyncio.create_task(self.run_hourly_commands_maintenance())
        asyncio.create_task(self.run_dynamic_channel_monitoring())
        asyncio.create_task(self.run_reaction_management())
        
        # Initial setup
        await self.initial_setup()
        
    async def initial_setup(self):
        """Perform initial setup tasks when bot starts."""
        try:
            # Update statistics immediately
            await self.update_all_statistics()
            
            # Set up commands channel
            await self.setup_commands_channel()
            
            # Update dynamic channel names
            await self.update_dynamic_channel_names()
            
            # Send startup notification
            await self.send_startup_notification()
            
            logger.info("Development bot initial setup completed")
            
        except Exception as e:
            logger.error(f"Error in initial setup: {e}")
    
    async def run_hourly_statistics_update(self):
        """Run statistics updates every hour."""
        while True:
            try:
                await asyncio.sleep(3600)  # 1 hour
                await self.update_all_statistics()
                self.last_stats_update = datetime.utcnow()
                logger.info("Completed hourly statistics update")
            except Exception as e:
                logger.error(f"Error in hourly statistics update: {e}")
    
    async def run_hourly_commands_maintenance(self):
        """Run commands channel maintenance every hour."""
        while True:
            try:
                await asyncio.sleep(3600)  # 1 hour
                await self.setup_commands_channel()
                self.last_commands_update = datetime.utcnow()
                logger.info("Completed hourly commands maintenance")
            except Exception as e:
                logger.error(f"Error in commands maintenance: {e}")
    
    async def run_dynamic_channel_monitoring(self):
        """Monitor and update dynamic channel names every 10 minutes."""
        while True:
            try:
                await asyncio.sleep(600)  # 10 minutes
                await self.update_dynamic_channel_names()
            except Exception as e:
                logger.error(f"Error in dynamic channel monitoring: {e}")
    
    async def run_reaction_management(self):
        """Manage emoji reactions every 30 minutes."""
        while True:
            try:
                await asyncio.sleep(1800)  # 30 minutes
                await auto_manage_pr_reactions()
                await self.ensure_dynamic_channel_reactions()
            except Exception as e:
                logger.error(f"Error in reaction management: {e}")
    
    async def update_all_statistics(self):
        """Update all GitHub statistics channels."""
        try:
            # Fetch comprehensive statistics
            stats_data = await fetch_detailed_stats()
            
            if not stats_data:
                logger.warning("No statistics data received")
                return
            
            totals = stats_data.get("totals", {})
            repo_stats = stats_data.get("repositories", [])
            repo_count = stats_data.get("repository_count", 0)
            contributions = stats_data.get("contributions", {})
            
            # Calculate statistics
            stats_values = {
                "commits": totals.get("commits", 0),
                "pull-requests": totals.get("pull_requests", 0),
                "merges": totals.get("merged_pull_requests", 0),
                "repos": repo_count,
                "contributions": contributions.get("total_contributions", 0),
            }
            
            # Update each statistics channel
            channel_mapping = {
                "commits": settings.channel_stats_commits,
                "pull-requests": settings.channel_stats_pull_requests,
                "merges": settings.channel_stats_merges,
                "repos": settings.channel_stats_repos,
                "contributions": settings.channel_stats_contributions,
            }
            
            for stat_name, channel_id in channel_mapping.items():
                count = stats_values[stat_name]
                
                # Update channel name
                await discord_bot_instance.update_channel_name(
                    channel_id, f"{count}-{stat_name}"
                )
                
                # Update statistics embed
                embed = await self.create_statistics_embed(stat_name, repo_stats, totals, contributions)
                await self.update_statistics_message(channel_id, embed, stat_name)
            
            logger.info(f"Updated GitHub statistics: {stats_values}")
            
        except Exception as e:
            logger.error(f"Failed to update GitHub statistics: {e}")
            await self.log_error("Statistics Update Failed", str(e))
    
    async def create_statistics_embed(self, stat_type: str, repo_stats: List, totals: Dict, contributions: Dict) -> discord.Embed:
        """Create a detailed statistics embed for a specific type."""
        colors = {
            "commits": discord.Color.blue(),
            "pull-requests": discord.Color.orange(),
            "merges": discord.Color.green(),
            "repos": discord.Color.purple(),
            "contributions": discord.Color.gold(),
        }
        
        icons = {
            "commits": "📝",
            "pull-requests": "🔧",
            "merges": "🎉",
            "repos": "📚",
            "contributions": "⭐",
        }
        
        embed = discord.Embed(
            title=f"{icons.get(stat_type, '📊')} {stat_type.replace('-', ' ').title()} Statistics",
            color=colors.get(stat_type, discord.Color.blue()),
            timestamp=datetime.utcnow()
        )
        
        if stat_type == "repos":
            total_repos = len(repo_stats) if isinstance(repo_stats, list) else 0
            embed.add_field(name="Total Repositories", value=str(total_repos), inline=False)
            
            if repo_stats:
                # Show most active repositories
                sorted_repos = sorted(
                    repo_stats,
                    key=lambda x: x.get("commits", 0) + x.get("pull_requests", 0),
                    reverse=True
                )[:8]
                
                for repo in sorted_repos:
                    activity = repo.get("commits", 0) + repo.get("pull_requests", 0)
                    repo_name = repo["name"].split("/")[-1] if "/" in repo["name"] else repo["name"]
                    embed.add_field(
                        name=repo_name,
                        value=f"{activity} total",
                        inline=True
                    )
        
        elif stat_type == "contributions":
            total_contributions = contributions.get("total_contributions", 0)
            embed.add_field(name="Total Contributions", value=str(total_contributions), inline=False)
            embed.add_field(name="Commits", value=str(totals.get("commits", 0)), inline=True)
            embed.add_field(name="Pull Requests", value=str(totals.get("pull_requests", 0)), inline=True)
            embed.add_field(name="Public Repos", value=str(contributions.get("public_repos", 0)), inline=True)
            embed.add_field(name="Private Repos", value=str(contributions.get("private_repos", 0)), inline=True)
        
        else:
            # Show specific statistic breakdown
            total_count = totals.get(stat_type.replace("-", "_"), 0)
            if stat_type == "merges":
                total_count = totals.get("merged_pull_requests", 0)
            
            embed.add_field(name=f"Total {stat_type.replace('-', ' ').title()}", value=str(total_count), inline=False)
            
            if repo_stats:
                # Show top repositories for this statistic
                stat_key = stat_type.replace("-", "_")
                if stat_type == "merges":
                    stat_key = "merged_pull_requests"
                
                sorted_repos = sorted(
                    repo_stats,
                    key=lambda x: x.get(stat_key, 0),
                    reverse=True
                )[:8]
                
                for repo in sorted_repos:
                    count = repo.get(stat_key, 0)
                    if count > 0:
                        repo_name = repo["name"].split("/")[-1] if "/" in repo["name"] else repo["name"]
                        embed.add_field(
                            name=repo_name,
                            value=str(count),
                            inline=True
                        )
        
        embed.set_footer(text=f"Updated hourly • c1nderscript development statistics")
        return embed
    
    async def update_statistics_message(self, channel_id: int, embed: discord.Embed, stat_type: str):
        """Update or create statistics message in channel."""
        try:
            stats_map = load_stats_map()
            message_key = f"stats_{stat_type}"
            message_id = stats_map.get(message_key)
            
            channel = discord_bot_instance.bot.get_channel(channel_id)
            if message_id and channel:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=embed)
                    return
                except:
                    pass  # Message not found, create new one
            
            # Create new message
            message = await send_to_discord(channel_id, embed=embed)
            if message:
                stats_map[message_key] = message.id
                save_stats_map(stats_map)
                
        except Exception as e:
            logger.error(f"Failed to update statistics message for {stat_type}: {e}")
    
    async def update_dynamic_channel_names(self):
        """Update dynamic channel names based on current message counts."""
        try:
            for channel_id in settings.all_dynamic_channels:
                count = await self.get_channel_message_count(channel_id)
                channel_name = self.get_channel_name_from_id(channel_id)
                
                if channel_name:
                    await discord_bot_instance.update_channel_name(
                        channel_id, f"{count}-{channel_name}"
                    )
            
            logger.debug("Updated dynamic channel names")
            
        except Exception as e:
            logger.error(f"Failed to update dynamic channel names: {e}")
    
    async def get_channel_message_count(self, channel_id: int) -> int:
        """Get the number of non-pinned messages in a channel."""
        try:
            channel = discord_bot_instance.bot.get_channel(channel_id)
            if not channel:
                return 0
            
            count = 0
            async for message in channel.history(limit=None):
                if not message.pinned:
                    count += 1
            return count
        except:
            return 0
    
    def get_channel_name_from_id(self, channel_id: int) -> str:
        """Get the base channel name from channel ID."""
        channel_map = {
            settings.channel_commits: "commits",
            settings.channel_pull_requests: "pull-requests",
            settings.channel_code_merges: "merges",
            settings.channel_issues: "issues",
            settings.channel_releases: "releases",
            settings.channel_deployment_status: "deployments",
            settings.channel_ci_builds: "builds",
        }
        return channel_map.get(channel_id, "unknown")
    
    async def setup_commands_channel(self):
        """Set up the commands channel with current command list."""
        try:
            # Clear the channel
            await discord_bot_instance.purge_channel(settings.channel_bot_commands)
            
            # Create commands embed
            embed = discord.Embed(
                title="🤖 GitHub Development Bot Commands",
                description="Available commands for managing development workflows",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="!clear",
                value="Clear all content from all dynamic channels",
                inline=False
            )
            
            embed.add_field(
                name="!sync",
                value="Sync all channels: delete outdated messages, update numbers, refresh PRs",
                inline=False
            )
            
            embed.add_field(
                name="!update / !pr",
                value="Refresh all open pull requests in the pull requests channel",
                inline=False
            )
            
            embed.add_field(
                name="!setup",
                value="Create missing channels automatically for new servers",
                inline=False
            )
            
            embed.add_field(
                name="📊 Automated Features",
                value="• Hourly statistics updates\n• Dynamic message counting\n• Auto emoji reactions\n• Smart cleanup",
                inline=False
            )
            
            embed.set_footer(text="Commands and features updated hourly")
            
            # Send and pin the message
            message = await send_to_discord(settings.channel_bot_commands, embed=embed)
            if message:
                await message.pin()
            
            logger.info("Set up commands channel")
            
        except Exception as e:
            logger.error(f"Failed to setup commands channel: {e}")
    
    async def ensure_dynamic_channel_reactions(self):
        """Ensure all messages in dynamic channels have checkmark emojis."""
        try:
            for channel_id in settings.all_dynamic_channels:
                channel = discord_bot_instance.bot.get_channel(channel_id)
                if not channel:
                    continue
                
                # Check recent messages for missing reactions
                async for message in channel.history(limit=50):
                    if message.author.bot and not message.pinned:
                        # Check if message has checkmark
                        has_checkmark = any(str(reaction.emoji) == "✅" for reaction in message.reactions)
                        
                        if not has_checkmark:
                            try:
                                await message.add_reaction("✅")
                                logger.debug(f"Added missing checkmark to message {message.id}")
                            except Exception as e:
                                logger.error(f"Failed to add checkmark to message {message.id}: {e}")
        
        except Exception as e:
            logger.error(f"Error ensuring dynamic channel reactions: {e}")
    
    async def send_startup_notification(self):
        """Send startup notification to bot logs channel."""
        try:
            embed = discord.Embed(
                title="🚀 GitHub Development Bot Started",
                description="Development automation system is now active",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="🔄 Active Tasks",
                value="• Hourly statistics updates\n• Dynamic channel monitoring\n• Automated message management\n• Emoji reaction automation",
                inline=False
            )
            
            embed.add_field(
                name="📊 Channel Categories",
                value=f"• Statistics: {len(settings.all_stats_channels)} channels\n• Dynamic: {len(settings.all_dynamic_channels)} channels\n• Logging: 2 channels",
                inline=False
            )
            
            embed.set_footer(text="All automation features are now running")
            
            await send_to_discord(settings.channel_bot_logs, embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
    
    async def log_error(self, title: str, error_message: str):
        """Log an error to the bot logs channel."""
        try:
            embed = discord.Embed(
                title=f"❌ {title}",
                description=error_message[:2048],
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            
            await send_to_discord(settings.channel_bot_logs, embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to log error to Discord: {e}")
    
    async def get_status_report(self) -> dict:
        """Get current status of all bot automation features."""
        return {
            "last_stats_update": self.last_stats_update,
            "last_commands_update": self.last_commands_update,
            "bot_ready": discord_bot_instance.ready,
            "stats_channels": len(settings.all_stats_channels),
            "dynamic_channels": len(settings.all_dynamic_channels),
        }


# Global manager instance
dev_bot_manager = DevelopmentBotManager()
