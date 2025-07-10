import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, call, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import discord_bot
from config import settings


class TestUpdateCommand(unittest.TestCase):
    def test_update_sends_embeds_for_prs(self):
        prs = {
            "user/repo1": [
                {"number": 1, "title": "PR1", "html_url": "http://x/1", "user": {"login": "a"}}
            ],
            "user/repo2": [
                {"number": 2, "title": "PR2", "html_url": "http://x/2", "user": {"login": "b"}}
            ],
        }

        embed1 = MagicMock()
        embed2 = MagicMock()

        with patch(
            "discord_bot.fetch_open_pull_requests", new_callable=AsyncMock, return_value=prs
        ) as mock_fetch, patch(
            "discord_bot.format_pull_request_event", side_effect=[embed1, embed2]
        ) as mock_fmt, patch(
            "discord_bot.send_to_discord", new_callable=AsyncMock
        ) as mock_send:
            ctx = MagicMock()
            asyncio.run(discord_bot.update.callback(ctx))

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
