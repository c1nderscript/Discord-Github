import json
from logging_config import get_state_file_path
from typing import Dict

STATS_MAP_FILE = get_state_file_path("stats_message_map.json")


def load_stats_map() -> Dict[str, int]:
    """Load the stats message map from the state file."""
    try:
        with open(STATS_MAP_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def save_stats_map(stats_map: Dict[str, int]) -> None:
    """Save the stats message map to the state file."""
    with open(STATS_MAP_FILE, "w") as f:
        json.dump(stats_map, f, indent=2)
