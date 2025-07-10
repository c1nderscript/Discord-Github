"""Agent configuration for canonical directory compliance."""

from pathlib import Path
import os

# AGENTS.MD compliant canonical directory
AGENTS_CANONICAL_DIR = Path("/home/cinder/Documents/Agents")

# Subdirectories
AGENTS_LOGS_DIR = AGENTS_CANONICAL_DIR / "logs"
AGENTS_STATE_DIR = AGENTS_CANONICAL_DIR / "state"
AGENTS_CONFIG_DIR = AGENTS_CANONICAL_DIR / "config"
AGENTS_SHARED_DIR = AGENTS_CANONICAL_DIR / "shared"


# Ensure all directories exist with proper permissions
def ensure_agents_directories():
    """Ensure all required agent directories exist with proper permissions."""
    for directory in [
        AGENTS_LOGS_DIR,
        AGENTS_STATE_DIR,
        AGENTS_CONFIG_DIR,
        AGENTS_SHARED_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

        # Set permissions to allow deploy user to write
        try:
            os.chmod(directory, 0o755)
            # Change ownership to deploy user if possible
            if os.getuid() == 0:  # Running as root
                import pwd

                deploy_user = pwd.getpwnam("deploy")
                os.chown(directory, deploy_user.pw_uid, deploy_user.pw_gid)
        except (OSError, KeyError):
            # Ignore permission errors if not running as root
            pass


# Initialize on import
ensure_agents_directories()

# Export commonly used paths
LOGS_DIR = AGENTS_LOGS_DIR
STATE_DIR = AGENTS_STATE_DIR
CONFIG_DIR = AGENTS_CONFIG_DIR
SHARED_DIR = AGENTS_SHARED_DIR

# Agent metadata for compliance
AGENT_METADATA = {
    "name": "Discord-GitHub Webhook Bot",
    "version": "1.0.0",
    "canonical_dir": str(AGENTS_CANONICAL_DIR),
    "logs_dir": str(AGENTS_LOGS_DIR),
    "state_dir": str(AGENTS_STATE_DIR),
    "config_dir": str(AGENTS_CONFIG_DIR),
    "shared_dir": str(AGENTS_SHARED_DIR),
    "compliance": "AGENTS.MD v1.0",
}
