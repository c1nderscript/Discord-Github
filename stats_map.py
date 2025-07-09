"""Mapping utilities for repository statistics embed messages."""

import json
from logging_config import get_state_file_path

STATS_MAP_FILE = get_state_file_path("repo_stats_map.json")


def load_stats_map() -> dict:
    """Load the repository stats message map."""
    try:
        with open(STATS_MAP_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_stats_map(data: dict) -> None:
    """Save the repository stats message map."""
    with open(STATS_MAP_FILE, "w") as f:
        json.dump(data, f, indent=2)
