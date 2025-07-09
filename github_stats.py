"""Utilities for fetching GitHub repository statistics."""

import asyncio
import logging
from dataclasses import dataclass
from typing import List

import aiohttp

from config import settings
from discord_bot import discord_bot_instance
from formatters import (
    format_repo_commit_stats,
    format_repo_pr_stats,
    format_repo_merge_stats,
)
from stats_map import load_stats_map, save_stats_map

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

logger = logging.getLogger(__name__)


@dataclass
class RepoStats:
    """Simple repository statistics."""

    name: str
    url: str
    commits: int
    pull_requests: int
    merges: int


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


async def fetch_repositories(session: aiohttp.ClientSession) -> List[dict]:
    """Retrieve repositories for the configured GitHub user."""
    username = settings.github_username
    repos: List[dict] = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        async with session.get(url, headers=_headers()) as resp:
            if resp.status != 200:
                logger.error("Failed to fetch repositories: %s", resp.status)
                break
            data = await resp.json()
            repos.extend(data)
            if len(data) < 100:
                break
            page += 1
    return repos


async def fetch_repo_stats(session: aiohttp.ClientSession, owner: str, name: str) -> RepoStats:
    """Fetch commit, PR and merge counts for a repository."""
    query = """
    query($owner:String!, $name:String!){
      repository(owner:$owner,name:$name){
        url
        defaultBranchRef{ target{ ... on Commit{ history{ totalCount } } } }
        pullRequests{ totalCount }
        merged: pullRequests(states:MERGED){ totalCount }
      }
    }
    """
    variables = {"owner": owner, "name": name}
    async with session.post(
        GITHUB_GRAPHQL_URL,
        json={"query": query, "variables": variables},
        headers=_headers(),
    ) as resp:
        if resp.status != 200:
            logger.error("Failed to fetch stats for %s/%s: %s", owner, name, resp.status)
            return RepoStats(name=name, url="", commits=0, pull_requests=0, merges=0)
        result = await resp.json()
        repo = result.get("data", {}).get("repository", {})
        url = repo.get("url", "")
        commits = repo.get("defaultBranchRef", {}).get("target", {}).get("history", {}).get("totalCount", 0)
        prs = repo.get("pullRequests", {}).get("totalCount", 0)
        merges = repo.get("merged", {}).get("totalCount", 0)
        return RepoStats(name=name, url=url, commits=commits, pull_requests=prs, merges=merges)


async def update_repository_stats() -> None:
    """Fetch repository statistics and update Discord channels."""
    try:
        await discord_bot_instance.bot.wait_until_ready()
    except RuntimeError:
        # Bot was not started; skip updating in tests
        return
    stats_map = load_stats_map()
    async with aiohttp.ClientSession() as session:
        repos = await fetch_repositories(session)
        tasks = []
        for repo in repos:
            owner = repo.get("owner", {}).get("login")
            name = repo.get("name")
            if not owner or not name:
                continue
            tasks.append(fetch_repo_stats(session, owner, name))
        repo_stats_list = await asyncio.gather(*tasks)

    total_commits = sum(r.commits for r in repo_stats_list)
    total_prs = sum(r.pull_requests for r in repo_stats_list)
    total_merges = sum(r.merges for r in repo_stats_list)

    await discord_bot_instance.edit_channel_name(
        settings.channel_total_commits, f"{total_commits}-commits"
    )
    await discord_bot_instance.edit_channel_name(
        settings.channel_total_pull_requests, f"{total_prs}-pull-requests"
    )
    await discord_bot_instance.edit_channel_name(
        settings.channel_total_merges, f"{total_merges}-merges"
    )

    for stats in repo_stats_list:
        commit_embed = format_repo_commit_stats(stats.name, stats.url, stats.commits)
        pr_embed = format_repo_pr_stats(stats.name, stats.url, stats.pull_requests)
        merge_embed = format_repo_merge_stats(stats.name, stats.url, stats.merges)

        commit_key = f"{stats.name}#commits"
        pr_key = f"{stats.name}#prs"
        merge_key = f"{stats.name}#merges"

        commit_id = stats_map.get(commit_key)
        pr_id = stats_map.get(pr_key)
        merge_id = stats_map.get(merge_key)

        commit_id = await discord_bot_instance.send_or_update_embed(
            settings.channel_total_commits, commit_id, commit_embed
        )
        pr_id = await discord_bot_instance.send_or_update_embed(
            settings.channel_total_pull_requests, pr_id, pr_embed
        )
        merge_id = await discord_bot_instance.send_or_update_embed(
            settings.channel_total_merges, merge_id, merge_embed
        )

        if commit_id:
            stats_map[commit_key] = commit_id
        if pr_id:
            stats_map[pr_key] = pr_id
        if merge_id:
            stats_map[merge_key] = merge_id

    save_stats_map(stats_map)
