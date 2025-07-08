"""Formatters for GitHub webhook events to Discord messages."""

import discord
from typing import Dict, Any, Optional
from datetime import datetime


def format_commit_message(commit: Dict[str, Any]) -> str:
    """Format a single commit for display."""
    author = commit.get('author', {}).get('name', 'Unknown')
    message = commit.get('message', 'No message')
    url = commit.get('url', '')
    commit_id = commit.get('id', '')[:7]  # Short commit hash
    
    return f"[`{commit_id}`]({url}) {message} - {author}"


def format_push_event(payload: Dict[str, Any]) -> discord.Embed:
    """Format a push event for Discord."""
    repo = payload.get('repository', {})
    repo_name = repo.get('full_name', 'Unknown repo')
    repo_url = repo.get('html_url', '')
    
    pusher = payload.get('pusher', {}).get('name', 'Unknown')
    ref = payload.get('ref', '').replace('refs/heads/', '')
    
    commits = payload.get('commits', [])
    commit_count = len(commits)
    
    embed = discord.Embed(
        title=f"📝 {commit_count} commit{'s' if commit_count != 1 else ''} pushed to {ref}",
        url=f"{repo_url}/commits/{ref}",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="Repository",
        value=f"[{repo_name}]({repo_url})",
        inline=True
    )
    
    embed.add_field(
        name="Pusher",
        value=pusher,
        inline=True
    )
    
    embed.add_field(
        name="Branch",
        value=ref,
        inline=True
    )
    
    # Show up to 5 commits
    commit_messages = []
    for i, commit in enumerate(commits[:5]):
        commit_messages.append(format_commit_message(commit))
    
    if commit_messages:
        embed.add_field(
            name="Commits",
            value="\n".join(commit_messages),
            inline=False
        )
    
    if len(commits) > 5:
        embed.add_field(
            name="",
            value=f"... and {len(commits) - 5} more commits",
            inline=False
        )
    
    return embed


def format_pull_request_event(payload: Dict[str, Any]) -> discord.Embed:
    """Format a pull request event for Discord."""
    action = payload.get('action', '')
    pr = payload.get('pull_request', {})
    
    title = pr.get('title', 'No title')
    number = pr.get('number', 0)
    url = pr.get('html_url', '')
    user = pr.get('user', {}).get('login', 'Unknown')
    
    repo = payload.get('repository', {})
    repo_name = repo.get('full_name', 'Unknown repo')
    
    # Color based on action
    color_map = {
        'opened': discord.Color.green(),
        'closed': discord.Color.red(),
        'reopened': discord.Color.orange(),
        'ready_for_review': discord.Color.blue(),
        'draft': discord.Color.grey()
    }
    
    color = color_map.get(action, discord.Color.blue())
    
    # Icon based on action
    icon_map = {
        'opened': '🔓',
        'closed': '🔒',
        'reopened': '🔄',
        'ready_for_review': '👀',
        'draft': '📝'
    }
    
    icon = icon_map.get(action, '📋')
    
    embed = discord.Embed(
        title=f"{icon} Pull Request #{number}: {title}",
        url=url,
        color=color
    )
    
    embed.add_field(
        name="Repository",
        value=repo_name,
        inline=True
    )
    
    embed.add_field(
        name="Author",
        value=user,
        inline=True
    )
    
    embed.add_field(
        name="Action",
        value=action.replace('_', ' ').title(),
        inline=True
    )
    
    # Add description if available
    body = pr.get('body', '')
    if body:
        # Truncate long descriptions
        if len(body) > 200:
            body = body[:200] + "..."
        embed.add_field(
            name="Description",
            value=body,
            inline=False
        )
    
    return embed


def format_merge_event(payload: Dict[str, Any]) -> discord.Embed:
    """Format a merged pull request event for Discord."""
    pr = payload.get('pull_request', {})
    
    title = pr.get('title', 'No title')
    number = pr.get('number', 0)
    url = pr.get('html_url', '')
    user = pr.get('user', {}).get('login', 'Unknown')
    merged_by = pr.get('merged_by', {}).get('login', 'Unknown')
    
    repo = payload.get('repository', {})
    repo_name = repo.get('full_name', 'Unknown repo')
    
    embed = discord.Embed(
        title=f"🎉 Pull Request #{number} Merged: {title}",
        url=url,
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="Repository",
        value=repo_name,
        inline=True
    )
    
    embed.add_field(
        name="Author",
        value=user,
        inline=True
    )
    
    embed.add_field(
        name="Merged by",
        value=merged_by,
        inline=True
    )
    
    return embed


