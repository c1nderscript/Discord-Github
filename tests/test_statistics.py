import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, call
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")
os.environ.setdefault("GITHUB_TOKEN", "token")

import main
from config import settings
from discord_bot import discord_bot_instance
from github_utils import RepoStats


class TestUpdateStatistics(unittest.TestCase):
    def test_update_statistics(self):
        repo_stats = [
            RepoStats("repo1", 5, 2, 1),
            RepoStats("repo2", 3, 1, 1),
        ]
        with patch(
            "main.gather_repo_stats", new_callable=AsyncMock, return_value=repo_stats
        ), patch.object(
            discord_bot_instance,
            "update_channel_name",
            new_callable=AsyncMock,
        ) as mock_update, patch(
            "main.send_to_discord", new_callable=AsyncMock
        ) as mock_send:
            asyncio.run(main.update_statistics())

        mock_update.assert_has_awaits(
            [
                call(settings.channel_commits, "8-commits"),
                call(settings.channel_pull_requests, "3-pull-requests"),
                call(settings.channel_code_merges, "2-merges"),
            ],
            any_order=True,
        )
        self.assertEqual(mock_send.await_count, 6)
        embed = mock_send.await_args_list[0].kwargs["embed"]
        self.assertEqual(embed.title, "repo1")


if __name__ == "__main__":
    unittest.main()
