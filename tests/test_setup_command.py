import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

from commands.setup import setup_channels


class TestSetupCommand(unittest.TestCase):
    def test_setup_creates_channels(self):
        ctx = MagicMock()
        ctx.send = AsyncMock()
        guild = MagicMock()
        ctx.guild = guild
        with patch("commands.setup.ensure_channels", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = {"Bot Operations": {"bot-logs": 1}}
            update_cmd = MagicMock()
            update_cmd.callback = AsyncMock()
            ctx.bot = MagicMock()
            ctx.bot.get_command.return_value = update_cmd
            asyncio.run(setup_channels(ctx))
            mock_ensure.assert_awaited_once_with(guild)
            update_cmd.callback.assert_awaited_once_with(ctx)
        ctx.send.assert_awaited()


if __name__ == "__main__":
    unittest.main()
