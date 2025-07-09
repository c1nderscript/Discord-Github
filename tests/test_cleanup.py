import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
import unittest

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import pr_map
import cleanup
from config import settings


class TestCleanupScript(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.map_file = Path(self.tmpdir.name) / "map.json"
        patcher = patch.object(pr_map, "PR_MAP_FILE", self.map_file)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmpdir.cleanup)
        # Ensure the Discord bot is marked as ready
        from discord_bot import discord_bot_instance

        discord_bot_instance.ready = True

    def _mock_session(self, state: str):
        class MockResp:
            status = 200

            async def json(self):
                return {"state": state}

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

        class MockSession:
            def __init__(self, *args, **kwargs):
                pass

            def get(self, url, headers=None):
                return MockResp()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

        return MockSession

    def test_cleanup_closed_pr(self):
        pr_map.save_pr_map({"test/repo#1": 111})
        mock_session = self._mock_session("closed")
        with patch("cleanup.aiohttp.ClientSession", return_value=mock_session()), patch(
            "discord_bot.discord_bot_instance.delete_message_from_channel",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_delete:
            asyncio.run(cleanup.cleanup_pr_messages())
            mock_delete.assert_awaited_once_with(settings.channel_pull_requests, 111)
        self.assertEqual(pr_map.load_pr_map(), {})

    def test_cleanup_open_pr(self):
        pr_map.save_pr_map({"test/repo#1": 111})
        mock_session = self._mock_session("open")
        with patch("cleanup.aiohttp.ClientSession", return_value=mock_session()), patch(
            "discord_bot.discord_bot_instance.delete_message_from_channel",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_delete:
            asyncio.run(cleanup.cleanup_pr_messages())
            mock_delete.assert_not_called()
        self.assertEqual(pr_map.load_pr_map(), {"test/repo#1": 111})


if __name__ == "__main__":
    unittest.main()
