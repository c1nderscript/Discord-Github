"""Utilities for creating and managing Discord channels."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import discord

from config import settings

CONFIG_DIR = Path("config")
CHANNELS_FILE = CONFIG_DIR / "channels.json"
CHANNEL_IDS_FILE = CONFIG_DIR / "channel_ids.json"


def load_channel_definitions() -> Dict[str, List[str]]:
    """Return channel structure from channels.json."""
    with CHANNELS_FILE.open() as f:
        data = json.load(f)
    return data.get("categories", {})


def load_channel_ids() -> Dict[str, Dict[str, int]]:
    """Load saved channel IDs if available."""
    if CHANNEL_IDS_FILE.exists():
        with CHANNEL_IDS_FILE.open() as f:
            return json.load(f)
    return {}


def save_channel_ids(ids: Dict[str, Dict[str, int]]) -> None:
    """Persist channel ID mapping to file."""
    with CHANNEL_IDS_FILE.open("w") as f:
        json.dump(ids, f, indent=2)


async def ensure_channels(guild: discord.Guild) -> Dict[str, Dict[str, int]]:
    """Ensure all configured categories and channels exist."""
    definitions = load_channel_definitions()
    existing_ids = load_channel_ids()
    for category_name, channels in definitions.items():
        # Find or create category
        category = discord.utils.get(guild.categories, name=category_name)
        if category is None:
            category = await guild.create_category(category_name)
        cat_map = existing_ids.setdefault(category_name, {})
        for ch_name in channels:
            channel = discord.utils.get(category.channels, name=ch_name)
            if channel is None:
                channel = await guild.create_text_channel(ch_name, category=category)
            cat_map[ch_name] = channel.id
    save_channel_ids(existing_ids)
    return existing_ids
