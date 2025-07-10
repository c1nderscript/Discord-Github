import logging
from typing import Dict, List

import aiohttp

from config import settings

logger = logging.getLogger(__name__)
GITHUB_API_BASE = "https://api.github.com"


async def fetch_open_pull_requests() -> Dict[str, List[dict]]:
    """Fetch open pull requests grouped by repository."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"

    params = {"per_page": 100, "affiliation": "owner"}
    repos_url = f"{GITHUB_API_BASE}/user/repos"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(repos_url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    logger.error("Failed to fetch repositories: %s", resp.status)
                    return {}
                repositories = await resp.json()
        except Exception as exc:  # pragma: no cover - network failure
            logger.error("Error fetching repositories: %s", exc)
            return {}

        pr_map: Dict[str, List[dict]] = {}
        for repo in repositories:
            owner = repo.get("owner", {}).get("login") or settings.github_username
            name = repo.get("name")
            if not owner or not name:
                continue
            repo_full = f"{owner}/{name}"
            prs_url = f"{GITHUB_API_BASE}/repos/{owner}/{name}/pulls"
            try:
                async with session.get(prs_url, headers=headers, params={"state": "open"}) as pr_resp:
                    if pr_resp.status != 200:
                        logger.warning(
                            "Failed to fetch PRs for %s: %s", repo_full, pr_resp.status
                        )
                        continue
                    prs = await pr_resp.json()
                    if prs:
                        pr_map[repo_full] = prs
            except Exception as exc:  # pragma: no cover - network failure
                logger.error("Error fetching PRs for %s: %s", repo_full, exc)
        return pr_map
