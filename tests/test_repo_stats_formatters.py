import unittest
import discord
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from formatters import (
    format_repo_commit_stats,
    format_repo_pr_stats,
    format_repo_merge_stats,
)


class TestRepoStatsFormatters(unittest.TestCase):
    def test_commit_stats_embed(self):
        embed = format_repo_commit_stats("repo", "http://example.com", 5)
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("repo", embed.title)
        field = embed.fields[0]
        self.assertEqual(field.name, "Total Commits")
        self.assertEqual(field.value, "5")

    def test_pr_stats_embed(self):
        embed = format_repo_pr_stats("repo", "http://example.com", 3)
        self.assertIsInstance(embed, discord.Embed)
        field = embed.fields[0]
        self.assertEqual(field.name, "Total Pull Requests")
        self.assertEqual(field.value, "3")

    def test_merge_stats_embed(self):
        embed = format_repo_merge_stats("repo", "http://example.com", 2)
        self.assertIsInstance(embed, discord.Embed)
        field = embed.fields[0]
        self.assertEqual(field.name, "Total Merges")
        self.assertEqual(field.value, "2")


if __name__ == "__main__":
    unittest.main()
