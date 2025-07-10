"""Permission helpers."""

from discord.ext import commands


def is_admin():
    """Check if command author has administrator permissions."""

    async def predicate(ctx: commands.Context) -> bool:
        return ctx.author.guild_permissions.administrator

    return commands.check(predicate)
