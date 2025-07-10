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
import pull_request_handler
from config import settings


class TestPullRequestHandler(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.map_file = Path(self.tmpdir.name) / "map.json"
        patcher = patch.object(pr_map, "PR_MAP_FILE", self.map_file)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmpdir.cleanup)

    def test_open_pr_stores_message(self):
        message = MagicMock()
        message.id = 321
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 1,
                "title": "Add feature",
                "html_url": "http://example.com/pr/1",
                "user": {"login": "alice"},
            },
            "repository": {"full_name": "test/repo"},
        }
        with patch(
            "pull_request_handler.send_to_discord",
            new_callable=AsyncMock,
            return_value=message,
        ):
            result = asyncio.run(
                pull_request_handler.handle_pull_request_event_with_retry(payload, retries=1)
            )
        self.assertTrue(result)
        data = pr_map.load_pr_map()
        self.assertEqual(data.get("test/repo#1"), 321)

    def test_retry_success(self):
        async def side_effect(_):
            if not hasattr(side_effect, "called"):
                side_effect.called = True
                raise RuntimeError("boom")
            return None

        with patch(
            "pull_request_handler._process_pull_request_event",
            side_effect=side_effect,
        ) as proc, patch("asyncio.sleep", new_callable=AsyncMock) as sleep:
            result = asyncio.run(
                pull_request_handler.handle_pull_request_event_with_retry({}, retries=2, delay=0)
            )
        self.assertTrue(result)
        self.assertEqual(proc.call_count, 2)
        sleep.assert_awaited_once()

    def test_retry_failure(self):
        async def fail(_):
            raise RuntimeError("fail")

        with patch(
            "pull_request_handler._process_pull_request_event", side_effect=fail
        ) as proc, patch("asyncio.sleep", new_callable=AsyncMock) as sleep:
            result = asyncio.run(
                pull_request_handler.handle_pull_request_event_with_retry({}, retries=2, delay=0)
            )
        self.assertFalse(result)
        self.assertEqual(proc.call_count, 2)
        self.assertEqual(sleep.await_count, 1)


if __name__ == "__main__":
    unittest.main()
