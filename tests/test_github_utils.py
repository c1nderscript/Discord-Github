import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")
os.environ.setdefault("GITHUB_USERNAME", "alice")
os.environ.setdefault("GITHUB_TOKEN", "token")

import github_utils
from config import settings


class TestFetchRepoStats(unittest.TestCase):
    def setUp(self) -> None:
        patcher1 = mock.patch.object(settings, "github_username", "alice")
        patcher1.start()
        self.addCleanup(patcher1.stop)
        patcher2 = mock.patch.object(settings, "github_token", "token")
        patcher2.start()
        self.addCleanup(patcher2.stop)

    def _mock_session(self):
        class MockResponse:
            def __init__(self, data, status=200):
                self.data = data
                self.status = status

            async def json(self):
                return self.data

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

        class MockSession:
            def get(self, url, headers=None, params=None):
                if url.endswith("/user/repos"):
                    page = int(params.get("page", 1)) if params else 1
                    if page == 1:
                        return MockResponse([
                            {"full_name": "alice/repo1"},
                            {"full_name": "alice/repo2"},
                        ])
                    return MockResponse([])
                if url.endswith("/search/commits"):
                    repo = params["q"].split("repo:")[1]
                    count = {"alice/repo1": 5, "alice/repo2": 10}[repo]
                    return MockResponse({"total_count": count})
                if url.endswith("/search/issues"):
                    repo = params["q"].split("repo:")[1].split("+")[0]
                    if "is:merged" in params["q"]:
                        count = {"alice/repo1": 2, "alice/repo2": 4}[repo]
                    else:
                        count = {"alice/repo1": 3, "alice/repo2": 7}[repo]
                    return MockResponse({"total_count": count})
                return MockResponse({}, status=404)

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

        return MockSession()

    def _mock_session_missing(self):
        class MockResponse:
            def __init__(self, data, status=200):
                self.data = data
                self.status = status

            async def json(self):
                return self.data

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

        class MockSession:
            def get(self, url, headers=None, params=None):
                if url.endswith("/user/repos"):
                    page = int(params.get("page", 1)) if params else 1
                    if page == 1:
                        return MockResponse([{"full_name": "alice/repo1"}])
                    return MockResponse([])
                if url.endswith("/search/commits"):
                    return MockResponse({"total_count": 0})
                if url.endswith("/search/issues"):
                    if "is:merged" in params["q"]:
                        return MockResponse({"total_count": 0})
                    return MockResponse({"total_count": 1})
                return MockResponse({}, status=404)

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

        return MockSession()

    def test_fetch_repo_stats_success(self):
        mock_session = self._mock_session()
        with mock.patch("github_utils.aiohttp.ClientSession", return_value=mock_session):
            stats, totals = asyncio.run(github_utils.fetch_repo_stats())

        expected_stats = [
            {"name": "alice/repo1", "commits": 5, "pull_requests": 3, "merged_pull_requests": 2},
            {"name": "alice/repo2", "commits": 10, "pull_requests": 7, "merged_pull_requests": 4},
        ]
        expected_totals = {"commits": 15, "pull_requests": 10, "merged_pull_requests": 6}

        self.assertEqual(stats, expected_stats)
        self.assertEqual(totals, expected_totals)

    def test_fetch_repo_stats_missing_data(self):
        mock_session = self._mock_session_missing()
        with mock.patch("github_utils.aiohttp.ClientSession", return_value=mock_session):
            stats, totals = asyncio.run(github_utils.fetch_repo_stats())

        expected_stats = [
            {"name": "alice/repo1", "commits": 0, "pull_requests": 1, "merged_pull_requests": 0}
        ]
        expected_totals = {"commits": 0, "pull_requests": 1, "merged_pull_requests": 0}

        self.assertEqual(stats, expected_stats)
        self.assertEqual(totals, expected_totals)


if __name__ == "__main__":
    unittest.main()