def format_issue_event(payload: Dict[str, Any]) -> discord.Embed:
    """Format an issue event for Discord."""
    action = payload.get('action', '')
    issue = payload.get('issue', {})
    
    title = issue.get('title', 'No title')
    number = issue.get('number', 0)
    url = issue.get('html_url', '')
    user = issue.get('user', {}).get('login', 'Unknown')
    
    repo = payload.get('repository', {})
    repo_name = repo.get('full_name', 'Unknown repo')
    
    # Color based on action
    color_map = {
        'opened': discord.Color.green(),
        'closed': discord.Color.red(),
        'reopened': discord.Color.orange(),
        'assigned': discord.Color.blue(),
        'unassigned': discord.Color.grey()
    }
    
    color = color_map.get(action, discord.Color.blue())
    
    # Icon based on action
    icon_map = {
        'opened': '🐛',
        'closed': '✅',
        'reopened': '🔄',
        'assigned': '👤',
        'unassigned': '👥'
    }
    
    icon = icon_map.get(action, '📋')
    
    embed = discord.Embed(
        title=f"{icon} Issue #{number}: {title}",
        url=url,
        color=color
    )
    
    embed.add_field(
        name="Repository",
        value=repo_name,
        inline=True
    )
    
    embed.add_field(
        name="Author",
        value=user,
        inline=True
    )
    
    embed.add_field(
        name="Action",
        value=action.replace('_', ' ').title(),
        inline=True
    )
    
    return embed


def format_release_event(payload: Dict[str, Any]) -> discord.Embed:
    """Format a release event for Discord."""
    action = payload.get('action', '')
    release = payload.get('release', {})
    
    tag_name = release.get('tag_name', 'No tag')
    name = release.get('name', tag_name)
    url = release.get('html_url', '')
    author = release.get('author', {}).get('login', 'Unknown')
    
    repo = payload.get('repository', {})
    repo_name = repo.get('full_name', 'Unknown repo')
    
    embed = discord.Embed(
        title=f"🚀 Release {action}: {name}",
        url=url,
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="Repository",
        value=repo_name,
        inline=True
    )
    
    embed.add_field(
        name="Tag",
        value=tag_name,
        inline=True
    )
    
    embed.add_field(
        name="Author",
        value=author,
        inline=True
    )
    
    body = release.get('body', '')
    if body:
        # Truncate long descriptions
        if len(body) > 300:
            body = body[:300] + "..."
        embed.add_field(
            name="Release Notes",
            value=body,
            inline=False
        )
    
    return embed


def format_deployment_event(payload: Dict[str, Any]) -> discord.Embed:
    """Format a deployment status event for Discord."""
    deployment = payload.get('deployment', {})
    deployment_status = payload.get('deployment_status', {})
    
    environment = deployment.get('environment', 'Unknown')
    state = deployment_status.get('state', 'Unknown')
    target_url = deployment_status.get('target_url', '')
    
    repo = payload.get('repository', {})
    repo_name = repo.get('full_name', 'Unknown repo')
    
    # Color based on state
    color_map = {
        'success': discord.Color.green(),
        'failure': discord.Color.red(),
        'pending': discord.Color.orange(),
        'error': discord.Color.red()
    }
    
    color = color_map.get(state, discord.Color.blue())
    
    # Icon based on state
    icon_map = {
        'success': '✅',
        'failure': '❌',
        'pending': '⏳',
        'error': '🚨'
    }
    
    icon = icon_map.get(state, '🚀')
    
    embed = discord.Embed(
        title=f"{icon} Deployment to {environment}: {state}",
        url=target_url if target_url else None,
        color=color
    )
    
    embed.add_field(
        name="Repository",
        value=repo_name,
        inline=True
    )
    
    embed.add_field(
        name="Environment",
        value=environment,
        inline=True
    )
    
    embed.add_field(
        name="Status",
        value=state.title(),
        inline=True
    )
    
    return embed


def format_gollum_event(payload: Dict[str, Any]) -> discord.Embed:
    """Format a wiki (gollum) event for Discord."""
    pages = payload.get('pages', [])
    
    repo = payload.get('repository', {})
    repo_name = repo.get('full_name', 'Unknown repo')
    
    sender = payload.get('sender', {}).get('login', 'Unknown')
    
    embed = discord.Embed(
        title="📚 Wiki Updated",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="Repository",
        value=repo_name,
        inline=True
    )
    
    embed.add_field(
        name="Updated by",
        value=sender,
        inline=True
    )
    
    if pages:
        page_info = []
        for page in pages[:3]:  # Show up to 3 pages
            title = page.get('title', 'Unknown')
            action = page.get('action', 'modified')
            url = page.get('html_url', '')
            
            if url:
                page_info.append(f"[{title}]({url}) ({action})")
            else:
                page_info.append(f"{title} ({action})")
        
        embed.add_field(
            name="Pages",
            value="\n".join(page_info),
            inline=False
        )
        
        if len(pages) > 3:
            embed.add_field(
                name="",
                value=f"... and {len(pages) - 3} more pages",
                inline=False
            )
    
    return embed


def format_generic_event(event_type: str, payload: Dict[str, Any]) -> discord.Embed:
    """Format a generic/unknown event for Discord."""
    repo = payload.get('repository', {})
    repo_name = repo.get('full_name', 'Unknown repo')
    
    sender = payload.get('sender', {}).get('login', 'Unknown')
    action = payload.get('action', '')
    
    embed = discord.Embed(
        title=f"🔍 {event_type.replace('_', ' ').title()} Event",
        color=discord.Color.light_grey()
    )
    
    embed.add_field(
        name="Repository",
        value=repo_name,
        inline=True
    )
    
    embed.add_field(
        name="Sender",
        value=sender,
        inline=True
    )
    
    if action:
        embed.add_field(
            name="Action",
            value=action.replace('_', ' ').title(),
            inline=True
        )
    
    embed.add_field(
        name="Event Type",
        value=event_type,
        inline=False
    )
    
    return embed
