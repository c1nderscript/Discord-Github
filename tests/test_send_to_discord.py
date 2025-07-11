import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import discord
import discord_bot


class TestSendToDiscord(unittest.TestCase):
    def test_large_embed_is_split(self):
        embed = discord.Embed(title="Test")
        for i in range(30):
            embed.add_field(name=f"Field{i}", value=str(i), inline=False)

        messages = [MagicMock(), MagicMock()]
        with patch.object(
            discord_bot.discord_bot_instance,
            "send_to_channel",
            new_callable=AsyncMock,
            side_effect=messages,
        ) as mock_send:
            asyncio.run(discord_bot.send_to_discord(123, embed=embed))

        self.assertEqual(mock_send.await_count, 2)
        for call in mock_send.await_args_list:
            called_embed = call.kwargs["embed"]
            self.assertLessEqual(len(called_embed.fields), 25)


if __name__ == "__main__":
    unittest.main()
