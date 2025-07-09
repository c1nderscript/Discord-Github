"""Main server endpoint for receiving GitHub webhooks with enhanced PR handling."""

import logging
import asyncio

import discord
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from logging_config import setup_logging
from config import settings
from discord_bot import send_to_discord, discord_bot_instance
from pull_request_handler import handle_pull_request_event_with_retry

from cleanup import cleanup_pr_messages

from pr_map import load_pr_map, save_pr_map
from github_utils import (
    verify_github_signature,
    is_github_event_relevant,
    fetch_repo_stats,
)
from formatters import (
    format_push_event,
    format_pull_request_event,
    format_merge_event,
    format_issue_event,
    format_release_event,
    format_deployment_event,
    format_gollum_event,
    format_workflow_run,
    format_workflow_job,
    format_check_run,
    format_check_suite,
    format_generic_event
)

# Setup logging
setup_logging()

# Initialize FastAPI app
app = FastAPI()


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}

# Logger
logger = logging.getLogger("uvicorn")


@app.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok"})


@app.on_event("startup")
async def startup_event():
    """Startup event to initialize Discord bot."""
    logger.info("Starting up Discord bot...")
    asyncio.create_task(discord_bot_instance.start())
    asyncio.create_task(cleanup_pr_messages())
    asyncio.create_task(update_github_stats())

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
        await send_to_discord(settings.channel_commits, embed=embed)
    elif event_type == "pull_request":
        # Use enhanced PR handler with retry logic
        success = await handle_pull_request_event_with_retry(payload)
        if success:
            logger.info(f"Successfully processed pull_request event")
        else:
            logger.error(f"Failed to process pull_request event")
    elif event_type == "issues":
        embed = format_issue_event(payload)
        await send_to_discord(settings.channel_issues, embed=embed)
    elif event_type == "release":
        embed = format_release_event(payload)
        await send_to_discord(settings.channel_releases, embed=embed)
    elif event_type == "deployment_status":
        embed = format_deployment_event(payload)
        await send_to_discord(settings.channel_deployment_status, embed=embed)
    elif event_type == "workflow_run":
        embed = format_workflow_run(payload)
        await send_to_discord(settings.channel_ci_builds, embed=embed)
    elif event_type == "workflow_job":
        embed = format_workflow_job(payload)
        await send_to_discord(settings.channel_ci_builds, embed=embed)
    elif event_type == "check_run":
        embed = format_check_run(payload)
        await send_to_discord(settings.channel_ci_builds, embed=embed)
    elif event_type == "check_suite":
        embed = format_check_suite(payload)
        await send_to_discord(settings.channel_ci_builds, embed=embed)
    elif event_type == "gollum":
        embed = format_gollum_event(payload)
        await send_to_discord(settings.channel_gollum, embed=embed)
    else:
        embed = format_generic_event(event_type, payload)
        await send_to_discord(settings.channel_bot_logs, embed=embed)
    
    logger.info(f"Event {event_type} routed successfully.")
    await update_github_stats()


stats_messages: dict[int, int] = {}


async def update_github_stats() -> None:
    """Update Discord overview channels with GitHub statistics."""
    try:
        repo_stats = await fetch_repo_stats()
    except Exception as exc:  # pragma: no cover - unexpected errors
        logger.error("Failed to fetch repo stats: %s", exc)
        return

    total_commits = sum(s.get("commits", 0) for s in repo_stats.values())
    total_prs = sum(s.get("pull_requests", 0) for s in repo_stats.values())
    total_merges = sum(s.get("merges", 0) for s in repo_stats.values())

    await discord_bot_instance.update_channel_name(
        settings.channel_commits, f"{total_commits}-commits"
    )
    await discord_bot_instance.update_channel_name(
        settings.channel_pull_requests, f"{total_prs}-pull-requests"
    )
    await discord_bot_instance.update_channel_name(
        settings.channel_code_merges, f"{total_merges}-merges"
    )

    commits_embed = discord.Embed(title="Commit Counts", color=discord.Color.blue())
    prs_embed = discord.Embed(title="Pull Request Counts", color=discord.Color.blurple())
    merges_embed = discord.Embed(title="Merge Counts", color=discord.Color.green())

    for repo, counts in repo_stats.items():
        commits_embed.add_field(name=repo, value=str(counts.get("commits", 0)), inline=False)
        prs_embed.add_field(name=repo, value=str(counts.get("pull_requests", 0)), inline=False)
        merges_embed.add_field(name=repo, value=str(counts.get("merges", 0)), inline=False)

    async def _send_or_edit(channel_id: int, embed: discord.Embed) -> None:
        message_id = stats_messages.get(channel_id)
        channel = discord_bot_instance.bot.get_channel(channel_id)
        if message_id and channel:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embed)
                return
            except Exception as exc:  # pragma: no cover - fetch failures
                logger.error("Failed to edit stats message in %s: %s", channel_id, exc)

        message = await send_to_discord(channel_id, embed=embed)
        if message:
            stats_messages[channel_id] = message.id

    await _send_or_edit(settings.channel_commits, commits_embed)
    await _send_or_edit(settings.channel_pull_requests, prs_embed)
    await _send_or_edit(settings.channel_code_merges, merges_embed)

    logger.info("GitHub statistics updated")
