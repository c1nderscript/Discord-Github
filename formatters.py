"""Formatters for GitHub webhook events to Discord messages."""

import discord
from typing import Dict, Any, Optional
from datetime import datetime


def format_commit_message(commit: Dict[str, Any]) -> str:
    """Format a single commit for display."""
    author = commit.get("author", {}).get("name", "Unknown")
    message = commit.get("message", "No message")
    url = commit.get("url", "")
    commit_id = commit.get("id", "")[:7]  # Short commit hash

    return f"[`{commit_id}`]({url}) {message} - {author}"


def format_push_event(payload: Dict[str, Any]) -> discord.Embed:
    """Format a push event for Discord."""
    repo = payload.get("repository", {})
    repo_name = repo.get("full_name", "Unknown repo")
    repo_url = repo.get("html_url", "")

    pusher = payload.get("pusher", {}).get("name", "Unknown")
    ref = payload.get("ref", "").replace("refs/heads/", "")

    commits = payload.get("commits", [])
    commit_count = len(commits)

    embed = discord.Embed(
        title=f"📝 {commit_count} commit{'s' if commit_count != 1 else ''} pushed to {ref}",
        url=f"{repo_url}/commits/{ref}",
        color=discord.Color.blue(),
    )

    embed.add_field(name="Repository", value=f"[{repo_name}]({repo_url})", inline=True)

    embed.add_field(name="Pusher", value=pusher, inline=True)

    embed.add_field(name="Branch", value=ref, inline=True)

    # Show up to 5 commits
    commit_messages = []
    for i, commit in enumerate(commits[:5]):
        commit_messages.append(format_commit_message(commit))

    if commit_messages:
        embed.add_field(name="Commits", value="\n".join(commit_messages), inline=False)

    if len(commits) > 5:
        embed.add_field(
            name="", value=f"... and {len(commits) - 5} more commits", inline=False
        )

    return embed


def get_status_color(status: str, conclusion: Optional[str] = None) -> discord.Color:
    """Get Discord color based on status and conclusion."""
    if conclusion:
        if conclusion == "success":
            return discord.Color.green()
        elif conclusion == "failure":
            return discord.Color.red()
        elif conclusion == "cancelled":
            return discord.Color.light_grey()
        else:
            return discord.Color.orange()

    if status == "completed":
        return discord.Color.green()
    elif status in ["queued", "in_progress"]:
        return discord.Color.orange()
    elif status == "cancelled":
        return discord.Color.light_grey()
    else:
        return discord.Color.blue()


def get_status_icon(status: str, conclusion: Optional[str] = None) -> str:
    """Get emoji icon based on status and conclusion."""
    if conclusion:
        if conclusion == "success":
            return "✅"
        elif conclusion == "failure":
            return "❌"
        elif conclusion == "cancelled":
            return "🚫"
        else:
            return "⚠️"

    if status == "completed":
        return "✅"
    elif status == "queued":
        return "⏳"
    elif status == "in_progress":
        return "🔄"
    elif status == "cancelled":
        return "🚫"
    else:
        return "❓"


def calculate_duration(started_at: Optional[str], completed_at: Optional[str]) -> str:
    """Calculate and format duration between two timestamps."""
    if not started_at or not completed_at:
        return "N/A"

    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        duration = end - start

        total_seconds = int(duration.total_seconds())
        minutes = total_seconds // 60
        seconds = total_seconds % 60

        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    except Exception:
        return "N/A"


def format_workflow_run(event: Dict[str, Any]) -> discord.Embed:
    """Format a workflow run event for Discord."""
    workflow_run = event.get("workflow_run", {})
    repo = event.get("repository", {})

    name = workflow_run.get("name", "Unknown Workflow")
    run_id = workflow_run.get("id", 0)
    status = workflow_run.get("status", "unknown")
    conclusion = workflow_run.get("conclusion")
    head_branch = workflow_run.get("head_branch", "unknown")
    head_sha = workflow_run.get("head_sha", "")[:7]
    html_url = workflow_run.get("html_url", "")

    repo_name = repo.get("full_name", "Unknown repo")
    repo_url = repo.get("html_url", "")

    # Get appropriate color and icon
    color = get_status_color(status, conclusion)
    icon = get_status_icon(status, conclusion)

    # Calculate duration
    duration = calculate_duration(
        workflow_run.get("run_started_at"), workflow_run.get("updated_at")
    )

    # Format status display
    status_display = (
        conclusion.title() if conclusion else status.replace("_", " ").title()
    )

    embed = discord.Embed(
        title=f"{icon} Workflow Run: {name}", url=html_url, color=color
    )

    embed.add_field(name="Repository", value=f"[{repo_name}]({repo_url})", inline=True)

    embed.add_field(name="Branch", value=head_branch, inline=True)

    embed.add_field(name="Commit", value=f"`{head_sha}`", inline=True)

    embed.add_field(name="Status", value=status_display, inline=True)

    embed.add_field(name="Duration", value=duration, inline=True)

    embed.add_field(name="Run ID", value=f"#{run_id}", inline=True)

    return embed


