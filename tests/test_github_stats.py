import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import unittest
import discord

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import main
from config import settings
from discord_bot import discord_bot_instance


class TestGithubStats(unittest.TestCase):
    def test_update_stats_renames_and_posts(self):
        sample_stats = {
            "repo1": {"commits": 5, "pull_requests": 2, "merges": 1},
            "repo2": {"commits": 3, "pull_requests": 1, "merges": 1},
        }

        msg = MagicMock()
        msg.id = 123

        with patch("main.fetch_repo_stats", new_callable=AsyncMock, return_value=sample_stats) as fetch, \
             patch.object(discord_bot_instance, "update_channel_name", new_callable=AsyncMock) as rename, \
             patch("main.send_to_discord", new_callable=AsyncMock, return_value=msg) as send:
            asyncio.run(main.update_github_stats())

        fetch.assert_awaited_once()
        rename.assert_has_awaits(
            [
                unittest.mock.call(settings.channel_commits, "8-commits"),
                unittest.mock.call(settings.channel_pull_requests, "3-pull-requests"),
                unittest.mock.call(settings.channel_code_merges, "2-merges"),
            ],
            any_order=False,
        )
        self.assertEqual(send.await_count, 3)
        for call_args in send.await_args_list:
            self.assertIn("embed", call_args.kwargs)
            self.assertIsInstance(call_args.kwargs["embed"], discord.Embed)


if __name__ == "__main__":
    unittest.main()
