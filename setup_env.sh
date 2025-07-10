#!/usr/bin/env bash
set -e

# Install pip if missing
if ! command -v pip >/dev/null 2>&1; then
    echo "pip not found. Installing python3-pip..."
    sudo apt-get update && sudo apt-get install -y python3-pip
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# Activate the virtual environment
# shellcheck source=/dev/null
source .venv/bin/activate

# Install required Python packages
pip install --upgrade pip
pip install -r requirements.txt
