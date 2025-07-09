"""GitHub webhook utilities for signature verification."""

import hashlib
import hmac
from fastapi import Request, HTTPException
from typing import Optional, List
from dataclasses import dataclass
import re
import aiohttp

from config import settings


async def verify_github_signature(request: Request, body: bytes) -> None:
    """Verify the GitHub webhook signature."""
    if not settings.github_webhook_secret:
        # If no secret is configured, skip verification
        return
    
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")
    
    # Calculate the expected signature
    expected_signature = hmac.new(
        settings.github_webhook_secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()
    
    # GitHub prefixes the signature with "sha256="
    expected_signature = f"sha256={expected_signature}"
    
    # Compare signatures
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")


def is_github_event_relevant(event_type: str, payload: dict) -> bool:
    """Check if the GitHub event is relevant and should be processed."""
    # Skip some events that might be too noisy
    skip_actions = {
        "pull_request": ["synchronize", "edited", "review_requested"],
        "issues": ["edited", "labeled", "unlabeled"],
        "push": []  # Process all push events
    }
    
    if event_type in skip_actions:
        action = payload.get("action")
        if action in skip_actions[event_type]:
            return False
    
    return True


@dataclass
class RepoStats:
    """Statistics for a single GitHub repository."""

    name: str
    commit_count: int
    pr_count: int
    merge_count: int


async def _get_paginated_count(
    session: aiohttp.ClientSession, url: str, headers: dict
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

    headers = {"Accept": "application/vnd.github+json", "Authorization": f"token {settings.github_token}"}

    repos_url = "https://api.github.com/user/repos?per_page=100&affiliation=owner"
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

            commits_url = f"https://api.github.com/repos/{full_name}/commits?per_page=1"
            commit_count = await _get_paginated_count(session, commits_url, headers)

            prs_url = (
                f"https://api.github.com/search/issues?q=repo:{full_name}+type:pr"
            )
            merges_url = (
                f"https://api.github.com/search/issues?q=repo:{full_name}+is:pr+is:merged"
            )

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
