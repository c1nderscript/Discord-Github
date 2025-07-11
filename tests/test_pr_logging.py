import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

class TestPullRequestLogging(unittest.TestCase):
    def test_success_log_once(self):
        with patch("discord.ext.commands.Bot.add_command"), patch("discord_bot.send_to_discord", new_callable=AsyncMock), patch("discord_bot.discord_bot_instance"):
            import importlib
            import main
            importlib.reload(main)

        payload = {"action": "opened", "pull_request": {}, "repository": {}}

        def close_coro(coro):
            coro.close()
            return MagicMock()

        with patch(
            "main.handle_pull_request_event_with_retry",
            new_callable=AsyncMock,
            return_value=True,
        ), patch("main.send_to_discord", new_callable=AsyncMock), patch(
            "main.update_github_stats",
            new_callable=AsyncMock,
        ), patch("asyncio.create_task", side_effect=close_coro), self.assertLogs(
            main.logger, level="INFO"
        ) as cm:
            asyncio.run(main.route_github_event("pull_request", payload))

        log_lines = [line for line in cm.output if "Successfully processed pull_request event" in line]
        self.assertEqual(len(log_lines), 1)


if __name__ == "__main__":
    unittest.main()
