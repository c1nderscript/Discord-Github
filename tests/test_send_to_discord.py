import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch
import unittest
import discord

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import discord_bot


class TestSendToDiscord(unittest.TestCase):
    def _make_embed(self, count: int) -> discord.Embed:
        embed = discord.Embed(title="Test")
        for i in range(count):
            embed.add_field(name=f"Field{i}", value=str(i))
        return embed

    def test_split_to_channel(self):
        embed = self._make_embed(27)
        with patch.object(
            discord_bot.discord_bot_instance,
            "send_to_channel",
            new_callable=AsyncMock,
        ) as mock_channel:
            asyncio.run(discord_bot.send_to_discord(123, embed=embed))
            self.assertEqual(mock_channel.await_count, 2)
            for call_args in mock_channel.await_args_list:
                sent_embed = call_args.args[2]
                self.assertLessEqual(len(sent_embed.fields), 25)

    def test_split_to_webhook(self):
        embed = self._make_embed(30)
        with patch.object(discord_bot.settings, "discord_webhook_url", "http://example.com"), patch.object(
            discord_bot.discord_bot_instance,
            "send_to_webhook",
            new_callable=AsyncMock,
        ) as mock_hook:
            asyncio.run(discord_bot.send_to_discord(123, embed=embed, use_webhook=True))
            self.assertEqual(mock_hook.await_count, 2)
            for call_args in mock_hook.await_args_list:
                sent_embed = call_args.args[2]
                self.assertLessEqual(len(sent_embed.fields), 25)


if __name__ == "__main__":
    unittest.main()
