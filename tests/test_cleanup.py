import asyncio
import tempfile
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import pr_map
from config import settings
from pr_cleanup import cleanup_pr_messages


class TestPRCleanupJob(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.map_file = Path(self.tmpdir.name) / "map.json"
        patcher = patch.object(pr_map, "PR_MAP_FILE", self.map_file)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmpdir.cleanup)

    def test_cleanup_removes_closed_pr_messages(self):
        pr_map.save_pr_map({
            "test/repo#1": 111,
            "test/repo#2": 222,
        })

        # Mock GitHub API responses
        responses = {
            "https://api.github.com/repos/test/repo/pulls/1": {"state": "closed"},
            "https://api.github.com/repos/test/repo/pulls/2": {"state": "open"},
        }

        class MockResponse:
            def __init__(self, data):
                self.status = 200
                self._data = data

            async def json(self):
                return self._data

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

        class MockSession:
            def get(self, url, headers=None):
                return MockResponse(responses[url])

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

        with patch("pr_cleanup.aiohttp.ClientSession", return_value=MockSession()), \
             patch(
                 "discord_bot.discord_bot_instance.delete_message_from_channel",
                 new_callable=AsyncMock,
             ) as mock_delete:
            asyncio.run(cleanup_pr_messages())
            mock_delete.assert_awaited_once_with(settings.channel_pull_requests, 111)

        data = pr_map.load_pr_map()
        self.assertEqual(data, {"test/repo#2": 222})


if __name__ == "__main__":
    unittest.main()
