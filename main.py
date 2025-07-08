"""Main server endpoint for receiving GitHub webhooks."""

import logging
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from config import settings
from discord_bot import send_to_discord, discord_bot_instance
from github_utils import verify_github_signature, is_github_event_relevant
from formatters import (
    format_push_event,
    format_pull_request_event,
    format_merge_event,
    format_issue_event,
    format_release_event,
    format_deployment_event,
    format_gollum_event,
    format_generic_event
)


# Initialize FastAPI app
app = FastAPI()


# Logger
logger = logging.getLogger("uvicorn")


@app.on_event("startup")
async def startup_event():
    """Startup event to initialize Discord bot."""
    logger.info("Starting up Discord bot...")
    asyncio.create_task(discord_bot_instance.start())


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
        
        if action == "closed" and is_merged:
            embed = format_merge_event(payload)
            await send_to_discord(settings.channel_code_merges, embed=embed)
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
    elif event_type == "gollum":
        embed = format_gollum_event(payload)
        await send_to_discord(settings.channel_gollum, embed=embed)
    else:
        embed = format_generic_event(event_type, payload)
        await send_to_discord(settings.channel_bot_logs, embed=embed)
    
    logger.info(f"Event {event_type} routed successfully.")
