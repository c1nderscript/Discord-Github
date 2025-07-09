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


async def fetch_repo_stats() -> dict:
    """Fetch commit, pull request and merge counts for the user's repositories."""
    import aiohttp
    import logging

    logger = logging.getLogger(__name__)

    if not settings.github_username:
        logger.warning("GitHub username not configured; skipping stats fetch")
        return {}

    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"  # pragma: no cover - optional auth

    repos_url = f"https://api.github.com/users/{settings.github_username}/repos"

    stats: dict = {}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(repos_url, headers=headers) as resp:
                if resp.status != 200:
                    logger.error("Failed to fetch repositories: %s", resp.status)
                    return {}
                repos = await resp.json()
        except Exception as exc:  # pragma: no cover - network failures
            logger.error("Error fetching repositories: %s", exc)
            return {}

        for repo in repos:
            name = repo.get("full_name")
            if not name:
                continue
            stats[name] = {"commits": 0, "pull_requests": 0, "merges": 0}

            commits_url = f"https://api.github.com/repos/{name}/commits?per_page=1"
            pulls_url = f"https://api.github.com/repos/{name}/pulls?state=all&per_page=1"
            merges_url = f"https://api.github.com/repos/{name}/pulls?state=closed&per_page=1"

            try:
                async with session.get(commits_url, headers=headers) as c_resp:
                    if "link" in c_resp.headers:
                        link = c_resp.headers["link"]
                        if "last" in link:
                            last_part = link.split(",")[-1]
                            if "page=" in last_part:
                                stats[name]["commits"] = int(last_part.split("page=")[-1].split(" ")[0])
                async with session.get(pulls_url, headers=headers) as p_resp:
                    if "link" in p_resp.headers:
                        link = p_resp.headers["link"]
                        if "last" in link:
                            part = link.split(",")[-1]
                            if "page=" in part:
                                stats[name]["pull_requests"] = int(part.split("page=")[-1].split(" ")[0])
                async with session.get(merges_url, headers=headers) as m_resp:
                    if "link" in m_resp.headers:
                        link = m_resp.headers["link"]
                        if "last" in link:
                            part = link.split(",")[-1]
                            if "page=" in part:
                                stats[name]["merges"] = int(part.split("page=")[-1].split(" ")[0])
            except Exception:  # pragma: no cover - network failures
                logger.error("Error fetching stats for repo %s", name)

    return stats
