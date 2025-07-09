"""GitHub webhook utilities for signature verification."""

import hashlib
import hmac
from fastapi import Request, HTTPException
from typing import Optional

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

import aiohttp

GITHUB_API_BASE = "https://api.github.com"


async def _extract_total_from_link(link_header: Optional[str]) -> int:
    """Extract the last page number from a GitHub pagination link header."""
    if not link_header or "rel=\"last\"" not in link_header:
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


async def fetch_repo_stats() -> tuple[dict[str, dict[str, int]], dict[str, int]]:
    """Fetch commit and pull request stats for all repos owned by the user."""
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

        stats: dict[str, dict[str, int]] = {}
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

            pulls_url = (
                f"{GITHUB_API_BASE}/repos/{full_name}/pulls?state=all&per_page=1"
            )
            async with session.get(pulls_url, headers=headers) as r:
                pr_count = 0
                if r.status == 200:
                    await r.json()
                    pr_count = await _extract_total_from_link(r.headers.get("Link"))

            search_url = (
                f"{GITHUB_API_BASE}/search/issues?q=repo:{full_name}+is:pr+is:merged&per_page=1"
            )
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
