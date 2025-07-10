# Discord GitHub Bot Wiki

This wiki provides additional documentation for running and maintaining the Discord GitHub webhook bot.

## Setup

1. Run `bash setup_env.sh` to install dependencies and activate the virtual environment.
2. Start the bot with `python run.py`.

## Features

- Routes GitHub events to Discord channels using FastAPI.
- Supports pull requests, issues, deployments, releases and wiki updates.
- Includes cleanup utilities for old pull request notifications.

