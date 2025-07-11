import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import main
from config import settings
from discord_bot import discord_bot_instance


class TestPullRequestCountUpdate(unittest.TestCase):
    def test_update_pull_request_count(self):
        pr_map = {"repo1": [{}, {}], "repo2": [{}]}
        with patch(
            "github_prs.fetch_open_pull_requests",
            new_callable=AsyncMock,
            return_value=pr_map,
        ) as mock_fetch, patch(
            "discord_bot.discord_bot_instance.update_channel_name",
            new_callable=AsyncMock,
        ) as mock_rename:
            discord_bot_instance.ready = True
            asyncio.run(main.update_pull_request_count())

        mock_fetch.assert_awaited_once()
        mock_rename.assert_awaited_once_with(
            settings.channel_pull_requests, "3-pull-requests"
        )


if __name__ == "__main__":
    unittest.main()
