import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import discord
import discord_bot
from config import settings


class TestSendToDiscord(unittest.TestCase):
    def test_split_fields_channel(self):
        embed = discord.Embed(title="Test")
        for i in range(30):
            embed.add_field(name=f"f{i}", value=str(i))

        with patch.object(discord_bot.discord_bot_instance, "send_to_channel", new_callable=AsyncMock) as mock_send:
            asyncio.run(discord_bot.send_to_discord(123, embed=embed))

        self.assertEqual(mock_send.await_count, 2)
        first_embed = mock_send.await_args_list[0][0][2]
        second_embed = mock_send.await_args_list[1][0][2]
        self.assertEqual(len(first_embed.fields), 25)
        self.assertEqual(len(second_embed.fields), 5)

    def test_split_fields_webhook(self):
        embed = discord.Embed(title="Test")
        for i in range(30):
            embed.add_field(name=f"f{i}", value=str(i))

        with patch.object(settings, "discord_webhook_url", "http://example.com"), \
             patch.object(discord_bot.discord_bot_instance, "send_to_webhook", new_callable=AsyncMock) as mock_hook:
            asyncio.run(discord_bot.send_to_discord(123, embed=embed, use_webhook=True))

        self.assertEqual(mock_hook.await_count, 2)
        first_embed = mock_hook.await_args_list[0][0][2]
        second_embed = mock_hook.await_args_list[1][0][2]
        self.assertEqual(len(first_embed.fields), 25)
        self.assertEqual(len(second_embed.fields), 5)


if __name__ == "__main__":
    unittest.main()
