import unittest
import discord

from utils.embed_utils import split_embed_fields


class TestEmbedUtils(unittest.TestCase):
    def test_split_embed_fields(self):
        embed = discord.Embed(title="Test")
        for i in range(30):
            embed.add_field(name=f"Field{i}", value=str(i), inline=False)

        embeds = split_embed_fields(embed, max_fields=25)
        self.assertEqual(len(embeds), 2)
        self.assertEqual(len(embeds[0].fields), 25)
        self.assertEqual(len(embeds[1].fields), 5)


if __name__ == "__main__":
    unittest.main()