def format_workflow_job(event: Dict[str, Any]) -> discord.Embed:
    """Format a workflow job event for Discord."""
    workflow_job = event.get("workflow_job", {})
    repo = event.get("repository", {})

    name = workflow_job.get("name", "Unknown Job")
    job_id = workflow_job.get("id", 0)
    run_id = workflow_job.get("run_id", 0)
    status = workflow_job.get("status", "unknown")
    conclusion = workflow_job.get("conclusion")
    head_sha = workflow_job.get("head_sha", "")[:7]
    html_url = workflow_job.get("html_url", "")

    repo_name = repo.get("full_name", "Unknown repo")
    repo_url = repo.get("html_url", "")

    # Get appropriate color and icon
    color = get_status_color(status, conclusion)
    icon = get_status_icon(status, conclusion)

    # Calculate duration
    duration = calculate_duration(
        workflow_job.get("started_at"), workflow_job.get("completed_at")
    )

    # Format status display
    status_display = (
        conclusion.title() if conclusion else status.replace("_", " ").title()
    )

    embed = discord.Embed(
        title=f"{icon} Workflow Job: {name}", url=html_url, color=color
    )

    embed.add_field(name="Repository", value=f"[{repo_name}]({repo_url})", inline=True)

    embed.add_field(name="Commit", value=f"`{head_sha}`", inline=True)

    embed.add_field(name="Status", value=status_display, inline=True)

    embed.add_field(name="Duration", value=duration, inline=True)

    embed.add_field(name="Job ID", value=f"#{job_id}", inline=True)

    embed.add_field(name="Run ID", value=f"#{run_id}", inline=True)

    return embed


def format_check_run(event: Dict[str, Any]) -> discord.Embed:
    """Format a check run event for Discord."""
    check_run = event.get("check_run", {})
    repo = event.get("repository", {})

    name = check_run.get("name", "Unknown Check")
    check_id = check_run.get("id", 0)
    status = check_run.get("status", "unknown")
    conclusion = check_run.get("conclusion")
    head_sha = check_run.get("head_sha", "")[:7]
    html_url = check_run.get("html_url", "")
    details_url = check_run.get("details_url", html_url)

    repo_name = repo.get("full_name", "Unknown repo")
    repo_url = repo.get("html_url", "")

    # Get appropriate color and icon
    color = get_status_color(status, conclusion)
    icon = get_status_icon(status, conclusion)

    # Calculate duration
    duration = calculate_duration(
        check_run.get("started_at"), check_run.get("completed_at")
    )

    # Format status display
    status_display = (
        conclusion.title() if conclusion else status.replace("_", " ").title()
    )

    # Get branch from check suite if available
    check_suite = check_run.get("check_suite", {})
    branch = check_suite.get("head_branch", "unknown")

    embed = discord.Embed(
        title=f"{icon} Check Run: {name}", url=details_url, color=color
    )

    embed.add_field(name="Repository", value=f"[{repo_name}]({repo_url})", inline=True)

    embed.add_field(name="Branch", value=branch, inline=True)

    embed.add_field(name="Commit", value=f"`{head_sha}`", inline=True)

    embed.add_field(name="Status", value=status_display, inline=True)

    embed.add_field(name="Duration", value=duration, inline=True)

    embed.add_field(name="Check ID", value=f"#{check_id}", inline=True)

    return embed


