import json
from pathlib import Path
from typing import Dict

PR_MAP_FILE = Path("pr_message_map.json")


def load_pr_map() -> Dict[str, int]:
    """Load the PR message map from disk."""
    if PR_MAP_FILE.exists():
        try:
            with PR_MAP_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_pr_map(data: Dict[str, int]) -> None:
    """Save the PR message map to disk."""
    with PR_MAP_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f)
