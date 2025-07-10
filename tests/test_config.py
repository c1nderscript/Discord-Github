import os
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

from config import Settings, settings


class TestConfig(unittest.TestCase):
    def test_settings_load(self):
        self.assertIsInstance(settings, Settings)
        self.assertEqual(settings.host, "0.0.0.0")
        self.assertEqual(settings.port, 8000)
        self.assertIsInstance(settings.channel_commits, int)
        self.assertIsInstance(settings.channel_pull_requests, int)
        self.assertIsInstance(settings.channel_bot_logs, int)


if __name__ == "__main__":
    unittest.main()
