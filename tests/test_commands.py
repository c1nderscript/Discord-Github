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
        with patch.object(
            discord_bot.discord_bot_instance,
            "purge_old_messages",
            new_callable=AsyncMock,
        ) as mock_purge:
            asyncio.run(discord_bot.clear(self.ctx))

        mock_purge.assert_awaited_once_with(settings.channel_pull_requests, 0)
        self.ctx.send.assert_awaited_once()

    def test_update_command(self):
        sample_prs = [("repo/test", {
                "number": 1,
                "title": "Test PR",
                "html_url": "https://example.com/pr/1",
                "user": {"login": "tester"}
            })]
        embed = MagicMock()
        message = MagicMock()
        message.id = 99

        with patch(
            "github_api.fetch_open_pull_requests",
            new_callable=AsyncMock,
            return_value=sample_prs,
        ) as mock_fetch, patch(
            "formatters.format_pull_request_event",
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
            asyncio.run(discord_bot.update_pull_requests(self.ctx))

        mock_fetch.assert_awaited_once()
        mock_format.assert_called_once()
        mock_send.assert_awaited_once_with(settings.channel_pull_requests, embed=embed)
        mock_load.assert_called_once()
        mock_save.assert_called_once()
        self.ctx.send.assert_awaited()
class TestUpdateCommand(unittest.TestCase):
    def test_update_sends_embeds_for_prs(self):
        prs = [
            ("user/repo1", {"number": 1, "title": "PR1", "html_url": "http://x/1", "user": {"login": "a"}}),
            ("user/repo2", {"number": 2, "title": "PR2", "html_url": "http://x/2", "user": {"login": "b"}}),
        ]

        embed1 = MagicMock()
        embed2 = MagicMock()

        with patch(
            "github_api.fetch_open_pull_requests", new_callable=AsyncMock, return_value=prs
        ) as mock_fetch, patch(
            "formatters.format_pull_request_event", side_effect=[embed1, embed2]
        ) as mock_fmt, patch(
            "discord_bot.send_to_discord", new_callable=AsyncMock
        ) as mock_send, patch(
            "discord_bot.load_pr_map", return_value={}
        ), patch(
            "discord_bot.save_pr_map"
        ):
            ctx = MagicMock()
            ctx.send = AsyncMock()
            asyncio.run(discord_bot.update_pull_requests.callback(ctx))

        mock_fetch.assert_awaited_once()
        self.assertEqual(mock_fmt.call_count, 2)
        mock_send.assert_has_awaits(
            [
                call(settings.channel_pull_requests, embed=embed1),
                call(settings.channel_pull_requests, embed=embed2),
            ],
            any_order=False,
        )



if __name__ == "__main__":
    unittest.main()
