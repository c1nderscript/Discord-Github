import json
from logging_config import get_state_file_path
from typing import Dict, List

STATS_MAP_FILE = get_state_file_path("stats_message_map.json")


def load_stats_map() -> Dict[str, List[int]]:
    """Load the stats message map from the state file."""
    try:
        with open(STATS_MAP_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {k: list(v) if isinstance(v, list) else [] for k, v in data.items()}
            return {}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def save_stats_map(stats_map: Dict[str, List[int]]) -> None:
    """Save the stats message map to the state file."""
    with open(STATS_MAP_FILE, "w") as f:
        json.dump(stats_map, f, indent=2)
