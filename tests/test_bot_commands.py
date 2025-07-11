import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import pr_map
from discord_bot import clear_channels, update_pull_requests, discord_bot_instance
from config import settings


class TestBotCommands(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(__file__).resolve().parent / "tmp"
        self.tmpdir.mkdir(exist_ok=True)
        self.map_file = self.tmpdir / "map.json"
        patcher = patch.object(pr_map, "PR_MAP_FILE", self.map_file)
        patcher.start()
        self.addCleanup(patcher.stop)
        if self.map_file.exists():
            self.map_file.unlink()

    def tearDown(self):
        for item in self.tmpdir.iterdir():
            item.unlink()

    def test_clear_channels(self):
        ctx = MagicMock()
        ctx.send = AsyncMock()
        with patch.object(
            discord_bot_instance, "purge_old_messages", new_callable=AsyncMock
        ) as mock_purge:
            asyncio.run(clear_channels(ctx))
            mock_purge.assert_awaited_once_with(settings.channel_pull_requests, 0)
        ctx.send.assert_called_once()

    def test_update_pull_requests(self):
        ctx = MagicMock()
        ctx.send = AsyncMock()
        message = MagicMock()
        message.id = 123
        sample_pr = {"number": 1, "title": "Test", "html_url": "url", "user": {"login": "bob"}}
        with patch("github_api.fetch_open_pull_requests", new_callable=AsyncMock, return_value=[("repo/test", sample_pr)]), \
             patch("discord_bot.send_to_discord", new_callable=AsyncMock, return_value=message) as mock_send:
            asyncio.run(update_pull_requests(ctx))
            mock_send.assert_awaited_once()
        data = pr_map.load_pr_map()
        self.assertIn("repo/test#1", data)
        ctx.send.assert_called()


if __name__ == "__main__":
    unittest.main()
