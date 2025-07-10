import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import pr_map
import main
from config import settings


class TestPRMessageCleanup(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.pr_file = Path(self.tmpdir.name) / "map.json"
        patcher = patch.object(pr_map, "PR_MAP_FILE", self.pr_file)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmpdir.cleanup)

    def test_store_message_id_on_open(self):
        message = MagicMock()
        message.id = 123
        payload = {
            "action": "opened",
            "pull_request": {"number": 1, "title": "Add", "html_url": "x", "user": {"login": "a"}},
            "repository": {"full_name": "test/repo"},
        }
        with patch("main.send_to_discord", new_callable=AsyncMock, return_value=message), \
             patch("main.update_github_stats", new_callable=AsyncMock):
            asyncio.run(main.route_github_event("pull_request", payload))
        data = pr_map.load_pr_map()
        self.assertEqual(data.get("test/repo#1"), message.id)

    def test_delete_message_on_close(self):
        pr_map.save_pr_map({"test/repo#1": 456})
        payload = {
            "action": "closed",
            "pull_request": {"number": 1, "merged": True},
            "repository": {"full_name": "test/repo"},
        }
        with patch("main.update_github_stats", new_callable=AsyncMock), \
             patch("discord_bot.discord_bot_instance.delete_message_from_channel", new_callable=AsyncMock) as mock_del, \
             patch("main.send_to_discord", new_callable=AsyncMock):
            asyncio.run(main.route_github_event("pull_request", payload))
            mock_del.assert_awaited_with(settings.channel_pull_requests, 456)
        self.assertEqual(pr_map.load_pr_map(), {})


if __name__ == "__main__":
    unittest.main()
