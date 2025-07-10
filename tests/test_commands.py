import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import discord_bot
from config import settings


class TestBotCommands(unittest.TestCase):
    def setUp(self):
        self.ctx = MagicMock()
        self.ctx.send = AsyncMock()

    def test_clear_command(self):
        channels = [
            settings.channel_commits,
            settings.channel_pull_requests,
            settings.channel_releases,
            settings.channel_ci_builds,
            settings.channel_code_merges,
        ]
        with patch.object(
            discord_bot.discord_bot_instance,
            "purge_old_messages",
            new_callable=AsyncMock,
        ) as mock_purge:
            asyncio.run(discord_bot.clear(self.ctx))

        mock_purge.assert_has_awaits([call(ch, 0) for ch in channels], any_order=True)
        self.ctx.send.assert_awaited_once()

    def test_update_command(self):
        sample_prs = [
            {
                "number": 1,
                "title": "Test PR",
                "html_url": "https://example.com/pr/1",
                "user": {"login": "tester"},
                "repository_full_name": "repo/test",
            }
        ]
        embed = MagicMock()
        message = MagicMock()
        message.id = 99

        with patch(
            "discord_bot.fetch_open_pull_requests",
            new_callable=AsyncMock,
            return_value=sample_prs,
        ) as mock_fetch, patch(
            "discord_bot.format_pull_request_event",
            return_value=embed,
        ) as mock_format, patch(
            "discord_bot.send_to_discord",
            new_callable=AsyncMock,
            return_value=message,
        ) as mock_send, patch(
            "discord_bot.load_pr_map",
            return_value={},
        ) as mock_load, patch(
            "discord_bot.save_pr_map"
        ) as mock_save:
            asyncio.run(discord_bot.update(self.ctx))

        mock_fetch.assert_awaited_once()
        mock_format.assert_called_once()
        mock_send.assert_awaited_once_with(settings.channel_pull_requests, embed=embed)
        mock_load.assert_called_once()
        mock_save.assert_called_once()
        self.ctx.send.assert_awaited()


if __name__ == "__main__":
    unittest.main()
