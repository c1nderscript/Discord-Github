"""Main server endpoint for receiving GitHub webhooks with enhanced development bot features."""

import logging
import asyncio
import discord
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from logging_config import setup_logging
from config import settings
from discord_bot import send_to_discord, discord_bot_instance
from pull_request_handler import handle_pull_request_event_with_retry
from cleanup import periodic_pr_cleanup

from github_utils import (
    verify_github_signature,
    is_github_event_relevant,
    gather_repo_stats,
    fetch_repo_stats,
)
from github_stats import fetch_repo_stats as fetch_github_stats
from stats_map import load_stats_map, save_stats_map
from utils.embed_utils import split_embed_fields

from formatters import (
    format_push_event,
    format_issue_event,
    format_release_event,
    format_deployment_event,
    format_gollum_event,
    format_workflow_run,
    format_workflow_job,
    format_check_run,
    format_check_suite,
    format_generic_event,
)

# Setup logging
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan for startup tasks."""
    logger.info("Starting up Discord development bot...")
    
    # Start Discord bot
    asyncio.create_task(discord_bot_instance.start())
    
    # Start periodic tasks
    asyncio.create_task(periodic_pr_cleanup(settings.pr_cleanup_interval_minutes))
    asyncio.create_task(periodic_stats_update())
    asyncio.create_task(periodic_commands_cleanup())
    
    # Initial cleanup and setup
    purge_channels = [
        settings.channel_commits,
        settings.channel_pull_requests,
        settings.channel_releases,
    ]
    for channel_id in purge_channels:
        asyncio.create_task(
            discord_bot_instance.purge_old_messages(
                channel_id, settings.message_retention_days
            )
        )

    # Initial statistics update
    asyncio.create_task(update_all_statistics())
    
    # Initial commands channel setup
    asyncio.create_task(setup_commands_channel())

    yield

# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

# Logger
logger = logging.getLogger("uvicorn")


@app.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok"})


async def periodic_stats_update():
    """Run statistics updates every hour."""
    while True:
        try:
            await update_all_statistics()
            logger.info("Completed hourly statistics update")
        except Exception as exc:
            logger.error(f"Statistics update failed: {exc}")
        await asyncio.sleep(settings.stats_update_interval_minutes * 60)


async def periodic_commands_cleanup():
    """Clean up commands channel every hour."""
    while True:
        try:
            await setup_commands_channel()
            logger.info("Completed hourly commands channel cleanup")
        except Exception as exc:
            logger.error(f"Commands cleanup failed: {exc}")
        await asyncio.sleep(60 * 60)  # Every hour


async def update_all_statistics():
    """Update both API-based statistics channels and dynamic channel names."""
    # Wait for bot to be ready
    while not discord_bot_instance.ready:
        await asyncio.sleep(1)
    
    # Update API-based statistics channels
    await update_github_statistics()
    
    # Update dynamic channel names based on message counts
    await update_dynamic_channel_names()


async def update_github_statistics():
    """Update GitHub statistics channels with API data."""
    try:
        # Fetch statistics from GitHub API
        repo_stats, totals = await fetch_repo_stats()
        
        # Calculate additional statistics
        total_repos = len(repo_stats) if isinstance(repo_stats, list) else len(repo_stats)
        total_contributions = totals.get("commits", 0) + totals.get("pull_requests", 0)
        
        # Statistics data mapping
        stats_data = {
            "commits": totals.get("commits", 0),
            "pull_requests": totals.get("pull_requests", 0), 
            "merges": totals.get("merged_pull_requests", 0),
            "repos": total_repos,
            "contributions": total_contributions,
        }
        
        # Channel mapping for statistics
        stats_channels = {
            "commits": settings.channel_stats_commits,
            "pull_requests": settings.channel_stats_pull_requests,
            "merges": settings.channel_stats_merges,
            "repos": settings.channel_stats_repos,
            "contributions": settings.channel_stats_contributions,
        }
        
        # Update each statistics channel
        for stat_type, channel_id in stats_channels.items():
            count = stats_data[stat_type]
            
            # Update channel name
            await discord_bot_instance.update_channel_name(
                channel_id, f"{count}-{stat_type.replace('_', '-')}"
            )
            
            # Create statistics embed
            embed = await create_statistics_embed(stat_type, repo_stats, totals)
            
            # Update or send new embed
            await update_statistics_embed(channel_id, embed, stat_type)
            
        logger.info(f"Updated GitHub statistics: {stats_data}")
        
    except Exception as exc:
        logger.error(f"Failed to update GitHub statistics: {exc}")
        await send_to_discord(
            settings.channel_bot_logs,
            embed=discord.Embed(
                title="❌ Statistics Update Failed",
                description=f"Error updating GitHub statistics: {exc}",
                color=discord.Color.red()
            )
        )


async def create_statistics_embed(stat_type: str, repo_stats, totals: dict) -> discord.Embed:
    """Create a statistics embed for a specific statistic type."""
    colors = {
        "commits": discord.Color.blue(),
        "pull_requests": discord.Color.orange(),
        "merges": discord.Color.green(),
        "repos": discord.Color.purple(),
        "contributions": discord.Color.gold(),
    }
    
    icons = {
        "commits": "📝",
        "pull_requests": "🔧", 
        "merges": "🎉",
        "repos": "📚",
        "contributions": "⭐",
    }
    
    embed = discord.Embed(
        title=f"{icons.get(stat_type, '📊')} {stat_type.replace('_', ' ').title()} Statistics",
        color=colors.get(stat_type, discord.Color.blue()),
        timestamp=datetime.utcnow()
    )
    
    if stat_type == "repos":
        # Show repository count
        total_repos = len(repo_stats) if isinstance(repo_stats, list) else len(repo_stats)
        embed.add_field(name="Total Repositories", value=str(total_repos), inline=False)
        
        if isinstance(repo_stats, list):
            # Show top repositories by activity
            sorted_repos = sorted(
                repo_stats, 
                key=lambda x: x.get("commits", 0) + x.get("pull_requests", 0), 
                reverse=True
            )[:10]
            
            for repo in sorted_repos:
                activity = repo.get("commits", 0) + repo.get("pull_requests", 0)
                embed.add_field(
                    name=repo["name"].split("/")[-1],
                    value=f"{activity} total activity",
                    inline=True
                )
    
    elif stat_type == "contributions":
        # Show contribution breakdown
        total_contribs = totals.get("commits", 0) + totals.get("pull_requests", 0)
        embed.add_field(name="Total Contributions", value=str(total_contribs), inline=False)
        embed.add_field(name="Commits", value=str(totals.get("commits", 0)), inline=True)
        embed.add_field(name="Pull Requests", value=str(totals.get("pull_requests", 0)), inline=True)
        
    else:
        # Show specific statistic breakdown
        total_count = totals.get(stat_type, 0)
        if stat_type == "merges":
            total_count = totals.get("merged_pull_requests", 0)
            
        embed.add_field(name=f"Total {stat_type.title()}", value=str(total_count), inline=False)
        
        if isinstance(repo_stats, list):
            # Show top repositories for this statistic
            sorted_repos = sorted(
                repo_stats,
                key=lambda x: x.get(stat_type, 0) if stat_type != "merges" else x.get("merged_pull_requests", 0),
                reverse=True
            )[:10]
            
            for repo in sorted_repos:
                if stat_type == "merges":
                    count = repo.get("merged_pull_requests", 0)
                else:
                    count = repo.get(stat_type, 0)
                
                if count > 0:
                    embed.add_field(
                        name=repo["name"].split("/")[-1],
                        value=str(count),
                        inline=True
                    )
    
    embed.set_footer(text=f"Updated every hour • c1nderscript account statistics")
    return embed


async def update_statistics_embed(channel_id: int, embed: discord.Embed, stat_type: str):
    """Update or create statistics embed in channel."""
    try:
        stats_map = load_stats_map()
        message_id = stats_map.get(f"stats_{stat_type}")
        
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
            stats_map[f"stats_{stat_type}"] = message.id
            save_stats_map(stats_map)
            
    except Exception as exc:
        logger.error(f"Failed to update statistics embed for {stat_type}: {exc}")


async def update_dynamic_channel_names():
    """Update dynamic channel names based on message counts."""
    try:
        for channel_id in settings.all_dynamic_channels:
            count = await get_channel_message_count(channel_id)
            channel_name = get_channel_name_from_id(channel_id)
            
            if channel_name:
                await discord_bot_instance.update_channel_name(
                    channel_id, f"{count}-{channel_name}"
                )
                
        logger.info("Updated dynamic channel names")
        
    except Exception as exc:
        logger.error(f"Failed to update dynamic channel names: {exc}")


def get_channel_name_from_id(channel_id: int) -> str:
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


async def get_channel_message_count(channel_id: int) -> int:
    """Get the number of messages in a channel."""
    try:
        channel = discord_bot_instance.bot.get_channel(channel_id)
        if not channel:
            return 0
            
        # Count messages (excluding pinned)
        count = 0
        async for message in channel.history(limit=None):
            if not message.pinned:
                count += 1
        return count
    except:
        return 0


async def setup_commands_channel():
    """Set up the commands channel with pinned command list."""
    try:
        # Clear the channel
        await discord_bot_instance.purge_channel(settings.channel_bot_commands)
        
        # Create commands embed
        embed = discord.Embed(
            title="🤖 Bot Commands",
            description="Available commands for the GitHub Development Bot",
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
            value="Delete outdated messages, update channel numbers, and ensure only outstanding pull requests are in channels",
            inline=False
        )
        
        embed.add_field(
            name="!update",
            value="Refresh all open pull requests in the pull requests channel",
            inline=False
        )
        
        embed.add_field(
            name="!setup",
            value="Create missing channels automatically",
            inline=False
        )
        
        embed.set_footer(text="Commands updated hourly")
        
        # Send and pin the message
        message = await send_to_discord(settings.channel_bot_commands, embed=embed)
        if message:
            await message.pin()
            
        logger.info("Set up commands channel")
        
    except Exception as exc:
        logger.error(f"Failed to setup commands channel: {exc}")


@app.post("/github")
async def github_webhook(request: Request):
    """GitHub webhook endpoint."""
    # Get the raw body for signature verification
    body = await request.body()

    # Verify signature
    await verify_github_signature(request, body)

    # Parse event type and payload
    event_type = request.headers.get("X-GitHub-Event")
    if not event_type:
        raise HTTPException(status_code=400, detail="Missing X-GitHub-Event header")

    payload = await request.json()
    logger.info(f"Received event: {event_type}")

    # Check if the event is relevant
    if not is_github_event_relevant(event_type, payload):
        logger.info(f"Skipping irrelevant event: {event_type}")
        return JSONResponse(content={"status": "skipped"})

    # Route event to the appropriate handler
    await route_github_event(event_type, payload)

    return JSONResponse(content={"status": "success"})


async def route_github_event(event_type: str, payload: dict):
    """Route GitHub event to appropriate Discord channel."""
    if event_type == "push":
        embed = format_push_event(payload)
        message = await send_to_discord(settings.channel_commits, embed=embed)
        if message:
            await add_checkmark_emoji(message)
        asyncio.create_task(update_dynamic_channel_names())
        
    elif event_type == "pull_request":
        # Use enhanced PR handler with retry logic
        success = await handle_pull_request_event_with_retry(payload)
        if success:
            logger.info("Successfully processed pull_request event")
            if payload.get("action") in {"opened", "closed", "reopened"}:
                asyncio.create_task(update_dynamic_channel_names())
        else:
            logger.error("Failed to process pull_request event")
            
    elif event_type == "issues":
        embed = format_issue_event(payload)
        message = await send_to_discord(settings.channel_issues, embed=embed)
        if message:
            await add_checkmark_emoji(message)
        asyncio.create_task(update_dynamic_channel_names())
        
    elif event_type == "release":
        embed = format_release_event(payload)
        message = await send_to_discord(settings.channel_releases, embed=embed)
        if message:
            await add_checkmark_emoji(message)
        asyncio.create_task(update_dynamic_channel_names())
        
    elif event_type == "deployment_status":
        embed = format_deployment_event(payload)
        message = await send_to_discord(settings.channel_deployment_status, embed=embed)
        if message:
            await add_checkmark_emoji(message)
        asyncio.create_task(update_dynamic_channel_names())
        
    elif event_type == "workflow_run":
        embed = format_workflow_run(payload)
        message = await send_to_discord(settings.channel_ci_builds, embed=embed)
        if message:
            await add_checkmark_emoji(message)
        asyncio.create_task(update_dynamic_channel_names())
        
    elif event_type == "workflow_job":
        embed = format_workflow_job(payload)
        message = await send_to_discord(settings.channel_ci_builds, embed=embed)
        if message:
            await add_checkmark_emoji(message)
        asyncio.create_task(update_dynamic_channel_names())
        
    elif event_type == "check_run":
        embed = format_check_run(payload)
        message = await send_to_discord(settings.channel_ci_builds, embed=embed)
        if message:
            await add_checkmark_emoji(message)
        asyncio.create_task(update_dynamic_channel_names())
        
    elif event_type == "check_suite":
        embed = format_check_suite(payload)
        message = await send_to_discord(settings.channel_ci_builds, embed=embed)
        if message:
            await add_checkmark_emoji(message)
        asyncio.create_task(update_dynamic_channel_names())
        
    elif event_type == "gollum":
        embed = format_gollum_event(payload)
        message = await send_to_discord(settings.channel_gollum, embed=embed)
        if message:
            await add_checkmark_emoji(message)
            
    else:
        embed = format_generic_event(event_type, payload)
        await send_to_discord(settings.channel_bot_logs, embed=embed)

    logger.info(f"Event {event_type} routed successfully.")


async def add_checkmark_emoji(message):
    """Add checkmark emoji to message."""
    try:
        await message.add_reaction("✅")
    except Exception as exc:
        logger.error(f"Failed to add checkmark emoji: {exc}")
