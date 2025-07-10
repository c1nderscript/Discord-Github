"""Discord setup command for dynamic channel creation."""

from __future__ import annotations

import discord
from discord.ext import commands

from utils.channel_manager import ensure_channels
from utils.permissions import is_admin
from utils.config import CHANNEL_IDS_FILE


@commands.command(name="setup")
@is_admin()
async def setup_channels(ctx: commands.Context) -> None:
    """Create required categories and channels dynamically."""
    await ctx.send("Setting up channels...")
    guild = ctx.guild
    if not guild:
        await ctx.send("❌ Setup must be run in a guild context.")
        return

    try:
        ids = await ensure_channels(guild)
    except discord.Forbidden:
        await ctx.send("❌ Missing permissions to create channels.")
        return

    lines = [f"{cat} -> {name}: {cid}" for cat, chs in ids.items() for name, cid in chs.items()]
    summary = "\n".join(lines)
    await ctx.send(f"✅ Setup complete.\n```\n{summary}\n```")


__all__ = ["setup_channels"]
