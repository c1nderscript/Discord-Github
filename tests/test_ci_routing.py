import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

import main
from config import settings


def load_payload(name: str) -> dict:
    payload_dir = Path(__file__).parent / "payloads"
    with open(payload_dir / name, "r") as f:
        return json.load(f)


class TestCIRouting:
    def test_route_workflow_run(self):
        payload = load_payload("workflow_run.json")
        embed = MagicMock()
        with patch("main.format_workflow_run", return_value=embed) as fmt, patch(
            "main.send_to_discord", new_callable=AsyncMock
        ) as send:
            asyncio.run(main.route_github_event("workflow_run", payload))
            fmt.assert_called_once_with(payload)
            send.assert_awaited_once_with(settings.channel_ci_builds, embed=embed)

    def test_route_workflow_job(self):
        payload = load_payload("workflow_job.json")
        embed = MagicMock()
        with patch("main.format_workflow_job", return_value=embed) as fmt, patch(
            "main.send_to_discord", new_callable=AsyncMock
        ) as send:
            asyncio.run(main.route_github_event("workflow_job", payload))
            fmt.assert_called_once_with(payload)
            send.assert_awaited_once_with(settings.channel_ci_builds, embed=embed)

    def test_route_check_run(self):
        payload = load_payload("check_run.json")
        embed = MagicMock()
        with patch("main.format_check_run", return_value=embed) as fmt, patch(
            "main.send_to_discord", new_callable=AsyncMock
        ) as send:
            asyncio.run(main.route_github_event("check_run", payload))
            fmt.assert_called_once_with(payload)
            send.assert_awaited_once_with(settings.channel_ci_builds, embed=embed)

    def test_route_check_suite(self):
        payload = load_payload("check_suite.json")
        embed = MagicMock()
        with patch("main.format_check_suite", return_value=embed) as fmt, patch(
            "main.send_to_discord", new_callable=AsyncMock
        ) as send:
            asyncio.run(main.route_github_event("check_suite", payload))
            fmt.assert_called_once_with(payload)
            send.assert_awaited_once_with(settings.channel_ci_builds, embed=embed)
