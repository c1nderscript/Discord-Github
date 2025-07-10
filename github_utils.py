"""Utility functions for interacting with the GitHub API."""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

import aiohttp
from fastapi import Request, HTTPException

from config import settings

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


async def verify_github_signature(request: Request, body: bytes) -> None:
    """Verify the GitHub webhook signature if a secret is configured."""
    if not settings.github_webhook_secret:
        return

    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")

    expected = hmac.new(settings.github_webhook_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    expected = f"sha256={expected}"
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid signature")


def is_github_event_relevant(event_type: str, payload: dict) -> bool:
    """Return ``True`` if the event should be processed."""
    skip = {
        "pull_request": ["synchronize", "edited", "review_requested"],
        "issues": ["edited", "labeled", "unlabeled"],
        "push": [],
    }
    action = payload.get("action")
    return not (event_type in skip and action in skip[event_type])


def _extract_total_from_link(link_header: Optional[str]) -> int:
    if not link_header or 'rel="last"' not in link_header:
        return 1
    match = re.search(r"page=(\d+)>; rel=\"last\"", link_header)
    return int(match.group(1)) if match else 1


@dataclass
class RepoStats:
    name: str
    commit_count: int
    pr_count: int
    merge_count: int


async def gather_repo_stats() -> List[RepoStats]:
    """Return commit, pull request and merge counts for all user repositories."""
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

            commits_url = f"{GITHUB_API_BASE}/search/commits"
            pulls_url = f"{GITHUB_API_BASE}/repos/{full_name}/pulls?state=all&per_page=1"
            merges_url = f"{GITHUB_API_BASE}/search/issues?q=repo:{full_name}+is:pr+is:merged&per_page=1"

            async with session.get(f"{commits_url}?q=repo:{full_name}&per_page=1", headers=headers) as r:
                commit_count = 0
                if r.status == 200:
                    data = await r.json()
                    commit_count = int(data.get("total_count", 0))

            async with session.get(pulls_url, headers=headers) as r:
                pr_count = 0
                if r.status == 200:
                    await r.json()
                    pr_count = _extract_total_from_link(r.headers.get("Link"))

            async with session.get(merges_url, headers=headers) as r:
                merged_count = 0
                if r.status == 200:
                    data = await r.json()
                    merged_count = int(data.get("total_count", 0))

            stats.append(RepoStats(full_name, commit_count, pr_count, merged_count))

    return stats


async def fetch_repo_stats() -> Tuple[List[Dict[str, int]], Dict[str, int]]:
    """Return statistics for repositories owned by ``settings.github_username``."""
    if not settings.github_username:
        raise ValueError("github_username not configured")

    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"

    repos_url = f"{GITHUB_API_BASE}/user/repos"
    async with aiohttp.ClientSession() as session:
        async with session.get(repos_url, headers=headers) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Failed to list repos: {resp.status}")
            repos = await resp.json()

        repo_stats: List[Dict[str, int]] = []
        totals = {"commits": 0, "pull_requests": 0, "merged_pull_requests": 0}

        for repo in repos:
            full_name = repo.get("full_name")
            if not full_name:
                continue

            commits_url = f"{GITHUB_API_BASE}/search/commits"
            pulls_url = f"{GITHUB_API_BASE}/search/issues"
            search_url = f"{GITHUB_API_BASE}/search/issues"

            async with session.get(commits_url, headers=headers, params={"q": f"repo:{full_name}", "per_page": 1}) as r:
                commit_count = 0
                if r.status == 200:
                    data = await r.json()
                    commit_count = int(data.get("total_count", 0))

            async with session.get(pulls_url, headers=headers, params={"q": f"repo:{full_name}+type:pr", "per_page": 1}) as r:
                pr_count = 0
                if r.status == 200:
                    data = await r.json()
                    pr_count = int(data.get("total_count", 0))

            async with session.get(search_url, headers=headers, params={"q": f"repo:{full_name}+type:pr+is:merged", "per_page": 1}) as r:
                merged_count = 0
                if r.status == 200:
                    data = await r.json()
                    merged_count = int(data.get("total_count", 0))

            repo_stats.append(
                {
                    "name": full_name,
                    "commits": commit_count,
                    "pull_requests": pr_count,
                    "merged_pull_requests": merged_count,
                }
            )
            totals["commits"] += commit_count
            totals["pull_requests"] += pr_count
            totals["merged_pull_requests"] += merged_count

    return repo_stats, totals
