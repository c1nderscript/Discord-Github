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

    def _mock_session_sequence(self, responses):
        class MockResp:
            def __init__(self, status, data):
                self.status = status
                self._data = data

            async def json(self):
                return self._data

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

        class MockSession:
            def __init__(self, *args, **kwargs):
                self._responses = responses

            def get(self, url, headers=None):
                status, data = self._responses.pop(0)
                return MockResp(status, data)

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

        return MockSession

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
        with patch("cleanup.aiohttp.ClientSession", return_value=mock_session()), \
             patch(
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
        with patch("cleanup.aiohttp.ClientSession", return_value=mock_session()), \
             patch(
                 "discord_bot.discord_bot_instance.delete_message_from_channel",
                 new_callable=AsyncMock,
                 return_value=True,
             ) as mock_delete:
            asyncio.run(cleanup.cleanup_pr_messages())
            mock_delete.assert_not_called()
        self.assertEqual(pr_map.load_pr_map(), {"test/repo#1": 111})

    def test_api_error_logs_warning_and_continues(self):
        pr_map.save_pr_map({"repo#1": 101, "repo#2": 202})
        responses = [
            (500, {}),
            (200, {"state": "closed"}),
        ]
        mock_session = self._mock_session_sequence(responses)
        with patch("cleanup.aiohttp.ClientSession", return_value=mock_session()), \
             patch(
                 "discord_bot.discord_bot_instance.delete_message_from_channel",
                 new_callable=AsyncMock,
                 return_value=True,
             ) as mock_delete, self.assertLogs(cleanup.logger, level="WARNING") as cm:
            asyncio.run(cleanup.cleanup_pr_messages())
            mock_delete.assert_awaited_once_with(settings.channel_pull_requests, 202)

        data = pr_map.load_pr_map()
        self.assertEqual(data, {"repo#1": 101})
        self.assertIn("Failed to fetch PR repo#1", "\n".join(cm.output))

    def test_missing_state_logs_warning_and_continues(self):
        pr_map.save_pr_map({"repo#1": 101, "repo#2": 202})
        responses = [
            (200, {}),
            (200, {"state": "closed"}),
        ]
        mock_session = self._mock_session_sequence(responses)
        with patch("cleanup.aiohttp.ClientSession", return_value=mock_session()), \
             patch(
                 "discord_bot.discord_bot_instance.delete_message_from_channel",
                 new_callable=AsyncMock,
                 return_value=True,
             ) as mock_delete, self.assertLogs(cleanup.logger, level="WARNING") as cm:
            asyncio.run(cleanup.cleanup_pr_messages())
            mock_delete.assert_awaited_once_with(settings.channel_pull_requests, 202)

        data = pr_map.load_pr_map()
        self.assertEqual(data, {"repo#1": 101})
        self.assertIn("Missing 'state' in PR response for repo#1", "\n".join(cm.output))


if __name__ == "__main__":
    unittest.main()
