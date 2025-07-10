import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import patch
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")
os.environ.setdefault("AGENTS_DIR", "/tmp/agents")

import github_utils
from config import settings


class TestFetchRepoStats(unittest.TestCase):
    def setUp(self):
        patcher1 = patch.object(settings, "github_username", "testuser")
        patcher1.start()
        self.addCleanup(patcher1.stop)
        patcher2 = patch.object(settings, "github_token", "token")
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
                            {"full_name": "testuser/repo1"},
                            {"full_name": "testuser/repo2"},
                        ])
                    return MockResponse([])
                if url.endswith("/search/commits"):
                    repo = params["q"].split("repo:")[1]
                    count = {"testuser/repo1": 10, "testuser/repo2": 5}[repo]
                    return MockResponse({"total_count": count})
                if url.endswith("/search/issues"):
                    repo = params["q"].split("repo:")[1].split("+")[0]
                    if "is:merged" in params["q"]:
                        count = {"testuser/repo1": 7, "testuser/repo2": 2}[repo]
                    else:
                        count = {"testuser/repo1": 12, "testuser/repo2": 3}[repo]
                    return MockResponse({"total_count": count})
                return MockResponse({}, status=404)

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

        return MockSession()

    def test_fetch_repo_stats(self):
        mock_session = self._mock_session()
        with patch("github_utils.aiohttp.ClientSession", return_value=mock_session):
            repo_stats, totals = asyncio.run(github_utils.fetch_repo_stats())
        self.assertEqual(totals["commits"], 15)
        self.assertEqual(totals["pull_requests"], 15)
        self.assertEqual(totals["merged_pull_requests"], 9)
        self.assertEqual(len(repo_stats), 2)
        repo1 = next(r for r in repo_stats if r["name"] == "testuser/repo1")
        self.assertEqual(repo1["commits"], 10)
        self.assertEqual(repo1["pull_requests"], 12)
        self.assertEqual(repo1["merged_pull_requests"], 7)


if __name__ == "__main__":
    unittest.main()
