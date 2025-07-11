#!/usr/bin/env bash
# Codex environment setup script for the Discord GitHub Bot project.
# This script creates a Python virtual environment and installs the
# dependencies required for running the bot and its tests.

set -euo pipefail

# Create virtual environment if it does not already exist
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# Activate the virtual environment
source .venv/bin/activate

# Upgrade pip and install Python dependencies
python -m pip install --upgrade pip
# The tests depend on packages such as discord.py, so install everything
# from requirements.txt.
echo "Installing packages from requirements.txt..."
python -m pip install -r requirements.txt
python -m pip install pytest

# Create a default .env if none exists
if [ ! -f .env ] && [ -f .env.template ]; then
    cp .env.template .env
    echo "Created .env from template. Update it with your configuration."
fi

echo "Environment setup complete."
