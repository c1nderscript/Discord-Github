"""Main server endpoint for receiving GitHub webhooks."""

import logging
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from logging_config import setup_logging
from config import settings
from discord_bot import send_to_discord, discord_bot_instance

from cleanup import cleanup_pr_messages

from pr_map import load_pr_map, save_pr_map
from github_utils import verify_github_signature, is_github_event_relevant
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

async def health_check() -> JSONResponse:
    """Return service health status."""
    if discord_bot_instance.ready:
        return JSONResponse(content={"status": "ok"})
    return JSONResponse(status_code=503, content={"status": "starting"})

async def health() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok"})


# Logger
logger = logging.getLogger("uvicorn")


@app.on_event("startup")
async def startup_event():
    """Startup event to initialize Discord bot."""
    logger.info("Starting up Discord bot...")
    asyncio.create_task(discord_bot_instance.start())
    asyncio.create_task(cleanup_pr_messages())

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
        action = payload.get("action")
        pr = payload.get("pull_request", {})
        is_merged = pr.get("merged", False)
        repo = payload.get("repository", {})
        repo_name = repo.get("full_name", "")
        number = pr.get("number")
        pr_key = f"{repo_name}#{number}"

        if action in ("opened", "ready_for_review"):
            embed = format_pull_request_event(payload)
            message = await send_to_discord(settings.channel_pull_requests, embed=embed)
            if message:
                pr_map = load_pr_map()
                pr_map[pr_key] = message.id
                save_pr_map(pr_map)
        elif action == "closed":
            if is_merged:
                embed = format_merge_event(payload)
                await send_to_discord(settings.channel_code_merges, embed=embed)
            else:
                embed = format_pull_request_event(payload)
                await send_to_discord(settings.channel_pull_requests, embed=embed)

            pr_map = load_pr_map()
            message_id = pr_map.pop(pr_key, None)
            if message_id:
                await discord_bot_instance.delete_message_from_channel(
                    settings.channel_pull_requests, message_id
                )
                save_pr_map(pr_map)
        else:
            embed = format_pull_request_event(payload)
            await send_to_discord(settings.channel_pull_requests, embed=embed)
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
