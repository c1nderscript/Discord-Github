import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import stats_map
import main
from config import settings


class TestGithubStats(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.map_file = Path(self.tmpdir.name) / "stats.json"
        patcher = patch.object(stats_map, "STATS_MAP_FILE", self.map_file)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmpdir.cleanup)

    def test_update_github_stats(self):
        sample_stats = [
            main.RepoStats(name="repo1", commit_count=5, pr_count=2, merge_count=1),
            main.RepoStats(name="repo2", commit_count=3, pr_count=1, merge_count=0),
        ]

        message = MagicMock()
        message.id = 42

        with patch("main.gather_repo_stats", new_callable=AsyncMock, return_value=sample_stats), \
             patch("discord_bot.discord_bot_instance.update_channel_name", new_callable=AsyncMock) as mock_rename, \
             patch("main.send_to_discord", new_callable=AsyncMock, return_value=message) as mock_send:
            asyncio.run(main.update_github_stats())

        mock_rename.assert_has_awaits([
            call(settings.channel_commits, "8-commits"),
            call(settings.channel_pull_requests, "3-pull-requests"),
            call(settings.channel_code_merges, "1-merges"),
        ], any_order=True)
        self.assertEqual(mock_send.await_count, 3)
        data = stats_map.load_stats_map()
        self.assertEqual(data, {
            "commits": 42,
            "pull_requests": 42,
            "merges": 42,
        })


if __name__ == "__main__":
    unittest.main()
