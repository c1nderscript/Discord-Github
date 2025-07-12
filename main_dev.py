"""Main server endpoint for receiving GitHub webhooks with complete development bot automation."""

import logging
import asyncio
import discord
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from logging_config import setup_logging
from config import settings
from discord_bot import send_to_discord, discord_bot_instance
from pull_request_handler import handle_pull_request_event_with_retry
from cleanup import periodic_pr_cleanup
from dev_bot_manager import dev_bot_manager

from github_utils import (
    verify_github_signature,
    is_github_event_relevant,
)
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
    logger.info("Starting GitHub Development Bot...")
    
    # Start Discord bot
    asyncio.create_task(discord_bot_instance.start())
    
    # Start legacy cleanup task
    asyncio.create_task(periodic_pr_cleanup(settings.pr_cleanup_interval_minutes))
    
    # Start development bot automation
    asyncio.create_task(dev_bot_manager.start_automation_tasks())
    
    # Send startup log
    await log_bot_startup()

    yield

# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

# Logger
logger = logging.getLogger("uvicorn")


@app.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint with development bot status."""
    status = await dev_bot_manager.get_status_report()
    return JSONResponse(content={
        "status": "ok",
        "bot_ready": status["bot_ready"],
        "automation_active": True,
        "features": {
            "statistics_channels": status["stats_channels"],
            "dynamic_channels": status["dynamic_channels"],
            "last_stats_update": status["last_stats_update"].isoformat() if status["last_stats_update"] else None,
        }
    })


async def log_bot_startup():
    """Log bot startup to the logging channel."""
    # Wait for Discord bot to be ready
    while not discord_bot_instance.ready:
        await asyncio.sleep(1)
    
    try:
        embed = discord.Embed(
            title="🤖 GitHub Development Bot Started",
            description="Advanced development workflow automation is now active",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="🔄 Automation Features",
            value="• Hourly GitHub statistics updates\n• Dynamic channel message management\n• Auto emoji reactions\n• Smart PR cleanup\n• Commands maintenance",
            inline=False
        )
        
        embed.add_field(
            name="📊 Channel Management", 
            value=f"• {len(settings.all_stats_channels)} statistics channels\n• {len(settings.all_dynamic_channels)} dynamic channels\n• 2 logging channels",
            inline=False
        )
        
        await send_to_discord(settings.channel_bot_logs, embed=embed)
        logger.info("GitHub Development Bot startup complete")
        
    except Exception as e:
        logger.error(f"Failed to log startup: {e}")


@app.post("/github")
async def github_webhook(request: Request):
    """GitHub webhook endpoint with enhanced development bot integration."""
    # Get the raw body for signature verification
    body = await request.body()

    # Verify signature
    await verify_github_signature(request, body)

    # Parse event type and payload
    event_type = request.headers.get("X-GitHub-Event")
    if not event_type:
        raise HTTPException(status_code=400, detail="Missing X-GitHub-Event header")

    payload = await request.json()
    logger.info(f"Received GitHub event: {event_type}")

    # Check if the event is relevant
    if not is_github_event_relevant(event_type, payload):
        logger.info(f"Skipping irrelevant event: {event_type}")
        return JSONResponse(content={"status": "skipped"})

    # Route event to the appropriate handler
    await route_github_event(event_type, payload)

    return JSONResponse(content={"status": "success"})


async def route_github_event(event_type: str, payload: dict):
    """Route GitHub event to appropriate Discord channel with development bot features."""
    
    message = None
    
    try:
        if event_type == "push":
            embed = format_push_event(payload)
            message = await send_to_discord(settings.channel_commits, embed=embed)
            
        elif event_type == "pull_request":
            # Use enhanced PR handler with retry logic
            success = await handle_pull_request_event_with_retry(payload)
            if success:
                logger.info("Successfully processed pull_request event")
            else:
                logger.error("Failed to process pull_request event")
                await log_processing_error("pull_request", payload, "PR handler failed")
            return  # PR handler manages its own messages and reactions
            
        elif event_type == "issues":
            embed = format_issue_event(payload)
            message = await send_to_discord(settings.channel_issues, embed=embed)
            
        elif event_type == "release":
            embed = format_release_event(payload)
            message = await send_to_discord(settings.channel_releases, embed=embed)
            
        elif event_type == "deployment_status":
            embed = format_deployment_event(payload)
            message = await send_to_discord(settings.channel_deployment_status, embed=embed)
            
        elif event_type == "workflow_run":
            embed = format_workflow_run(payload)
            message = await send_to_discord(settings.channel_ci_builds, embed=embed)
            
        elif event_type == "workflow_job":
            embed = format_workflow_job(payload)
            message = await send_to_discord(settings.channel_ci_builds, embed=embed)
            
        elif event_type == "check_run":
            embed = format_check_run(payload)
            message = await send_to_discord(settings.channel_ci_builds, embed=embed)
            
        elif event_type == "check_suite":
            embed = format_check_suite(payload)
            message = await send_to_discord(settings.channel_ci_builds, embed=embed)
            
        elif event_type == "gollum":
            embed = format_gollum_event(payload)
            message = await send_to_discord(settings.channel_gollum, embed=embed)
            
        else:
            embed = format_generic_event(event_type, payload)
            await send_to_discord(settings.channel_bot_logs, embed=embed)
            logger.info(f"Handled unknown event type: {event_type}")
            return

        # Add checkmark emoji to dynamic channel messages
        if message and should_add_checkmark(event_type):
            await add_checkmark_emoji(message)
        
        # Trigger dynamic channel name update
        asyncio.create_task(dev_bot_manager.update_dynamic_channel_names())
        
        logger.info(f"Successfully routed {event_type} event")
        
    except Exception as e:
        logger.error(f"Error routing {event_type} event: {e}")
        await log_processing_error(event_type, payload, str(e))


def should_add_checkmark(event_type: str) -> bool:
    """Determine if an event type should get a checkmark emoji."""
    # Add checkmarks to all dynamic channel events
    checkmark_events = {
        "push", "issues", "release", "deployment_status", 
        "workflow_run", "workflow_job", "check_run", "check_suite"
    }
    return event_type in checkmark_events


async def add_checkmark_emoji(message):
    """Add checkmark emoji to a message."""
    try:
        if message:
            await message.add_reaction("✅")
            logger.debug(f"Added checkmark emoji to message {message.id}")
    except Exception as e:
        logger.error(f"Failed to add checkmark emoji: {e}")


async def log_processing_error(event_type: str, payload: dict, error_message: str):
    """Log event processing errors to the bot logs channel."""
    try:
        embed = discord.Embed(
            title="❌ Event Processing Error",
            description=f"Failed to process {event_type} event",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="Event Type",
            value=event_type,
            inline=True
        )
        
        embed.add_field(
            name="Repository",
            value=payload.get("repository", {}).get("full_name", "Unknown"),
            inline=True
        )
        
        embed.add_field(
            name="Error",
            value=error_message[:1024],
            inline=False
        )
        
        if "action" in payload:
            embed.add_field(
                name="Action",
                value=payload["action"],
                inline=True
            )
        
        await send_to_discord(settings.channel_bot_logs, embed=embed)
        
    except Exception as e:
        logger.error(f"Failed to log processing error: {e}")


# Export functions for use by other modules
async def update_dynamic_channel_names():
    """Wrapper function for updating dynamic channel names."""
    await dev_bot_manager.update_dynamic_channel_names()


async def update_all_statistics():
    """Wrapper function for updating all statistics."""
    await dev_bot_manager.update_all_statistics()


async def get_channel_message_count(channel_id: int) -> int:
    """Wrapper function for getting channel message count."""
    return await dev_bot_manager.get_channel_message_count(channel_id)


def get_channel_name_from_id(channel_id: int) -> str:
    """Wrapper function for getting channel name from ID."""
    return dev_bot_manager.get_channel_name_from_id(channel_id)


async def setup_commands_channel():
    """Wrapper function for setting up commands channel."""
    await dev_bot_manager.setup_commands_channel()
