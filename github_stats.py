import json
import logging
from typing import Dict

from logging_config import get_state_file_path

logger = logging.getLogger(__name__)

REPO_STATS_FILE = get_state_file_path("repositories.json")


async def fetch_repo_stats() -> Dict[str, Dict[str, int]]:
    """Fetch repository statistics from the local state file."""
    try:
        with open(REPO_STATS_FILE, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.error("repositories.json has invalid format")
            return {}
        return data
    except FileNotFoundError:
        logger.error("repositories.json file not found")
        return {}
    except Exception as exc:
        logger.error(f"Failed to load repository stats: {exc}")
        return {}