def format_check_suite(event: Dict[str, Any]) -> discord.Embed:
    """Format a check suite event for Discord."""
    check_suite = event.get("check_suite", {})
    repo = event.get("repository", {})

    suite_id = check_suite.get("id", 0)
    status = check_suite.get("status", "unknown")
    conclusion = check_suite.get("conclusion")
    head_branch = check_suite.get("head_branch", "unknown")
    head_sha = check_suite.get("head_sha", "")[:7]

    repo_name = repo.get("full_name", "Unknown repo")
    repo_url = repo.get("html_url", "")

    # Get appropriate color and icon
    color = get_status_color(status, conclusion)
    icon = get_status_icon(status, conclusion)

    # Calculate duration
    duration = calculate_duration(
        check_suite.get("created_at"), check_suite.get("updated_at")
    )

    # Format status display
    status_display = (
        conclusion.title() if conclusion else status.replace("_", " ").title()
    )

    # Get app name if available
    app = check_suite.get("app", {})
    app_name = app.get("name", "Unknown App")

    # Build URL to check suite (GitHub doesn't provide a direct HTML URL for check suites)
    suite_url = f"{repo_url}/commits/{head_sha}/checks"

    embed = discord.Embed(
        title=f"{icon} Check Suite: {app_name}", url=suite_url, color=color
    )

    embed.add_field(name="Repository", value=f"[{repo_name}]({repo_url})", inline=True)

    embed.add_field(name="Branch", value=head_branch, inline=True)

    embed.add_field(name="Commit", value=f"`{head_sha}`", inline=True)

    embed.add_field(name="Status", value=status_display, inline=True)

    embed.add_field(name="Duration", value=duration, inline=True)

    embed.add_field(name="Suite ID", value=f"#{suite_id}", inline=True)

    return embed


def format_pull_request_event(payload: Dict[str, Any]) -> discord.Embed:
    """Format a pull request event for Discord."""
    action = payload.get("action", "")
    pr = payload.get("pull_request", {})

    title = pr.get("title", "No title")
    number = pr.get("number", 0)
    url = pr.get("html_url", "")
    user = pr.get("user", {}).get("login", "Unknown")

    repo = payload.get("repository", {})
    repo_name = repo.get("full_name", "Unknown repo")

    # Color based on action
    color_map = {
        "opened": discord.Color.green(),
        "closed": discord.Color.red(),
        "reopened": discord.Color.orange(),
        "ready_for_review": discord.Color.blue(),
        "draft": discord.Color.light_grey(),
    }

    color = color_map.get(action, discord.Color.blue())

    # Icon based on action
    icon_map = {
        "opened": "🔓",
        "closed": "🔒",
        "reopened": "🔄",
        "ready_for_review": "👀",
        "draft": "📝",
    }

    icon = icon_map.get(action, "📋")

    embed = discord.Embed(
        title=f"{icon} Pull Request #{number}: {title}", url=url, color=color
    )

    embed.add_field(name="Repository", value=repo_name, inline=True)

    embed.add_field(name="Author", value=user, inline=True)

    embed.add_field(name="Action", value=action.replace("_", " ").title(), inline=True)

    # Add description if available
    body = pr.get("body", "")
    if body:
        # Truncate long descriptions
        if len(body) > 200:
            body = body[:200] + "..."
        embed.add_field(name="Description", value=body, inline=False)

    return embed


def format_merge_event(payload: Dict[str, Any]) -> discord.Embed:
    """Format a merged pull request event for Discord."""
    pr = payload.get("pull_request", {})

    title = pr.get("title", "No title")
    number = pr.get("number", 0)
    url = pr.get("html_url", "")
    user = pr.get("user", {}).get("login", "Unknown")
    merged_by = pr.get("merged_by", {}).get("login", "Unknown")

    repo = payload.get("repository", {})
    repo_name = repo.get("full_name", "Unknown repo")

    embed = discord.Embed(
        title=f"🎉 Pull Request #{number} Merged: {title}",
        url=url,
        color=discord.Color.purple(),
    )

    embed.add_field(name="Repository", value=repo_name, inline=True)

    embed.add_field(name="Author", value=user, inline=True)

    embed.add_field(name="Merged by", value=merged_by, inline=True)

    return embed


def format_issue_event(payload: Dict[str, Any]) -> discord.Embed:
    """Format an issue event for Discord."""
    action = payload.get("action", "")
    issue = payload.get("issue", {})

    title = issue.get("title", "No title")
    number = issue.get("number", 0)
    url = issue.get("html_url", "")
    user = issue.get("user", {}).get("login", "Unknown")

    repo = payload.get("repository", {})
    repo_name = repo.get("full_name", "Unknown repo")

    # Color based on action
    color_map = {
        "opened": discord.Color.green(),
        "closed": discord.Color.red(),
        "reopened": discord.Color.orange(),
        "assigned": discord.Color.blue(),
        "unassigned": discord.Color.light_grey(),
    }

    color = color_map.get(action, discord.Color.blue())

    # Icon based on action
    icon_map = {
        "opened": "🐛",
        "closed": "✅",
        "reopened": "🔄",
        "assigned": "👤",
        "unassigned": "👥",
    }

    icon = icon_map.get(action, "📋")

    embed = discord.Embed(
        title=f"{icon} Issue #{number}: {title}", url=url, color=color
    )

    embed.add_field(name="Repository", value=repo_name, inline=True)

    embed.add_field(name="Author", value=user, inline=True)

    embed.add_field(name="Action", value=action.replace("_", " ").title(), inline=True)

    return embed


