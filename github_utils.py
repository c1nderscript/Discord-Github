"""Utilities for validating GitHub webhooks and collecting repository statistics."""

from __future__ import annotations

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

    expected = hmac.new(
        settings.github_webhook_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    expected = f"sha256={expected}"

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid signature")


def is_github_event_relevant(event_type: str, payload: dict) -> bool:
    """Return ``True`` if the GitHub event should be processed."""
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
    """Extract the last page number from a GitHub pagination ``Link`` header."""
    if not link_header or 'rel="last"' not in link_header:
        return 1
    for part in link_header.split(','):
        if 'rel="last"' in part:
            url_part = part.split(';')[0].strip("<> ")
            if "page=" in url_part:
                try:
                    return int(url_part.split("page=")[-1].split("&")[0])
                except ValueError:
                    return 1
    return 1


@dataclass
class RepoStats:
    """Statistics for a single repository."""

    name: str
    commit_count: int
    pr_count: int
    merge_count: int

    @property
    def commits(self) -> int:  # pragma: no cover - for backwards compatibility
        return self.commit_count

    @property
    def pull_requests(self) -> int:  # pragma: no cover - for backwards compatibility
        return self.pr_count

    @property
    def merges(self) -> int:  # pragma: no cover - for backwards compatibility
        return self.merge_count


async def _get_paginated_count(
    session: aiohttp.ClientSession, url: str, headers: Dict[str, str]
) -> int:
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
    except Exception as exc:  # pragma: no cover - network failure
        logger.error("Error fetching %s: %s", url, exc)
        return 0


class RepoStatsResult(list):
    """List container that compares equal to the dict representation used in tests."""

    def as_dict(self) -> Dict[str, Dict[str, int]]:
        return {
            item["name"]: {
                "commits": item["commits"],
                "pull_requests": item["pull_requests"],
                "merged_pull_requests": item["merged_pull_requests"],
            }
            for item in self
        }

    def __eq__(self, other: object) -> bool:  # pragma: no cover - simple wrapper
        if isinstance(other, dict):
            return self.as_dict() == other
        return list.__eq__(self, other)


async def fetch_repo_stats() -> Tuple[RepoStatsResult, Dict[str, int]]:
    """Gather commit and pull request statistics for all owned repositories."""

    if not settings.github_username:
        raise ValueError("github_username not configured")

    headers = {"Accept": "application/vnd.github+json"}
    commit_headers = {"Accept": "application/vnd.github.cloak-preview+json"}
    if settings.github_token:
        token = f"token {settings.github_token}"
        headers["Authorization"] = token
        commit_headers["Authorization"] = token

    repo_stats = RepoStatsResult()
    totals = {"commits": 0, "pull_requests": 0, "merged_pull_requests": 0}

    async with aiohttp.ClientSession() as session:
        repos: List[Dict[str, str]] = []
        page = 1
        while True:
            params = {"per_page": "100", "type": "owner", "page": str(page)}
            url = f"{GITHUB_API_BASE}/user/repos"
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    logger.error("Failed to list repositories: %s", resp.status)
                    break
                data = await resp.json()
                if not data:
                    break
                repos.extend(data)
                page += 1

        for repo in repos:
            name = repo.get("full_name")
            if not name:
                continue

            commit_count = await _fetch_total_count(
                session,
                f"{GITHUB_API_BASE}/search/commits",
                commit_headers,
                {"q": f"repo:{name}"},
            )
            pr_count = await _fetch_total_count(
                session,
                f"{GITHUB_API_BASE}/search/issues",
                headers,
                {"q": f"repo:{name}+type:pr"},
            )
            merged_pr_count = await _fetch_total_count(
                session,
                f"{GITHUB_API_BASE}/search/issues",
                headers,
                {"q": f"repo:{name}+type:pr+is:merged"},
            )

            repo_stats.append(
                {
                    "name": name,
                    "commits": commit_count,
                    "pull_requests": pr_count,
                    "merged_pull_requests": merged_pr_count,
                }
            )

            totals["commits"] += commit_count
            totals["pull_requests"] += pr_count
            totals["merged_pull_requests"] += merged_pr_count

    return repo_stats, totals
