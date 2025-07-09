import unittest
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import asyncio

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import main
from discord_bot import discord_bot_instance


class TestHealthEndpoint(unittest.TestCase):
    """Test the /health endpoint."""

    def test_health_ok(self):
        """Health endpoint returns expected response."""
        with patch.object(discord_bot_instance, "start", new_callable=AsyncMock), \
             patch.object(discord_bot_instance, "purge_old_messages", new_callable=AsyncMock), \
             patch.object(main, "cleanup_pr_messages", new_callable=AsyncMock):
            with TestClient(main.app) as client:
                response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