def format_release_event(payload: Dict[str, Any]) -> discord.Embed:
    """Format a release event for Discord."""
    action = payload.get("action", "")
    release = payload.get("release", {})

    tag_name = release.get("tag_name", "No tag")
    name = release.get("name", tag_name)
    url = release.get("html_url", "")
    author = release.get("author", {}).get("login", "Unknown")

    repo = payload.get("repository", {})
    repo_name = repo.get("full_name", "Unknown repo")

    embed = discord.Embed(
        title=f"🚀 Release {action}: {name}", url=url, color=discord.Color.gold()
    )

    embed.add_field(name="Repository", value=repo_name, inline=True)

    embed.add_field(name="Tag", value=tag_name, inline=True)

    embed.add_field(name="Author", value=author, inline=True)

    body = release.get("body", "")
    if body:
        # Truncate long descriptions
        if len(body) > 300:
            body = body[:300] + "..."
        embed.add_field(name="Release Notes", value=body, inline=False)

    return embed


def format_deployment_event(payload: Dict[str, Any]) -> discord.Embed:
    """Format a deployment status event for Discord."""
    deployment = payload.get("deployment", {})
    deployment_status = payload.get("deployment_status", {})

    environment = deployment.get("environment", "Unknown")
    state = deployment_status.get("state", "Unknown")
    target_url = deployment_status.get("target_url", "")

    repo = payload.get("repository", {})
    repo_name = repo.get("full_name", "Unknown repo")

    # Color based on state
    color_map = {
        "success": discord.Color.green(),
        "failure": discord.Color.red(),
        "pending": discord.Color.orange(),
        "error": discord.Color.red(),
    }

    color = color_map.get(state, discord.Color.blue())

    # Icon based on state
    icon_map = {"success": "✅", "failure": "❌", "pending": "⏳", "error": "🚨"}

    icon = icon_map.get(state, "🚀")

    embed = discord.Embed(
        title=f"{icon} Deployment to {environment}: {state}",
        url=target_url if target_url else None,
        color=color,
    )

    embed.add_field(name="Repository", value=repo_name, inline=True)

    embed.add_field(name="Environment", value=environment, inline=True)

    embed.add_field(name="Status", value=state.title(), inline=True)

    return embed


def format_gollum_event(payload: Dict[str, Any]) -> discord.Embed:
    """Format a wiki (gollum) event for Discord."""
    pages = payload.get("pages", [])

    repo = payload.get("repository", {})
    repo_name = repo.get("full_name", "Unknown repo")

    sender = payload.get("sender", {}).get("login", "Unknown")

    embed = discord.Embed(title="📚 Wiki Updated", color=discord.Color.blue())

    embed.add_field(name="Repository", value=repo_name, inline=True)

    embed.add_field(name="Updated by", value=sender, inline=True)

    if pages:
        page_info = []
        for page in pages[:3]:  # Show up to 3 pages
            title = page.get("title", "Unknown")
            action = page.get("action", "modified")
            url = page.get("html_url", "")

            if url:
                page_info.append(f"[{title}]({url}) ({action})")
            else:
                page_info.append(f"{title} ({action})")

        embed.add_field(name="Pages", value="\n".join(page_info), inline=False)

        if len(pages) > 3:
            embed.add_field(
                name="", value=f"... and {len(pages) - 3} more pages", inline=False
            )

    return embed


def format_generic_event(event_type: str, payload: Dict[str, Any]) -> discord.Embed:
    """Format a generic/unknown event for Discord."""
    repo = payload.get("repository", {})
    repo_name = repo.get("full_name", "Unknown repo")

    sender = payload.get("sender", {}).get("login", "Unknown")
    action = payload.get("action", "")

    embed = discord.Embed(
        title=f"🔍 {event_type.replace('_', ' ').title()} Event",
        color=discord.Color.light_grey(),
    )

    embed.add_field(name="Repository", value=repo_name, inline=True)

    embed.add_field(name="Sender", value=sender, inline=True)

    if action:
        embed.add_field(
            name="Action", value=action.replace("_", " ").title(), inline=True
        )

    embed.add_field(name="Event Type", value=event_type, inline=False)

    return embed
