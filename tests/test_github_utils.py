import asyncio
import os
import sys
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")
os.environ.setdefault("GITHUB_USERNAME", "alice")

import github_utils
from config import settings


class MockResp:
    def __init__(self, status: int, data=None, headers=None):
        self.status = status
        self._data = data or {}
        self.headers = headers or {}

    async def json(self):
        return self._data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


class MockSession:
    def __init__(self, responses):
        self._responses = responses

    def get(self, url, headers=None, params=None):
        return self._responses.pop(0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


class TestFetchRepoStats(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(settings, "github_username", "alice")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_fetch_repo_stats_success(self):
        responses = [
            MockResp(200, [{"full_name": "alice/repo1"}, {"full_name": "alice/repo2"}]),
            MockResp(200, {"total_count": 5}),
            MockResp(200, {"total_count": 3}),
            MockResp(200, {"total_count": 2}),
            MockResp(200, {"total_count": 10}),
            MockResp(200, {"total_count": 7}),
            MockResp(200, {"total_count": 4}),
        ]
        mock_session = MockSession(responses)
        with mock.patch("github_utils.aiohttp.ClientSession", return_value=mock_session):
            stats, totals = asyncio.run(github_utils.fetch_repo_stats())

        expected = [
            {
                "name": "alice/repo1",
                "commits": 5,
                "pull_requests": 3,
                "merged_pull_requests": 2,
            },
            {
                "name": "alice/repo2",
                "commits": 10,
                "pull_requests": 7,
                "merged_pull_requests": 4,
            },
        ]
        self.assertEqual(stats, expected)
        self.assertEqual(totals, {"commits": 15, "pull_requests": 10, "merged_pull_requests": 6})

    def test_fetch_repo_stats_missing_data(self):
        responses = [
            MockResp(200, [{"full_name": "alice/repo1"}]),
            MockResp(404),
            MockResp(200, {"total_count": 0}),
            MockResp(200, {"total_count": 0}),
        ]
        mock_session = MockSession(responses)
        with mock.patch("github_utils.aiohttp.ClientSession", return_value=mock_session):
            stats, totals = asyncio.run(github_utils.fetch_repo_stats())

        self.assertEqual(
            stats,
            [
                {
                    "name": "alice/repo1",
                    "commits": 0,
                    "pull_requests": 0,
                    "merged_pull_requests": 0,
                }
            ],
        )
        self.assertEqual(totals, {"commits": 0, "pull_requests": 0, "merged_pull_requests": 0})


if __name__ == "__main__":
    unittest.main()
