import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, call, MagicMock, patch
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DISCORD_BOT_TOKEN", "dummy")

from discord_bot import clear_channels, DEV_CHANNELS, discord_bot_instance


class TestClearCommand(unittest.TestCase):
    def test_clear_purges_all_channels(self):
        ctx = MagicMock()
        ctx.send = AsyncMock()
        with patch.object(
            discord_bot_instance, "purge_old_messages", new_callable=AsyncMock
        ) as mock_purge:
            asyncio.run(clear_channels(ctx))
            mock_purge.assert_has_awaits(
                [call(ch, 0) for ch in DEV_CHANNELS], any_order=True
            )
        ctx.send.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
