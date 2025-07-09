"""Utility functions for managing the PR message map."""

import json
from logging_config import get_state_file_path

PR_MAP_FILE = get_state_file_path("pr_message_map.json")


def load_pr_map():
    """Load the PR message map from the state file."""
    try:
        with open(PR_MAP_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_pr_map(pr_map):
    """Save the PR message map to the state file."""
    with open(PR_MAP_FILE, 'w') as f:
        json.dump(pr_map, f, indent=2)
