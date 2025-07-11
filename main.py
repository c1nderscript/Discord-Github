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

from cleanup import cleanup_pr_messages, periodic_pr_cleanup


from pr_map import load_pr_map, save_pr_map
from github_utils import (
    verify_github_signature,
    is_github_event_relevant,
    gather_repo_stats,
    RepoStats,
)
from github_stats import fetch_repo_stats
from stats_map import load_stats_map, save_stats_map
from github_prs import fetch_open_pull_requests

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

# Initialize FastAPI app
app = FastAPI()


# Logger
logger = logging.getLogger("uvicorn")


@app.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok"})


async def update_github_stats() -> None:
    """Update Discord overview channels with GitHub statistics."""
    stats: dict[str, dict[str, int]] = {}
    try:
        stats = await fetch_repo_stats()
    except Exception as exc:
        logger.error(f"Failed to fetch repo stats: {exc}")

    if not stats or all(
        sum(repo.get(key, 0) for repo in stats.values()) == 0
        for key in ("pull_requests", "merges")
    ):
        try:
            repo_stats = await gather_repo_stats()
            stats = {
                r.name: {
                    "commits": r.commit_count,
                    "pull_requests": r.pr_count,
                    "merges": r.merge_count,
                }
                for r in repo_stats
            }
        except Exception as exc:  # pragma: no cover - network failure
            logger.error(f"Failed to gather repo stats: {exc}")
            return

    totals = {"commits": 0, "pull_requests": 0, "merges": 0}
    for counts in stats.values():
        for key in totals:
            totals[key] += counts.get(key, 0)

    embeds = {}
    for key, title in [
        ("commits", "Commit Counts"),
        ("pull_requests", "Pull Request Counts"),
        ("merges", "Merge Counts"),
    ]:
        embed = discord.Embed(title=title, color=discord.Color.blue())
        for repo, counts in stats.items():
            embed.add_field(name=repo, value=str(counts.get(key, 0)), inline=False)
        embeds[key] = embed

    channel_map = {
        "commits": settings.channel_commits_overview,
        "pull_requests": settings.channel_pull_requests_overview,
        "merges": settings.channel_merges_overview,
    }

    message_map = load_stats_map()
    for key, channel_id in channel_map.items():
        await discord_bot_instance.update_channel_name(
            channel_id, f"{totals[key]}-{key.replace('_', '-')}"
        )

        embed = embeds[key]
        message_id = message_map.get(key)
        channel = discord_bot_instance.bot.get_channel(channel_id)
        if message_id and channel:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embed)
                continue
            except Exception as exc:
                logger.warning(
                    f"Failed to edit stats message in {channel_id}: {exc}"
                )

        msg = await send_to_discord(channel_id, embed=embed)
        if msg:
            message_map[key] = msg.id

    save_stats_map(message_map)


async def update_pull_request_count() -> None:
    """Update the pull-requests channel with the number of open PRs."""
    try:
        pr_map = await fetch_open_pull_requests()
        count = sum(len(prs) for prs in pr_map.values())
    except Exception as exc:  # pragma: no cover - network failure
        logger.error(f"Failed to fetch pull request count: {exc}")
        return

    while not discord_bot_instance.ready:
        await asyncio.sleep(1)

    await discord_bot_instance.update_channel_name(
        settings.channel_pull_requests, f"{count}-pull-requests"
    )


async def periodic_stats_update(interval_minutes: int) -> None:
    """Periodically update overview statistics."""
    while True:
        try:
            await update_github_stats()
        except Exception as exc:  # pragma: no cover - unexpected runtime failure
            logger.error("Stats update failed: %s", exc)
        await asyncio.sleep(interval_minutes * 60)


async def periodic_pr_count_update(interval_minutes: int) -> None:
    """Periodically update pull request count."""
    while True:
        try:
            await update_pull_request_count()
        except Exception as exc:  # pragma: no cover - unexpected runtime failure
            logger.error("PR count update failed: %s", exc)
        await asyncio.sleep(interval_minutes * 60)


@app.on_event("startup")
async def startup_event():
    """Startup event to initialize Discord bot."""
    logger.info("Starting up Discord bot...")
    asyncio.create_task(discord_bot_instance.start())
    asyncio.create_task(
        periodic_pr_cleanup(settings.pr_cleanup_interval_minutes)
    )
    asyncio.create_task(periodic_stats_update(settings.stats_update_interval_minutes))
    asyncio.create_task(periodic_pr_count_update(settings.pr_count_update_interval_minutes))
    asyncio.create_task(update_github_stats())
    asyncio.create_task(update_pull_request_count())

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
        asyncio.create_task(update_github_stats())
    elif event_type == "pull_request":
        # Use enhanced PR handler with retry logic
        success = await handle_pull_request_event_with_retry(payload)
        if success:

            logger.info(f"Successfully processed pull_request event")

            if payload.get("action") in {"opened", "closed", "reopened"}:
                asyncio.create_task(update_github_stats())
                asyncio.create_task(update_pull_request_count())
        else:
            logger.error("Failed to process pull_request event")
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


async def update_statistics() -> None:

    """Update channel names with repo statistics and post summary embeds."""
    if not settings.github_token:
        logger.warning("No GITHUB_TOKEN configured; skipping statistics update")
        return

    try:
        stats = await gather_repo_stats()
    except Exception as exc:
        logger.error(f"Failed to gather repo stats: {exc}")
        return

    total_commits = sum(r.commit_count for r in stats)
    total_prs = sum(r.pr_count for r in stats)
    total_merges = sum(r.merge_count for r in stats)

    while not discord_bot_instance.ready:
        await asyncio.sleep(1)


    await discord_bot_instance.update_channel_name(
        settings.channel_commits_overview, f"{total_commits}-commits"
    )
    await discord_bot_instance.update_channel_name(
        settings.channel_pull_requests_overview, f"{total_prs}-pull-requests"
    )
    await discord_bot_instance.update_channel_name(
        settings.channel_merges_overview, f"{total_merges}-merges"
    )

    for repo in stats:
        embed = discord.Embed(
            title=f"📊 Statistics for {repo.name}",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Commits", value=str(repo.commit_count), inline=True)
        embed.add_field(name="Pull Requests", value=str(repo.pr_count), inline=True)
        embed.add_field(name="Merges", value=str(repo.merge_count), inline=True)

        await send_to_discord(settings.channel_commits_overview, embed=embed)
        await send_to_discord(settings.channel_pull_requests_overview, embed=embed)
        await send_to_discord(settings.channel_merges_overview, embed=embed)
