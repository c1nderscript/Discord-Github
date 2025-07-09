import os
import unittest
from fastapi.testclient import TestClient

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import main
from discord_bot import discord_bot_instance

class TestHealthEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_health_ok(self):
        discord_bot_instance.ready = True
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

if __name__ == "__main__":
    unittest.main()
