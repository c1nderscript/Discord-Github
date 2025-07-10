#!/usr/bin/env python3
"""Health check script for AGENTS.MD compliance."""

import sys
import os
from pathlib import Path
from agents_config import AGENT_METADATA, AGENTS_CANONICAL_DIR, LOGS_DIR, STATE_DIR


def check_directory_permissions(directory: Path, user: str = "deploy") -> bool:
    """Check if directory exists and has proper permissions for user."""
    if not directory.exists():
        print(f"❌ Directory {directory} does not exist")
        return False

    if not directory.is_dir():
        print(f"❌ {directory} is not a directory")
        return False

    # Check if directory is writable (simplified check)
    test_file = directory / "test_write_permissions"
    try:
        test_file.touch()
        test_file.unlink()
        print(f"✅ Directory {directory} has write permissions")
        return True
    except PermissionError:
        print(f"❌ Directory {directory} lacks write permissions")
        return False
    except Exception as e:
        print(f"⚠️  Could not test permissions for {directory}: {e}")
        return False


def check_agent_compliance():
    """Check if the agent is compliant with AGENTS.MD specifications."""
    print("🔍 Checking AGENTS.MD compliance...")
    print("=" * 50)

    # Display the directory source
    env_value = os.getenv("AGENTS_DIR")
    if env_value:
        print(f"🌐 Using AGENTS_DIR from environment: {env_value}")
    else:
        print("🌐 AGENTS_DIR not set; using current directory")

    # Check canonical directory
    print(f"📁 Canonical directory: {AGENTS_CANONICAL_DIR}")
    if not check_directory_permissions(AGENTS_CANONICAL_DIR):
        return False

    # Check logs directory
    print(f"📄 Logs directory: {LOGS_DIR}")
    if not check_directory_permissions(LOGS_DIR):
        return False

    # Check state directory
    print(f"💾 State directory: {STATE_DIR}")
    if not check_directory_permissions(STATE_DIR):
        return False

    # Check for log files
    log_files = ["bot.log", "webhook_server.log", "application.log", "errors.log"]
    for log_file in log_files:
        log_path = LOGS_DIR / log_file
        if log_path.exists():
            print(f"✅ Log file found: {log_file}")
        else:
            print(f"⚠️  Log file missing: {log_file}")

    # Check for state files
    state_files = ["pr_message_map.json", "repositories.json"]
    for state_file in state_files:
        state_path = STATE_DIR / state_file
        if state_path.exists():
            print(f"✅ State file found: {state_file}")
        else:
            print(f"⚠️  State file missing: {state_file}")

    # Check metadata
    print("\n📋 Agent Metadata:")
    for key, value in AGENT_METADATA.items():
        print(f"  {key}: {value}")

    print("\n🎉 Agent compliance check completed!")
    return True


if __name__ == "__main__":
    success = check_agent_compliance()
    sys.exit(0 if success else 1)
