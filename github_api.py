import logging
from typing import Dict, List, Tuple
import aiohttp

from config import settings
from github_stats import fetch_repo_stats

logger = logging.getLogger(__name__)
GITHUB_API_BASE = "https://api.github.com"


async def fetch_open_pull_requests() -> List[Tuple[str, Dict]]:
    """Fetch open pull requests for all repositories in ``repositories.json``."""
    stats = await fetch_repo_stats()
    repos = stats.keys()

    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"

    pulls: List[Tuple[str, Dict]] = []
    async with aiohttp.ClientSession() as session:
        for repo in repos:
            url = f"{GITHUB_API_BASE}/repos/{repo}/pulls"
            try:
                async with session.get(url, headers=headers, params={"state": "open"}) as resp:
                    if resp.status != 200:
                        logger.warning("Failed to fetch PRs for %s: %s", repo, resp.status)
                        continue
                    data = await resp.json()
                    for pr in data:
                        pulls.append((repo, pr))
            except Exception as exc:
                logger.error("Error fetching PRs for %s: %s", repo, exc)
    return pulls
