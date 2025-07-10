"""GitHub utility functions for webhook handling and repo statistics."""

import hashlib
import hmac
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import aiohttp
from fastapi import HTTPException, Request

from config import settings

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


async def verify_github_signature(request: Request, body: bytes) -> None:
    """Verify the GitHub webhook signature."""
    if not settings.github_webhook_secret:
        return

    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")

    expected_signature = hmac.new(
        settings.github_webhook_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    expected_signature = f"sha256={expected_signature}"

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")


def is_github_event_relevant(event_type: str, payload: dict) -> bool:
    """Return ``True`` if the event should be processed."""
    skip_actions = {
        "pull_request": ["synchronize", "edited", "review_requested"],
        "issues": ["edited", "labeled", "unlabeled"],
        "push": [],
    }
    if event_type in skip_actions:
        action = payload.get("action")
        if action in skip_actions[event_type]:
            return False
    return True


async def _extract_total_from_link(link_header: Optional[str]) -> int:
    """Extract the last page number from a GitHub pagination link header."""
    if not link_header or 'rel="last"' not in link_header:
        return 1
    for part in link_header.split(','):
        if 'rel="last"' in part:
            url_part = part.split(';')[0].strip('<> ')
            if "page=" in url_part:
                try:
                    return int(url_part.split("page=")[-1].split("&")[0])
                except ValueError:
                    return 1
    return 1


async def _get_paginated_count(session: aiohttp.ClientSession, url: str, headers: Dict[str, str]) -> int:
    """Return the total item count for a paginated GitHub API endpoint."""
    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            return 0
        if "Link" in resp.headers:
            match = re.search(r"page=(\d+)>; rel=\"last\"", resp.headers["Link"])
            if match:
                return int(match.group(1))
        data = await resp.json()
        return len(data)


@dataclass
class RepoStats:
    """Statistics for a single GitHub repository."""

    name: str
    commit_count: int
    pr_count: int
    merge_count: int


async def gather_repo_stats() -> List[RepoStats]:
    """Gather commit, PR and merge counts for all user repositories."""
    if not settings.github_token:
        return []

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {settings.github_token}",
    }
    repos_url = f"{GITHUB_API_BASE}/user/repos?per_page=100&affiliation=owner"
    stats: List[RepoStats] = []

    async with aiohttp.ClientSession() as session:
        async with session.get(repos_url, headers=headers) as resp:
            if resp.status != 200:
                return stats
            repositories = await resp.json()

        for repo in repositories:
            full_name = repo.get("full_name")
            if not full_name:
                continue

            commits_url = f"{GITHUB_API_BASE}/repos/{full_name}/commits?per_page=1"
            commit_count = await _get_paginated_count(session, commits_url, headers)

            prs_url = f"{GITHUB_API_BASE}/search/issues?q=repo:{full_name}+type:pr"
            merges_url = f"{GITHUB_API_BASE}/search/issues?q=repo:{full_name}+is:pr+is:merged"

            async with session.get(prs_url, headers=headers) as resp:
                pr_data = await resp.json() if resp.status == 200 else {}
                pr_count = pr_data.get("total_count", 0)

            async with session.get(merges_url, headers=headers) as resp:
                merge_data = await resp.json() if resp.status == 200 else {}
                merge_count = merge_data.get("total_count", 0)

            stats.append(
                RepoStats(
                    name=full_name,
                    commit_count=commit_count,
                    pr_count=pr_count,
                    merge_count=merge_count,
                )
            )
    return stats


async def _fetch_total_count(
    session: aiohttp.ClientSession,
    url: str,
    headers: Dict[str, str],
    params: Dict[str, str],
) -> int:
    """Helper to fetch the GitHub API ``total_count`` value."""
    try:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status != 200:
                logger.error("Failed request %s: %s", url, resp.status)
                return 0
            data = await resp.json()
            return int(data.get("total_count", 0))
    except Exception as exc:
        logger.error("Error fetching %s: %s", url, exc)
        return 0


async def fetch_repo_stats() -> Tuple[List[Dict[str, int]], Dict[str, int]]:
    """Gather commit and pull request statistics for all owned repositories."""
    if not settings.github_username:
        raise ValueError("github_username not configured")

    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"

    repos_url = f"{GITHUB_API_BASE}/users/{settings.github_username}/repos"

    async with aiohttp.ClientSession() as session:
        async with session.get(repos_url, headers=headers) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Failed to list repos: {resp.status}")
            repos = await resp.json()

        stats: Dict[str, Dict[str, int]] = {}
        totals = {"commits": 0, "pull_requests": 0, "merged_pull_requests": 0}

        for repo in repos:
            full_name = repo.get("full_name")
            if not full_name:
                continue

            commits_url = f"{GITHUB_API_BASE}/repos/{full_name}/commits?per_page=1"
            async with session.get(commits_url, headers=headers) as r:
                commit_count = 0
                if r.status == 200:
                    await r.json()
                    commit_count = await _extract_total_from_link(r.headers.get("Link"))

            pulls_url = f"{GITHUB_API_BASE}/repos/{full_name}/pulls?state=all&per_page=1"
            async with session.get(pulls_url, headers=headers) as r:
                pr_count = 0
                if r.status == 200:
                    await r.json()
                    pr_count = await _extract_total_from_link(r.headers.get("Link"))

            search_url = f"{GITHUB_API_BASE}/search/issues?q=repo:{full_name}+is:pr+is:merged&per_page=1"
            async with session.get(search_url, headers=headers) as r:
                merged_count = 0
                if r.status == 200:
                    data = await r.json()
                    merged_count = int(data.get("total_count", 0))

            stats[full_name] = {
                "commits": commit_count,
                "pull_requests": pr_count,
                "merged_pull_requests": merged_count,
            }

            totals["commits"] += commit_count
            totals["pull_requests"] += pr_count
            totals["merged_pull_requests"] += merged_count

    return stats, totals
