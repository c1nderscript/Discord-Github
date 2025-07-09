import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import os

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import pr_map
import cleanup
from config import settings


class TestCleanupScript(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.pr_file = Path(self.tmpdir.name) / "map.json"
        patcher = patch.object(pr_map, "PR_MAP_FILE", self.pr_file)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmpdir.cleanup)

    def create_session(self, state):
        session_mock = MagicMock()

        class MockResp:
            status = 200

            async def json(self):
                return {"state": state}

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

        session_mock.get.return_value = MockResp()

        class MockSession:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return session_mock

            async def __aexit__(self, exc_type, exc, tb):
                pass

        return MockSession

    def test_cleanup_closed_pr(self):
        pr_map.save_pr_map({"test/repo#1": 111})
        mock_session = self.create_session("closed")
        with patch("cleanup.aiohttp.ClientSession", return_value=mock_session()), \
             patch(
                 "discord_bot.discord_bot_instance.delete_message_from_channel",
                 new_callable=AsyncMock,
                 return_value=True,
             ):
            asyncio.run(cleanup.cleanup_pr_messages())
        data = pr_map.load_pr_map()
        self.assertEqual(data, {})

    def test_cleanup_open_pr(self):
        pr_map.save_pr_map({"test/repo#1": 111})
        mock_session = self.create_session("open")
        with patch("cleanup.aiohttp.ClientSession", return_value=mock_session()), \
             patch(
                 "discord_bot.discord_bot_instance.delete_message_from_channel",
                 new_callable=AsyncMock,
                 return_value=True,
             ) as mock_delete:
            asyncio.run(cleanup.cleanup_pr_messages())
            mock_delete.assert_not_called()
        data = pr_map.load_pr_map()
        self.assertEqual(data, {"test/repo#1": 111})


if __name__ == "__main__":
    unittest.main()
