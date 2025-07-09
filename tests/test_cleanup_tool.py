import asyncio
import tempfile
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

import os

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import pr_map
import pr_cleanup_tool
from config import settings


class TestCleanupTool(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.map_file = Path(self.tmpdir.name) / "map.json"
        patcher = patch.object(pr_map, "PR_MAP_FILE", self.map_file)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmpdir.cleanup)

    def test_remove_closed_pr_message(self):
        pr_map.save_pr_map({"test/repo#1": 111})
        with patch(
            "pr_cleanup_tool.fetch_pr_state",
            new_callable=AsyncMock,
            return_value="closed",
        ), patch(
            "discord_bot.discord_bot_instance.delete_message_from_channel",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_delete:
            asyncio.run(pr_cleanup_tool.cleanup_pr_messages())
            mock_delete.assert_awaited_with(settings.channel_pull_requests, 111)
        data = pr_map.load_pr_map()
        self.assertEqual(data, {})

    def test_keep_open_pr_message(self):
        pr_map.save_pr_map({"test/repo#2": 222})
        with patch(
            "pr_cleanup_tool.fetch_pr_state",
            new_callable=AsyncMock,
            return_value="open",
        ), patch(
            "discord_bot.discord_bot_instance.delete_message_from_channel",
            new_callable=AsyncMock,
        ) as mock_delete:
            asyncio.run(pr_cleanup_tool.cleanup_pr_messages())
            mock_delete.assert_not_called()
        data = pr_map.load_pr_map()
        self.assertEqual(data, {"test/repo#2": 222})


if __name__ == "__main__":
    unittest.main()
