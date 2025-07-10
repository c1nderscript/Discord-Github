"""Logging configuration for the Discord-GitHub bot."""

import logging
import logging.handlers
from pathlib import Path
import os

# Canonical directory for agent logs and state. Use AGENTS_BASE_DIR env var if
# available, otherwise default to ~/Agents.
AGENTS_DIR = Path(
    os.environ.get("AGENTS_BASE_DIR", str(Path.home() / "Agents"))
).expanduser()
LOGS_DIR = AGENTS_DIR / "logs"
STATE_DIR = AGENTS_DIR / "state"

# Ensure directories exist and ignore permission errors
for _dir in (LOGS_DIR, STATE_DIR):
    try:
        _dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        continue


def setup_logging():
    """Set up logging configuration for the Discord-GitHub bot."""
    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Bot logs
    bot_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "bot.log", maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
    )
    bot_handler.setFormatter(detailed_formatter)
    bot_handler.setLevel(logging.INFO)

    # Webhook server logs
    webhook_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "webhook_server.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    webhook_handler.setFormatter(detailed_formatter)
    webhook_handler.setLevel(logging.INFO)

    # Application logs
    app_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "application.log", maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
    )
    app_handler.setFormatter(detailed_formatter)
    app_handler.setLevel(logging.INFO)

    # Error logs
    error_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "errors.log", maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
    )
    error_handler.setFormatter(detailed_formatter)
    error_handler.setLevel(logging.ERROR)

    # Configure specific loggers
    discord_logger = logging.getLogger("discord_bot")
    discord_logger.addHandler(bot_handler)
    discord_logger.addHandler(error_handler)
    discord_logger.setLevel(logging.INFO)

    webhook_logger = logging.getLogger("uvicorn")
    webhook_logger.addHandler(webhook_handler)
    webhook_logger.addHandler(error_handler)
    webhook_logger.setLevel(logging.INFO)

    app_logger = logging.getLogger("fastapi")
    app_logger.addHandler(app_handler)
    app_logger.addHandler(error_handler)
    app_logger.setLevel(logging.INFO)

    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(detailed_formatter)
    console_handler.setLevel(logging.INFO)

    # Add console handler to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(error_handler)

    return root_logger


def get_state_file_path(filename: str) -> Path:
    """Get the full path for a state file in the canonical directory."""
    return STATE_DIR / filename


def get_log_file_path(filename: str) -> Path:
    """Get the full path for a log file in the canonical directory."""
    return LOGS_DIR / filename
