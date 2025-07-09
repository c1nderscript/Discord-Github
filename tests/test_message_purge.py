import asyncio
import importlib
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, call

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import pr_map
import config
from discord_bot import discord_bot_instance


class TestMessagePurge(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.pr_file = Path(self.tmpdir.name) / "map.json"
        patcher = patch.object(pr_map, "PR_MAP_FILE", self.pr_file)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmpdir.cleanup)

    def test_startup_event_triggers_purge(self):
        os.environ["MESSAGE_RETENTION_DAYS"] = "5"
        importlib.reload(config)
        import main
        importlib.reload(main)

        stored = []

        def fake_create_task(coro):
            stored.append(coro)
            return MagicMock()

        with patch.object(discord_bot_instance, "start", new_callable=AsyncMock), \
             patch.object(discord_bot_instance, "purge_old_messages", new_callable=AsyncMock) as mock_purge, \
             patch("main.cleanup_pr_messages", new_callable=AsyncMock) as mock_cleanup, \
             patch("main.update_github_stats", new_callable=AsyncMock), \
             patch("asyncio.create_task", side_effect=fake_create_task):
            asyncio.run(main.startup_event())

        for coro in stored:
            asyncio.run(coro)

        channels = [
            config.settings.channel_commits,
            config.settings.channel_pull_requests,
            config.settings.channel_releases,
        ]
        mock_purge.assert_has_awaits(
            [call(channel, 5) for channel in channels], any_order=True
        )
        mock_cleanup.assert_awaited_once()

    def test_purge_removes_pr_map_entries(self):
        pr_map.save_pr_map({"repo#1": 111})

        deleted_message = MagicMock()
        deleted_message.id = 111

        channel = MagicMock()
        channel.purge = AsyncMock(return_value=[deleted_message])

        discord_bot_instance.ready = True
        with patch.object(discord_bot_instance.bot, "get_channel", return_value=channel):
            asyncio.run(
                discord_bot_instance.purge_old_messages(
                    config.settings.channel_pull_requests, 1
                )
            )

        data = pr_map.load_pr_map()
        self.assertEqual(data, {})


if __name__ == "__main__":
    unittest.main()

