"""GitHub webhook utilities for signature verification."""

import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Optional, List

import aiohttp
from fastapi import Request, HTTPException

from config import settings

logger = logging.getLogger(__name__)


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
    """Statistics for a single repository."""

    name: str
    commits: int
    pull_requests: int
    merges: int


async def gather_repo_stats() -> List[RepoStats]:
    """Gather commit, PR and merge counts for each repository."""
    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.github.com/user/repos",
            headers=headers,
            params={"per_page": 100, "affiliation": "owner"},
        ) as resp:
            if resp.status != 200:
                logger.error(f"Failed to fetch repositories: {resp.status}")
                return []
            repos = await resp.json()

        results: List[RepoStats] = []
        for repo in repos:
            full_name = repo.get("full_name")
            name = repo.get("name")

            # Commit count
            commits_url = f"https://api.github.com/repos/{full_name}/commits"
            async with session.get(commits_url, headers=headers, params={"per_page": 1}) as c_resp:
                if c_resp.status == 200:
                    link = c_resp.headers.get("Link")
                    if link and "page=" in link:
                        last = link.split(",")[-1]
                        commit_count = int(last.split("page=")[-1].split("&")[0])
                    else:
                        data = await c_resp.json()
                        commit_count = len(data)
                else:
                    commit_count = 0

            # PR count
            pr_url = "https://api.github.com/search/issues"
            async with session.get(
                pr_url,
                headers=headers,
                params={"q": f"repo:{full_name} is:pr", "per_page": 1},
            ) as pr_resp:
                if pr_resp.status == 200:
                    data = await pr_resp.json()
                    pr_count = data.get("total_count", 0)
                else:
                    pr_count = 0

            # Merge count
            async with session.get(
                pr_url,
                headers=headers,
                params={"q": f"repo:{full_name} is:pr is:merged", "per_page": 1},
            ) as merge_resp:
                if merge_resp.status == 200:
                    data = await merge_resp.json()
                    merge_count = data.get("total_count", 0)
                else:
                    merge_count = 0

            results.append(RepoStats(name, commit_count, pr_count, merge_count))

    return results
