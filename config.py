"""Configuration settings for the GitHub-Discord bot."""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional
from agents_config import AGENT_METADATA, LOGS_DIR, STATE_DIR


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Discord Bot Configuration
    discord_bot_token: str
    discord_webhook_url: Optional[str] = None

    # GitHub Webhook Configuration
    github_webhook_secret: Optional[str] = None
    github_token: Optional[str] = None
    github_username: Optional[str] = None

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # GitHub Statistics Channels (Category: 1392467153093132319)
    # These show API-based statistics with hourly updates
    stats_category_id: int = 1392467153093132319
    channel_stats_commits: int = 1392467209162592266
    channel_stats_pull_requests: int = 1392467228624158730
    channel_stats_merges: int = 1392213492156727387
    channel_stats_repos: int = 1393236980963475550
    channel_stats_contributions: int = 1393237031076888727

    # Dynamic GitHub Channels (Category: 1391791353821925376)
    # These show message-count based statistics with auto-deletion
    dynamic_category_id: int = 1391791353821925376
    channel_commits: int = 1392213436720615504
    channel_pull_requests: int = 1392485974398861354
    channel_code_merges: int = 1392213492156727387
    channel_issues: int = 1392213509382737991
    channel_releases: int = 1392213528542445628
    channel_deployment_status: int = 1392213551665381486
    channel_ci_builds: int = 1392457950169268334

    # GitHub Logging Channels (Category: 1392190727403868170)
    logging_category_id: int = 1392190727403868170
    channel_bot_commands: int = 1392190753291243652
    channel_bot_logs: int = 1392213610167664670

    # Legacy overview channels (for backward compatibility)
    channel_commits_overview: int = 1392467209162592266
    channel_pull_requests_overview: int = 1392467228624158730
    channel_merges_overview: int = 1392467252711919666
    channel_gollum: int = 1392213582963540028

    # Message retention configuration
    message_retention_days: int = 30

    # Cleanup interval in minutes for resolved pull requests
    pr_cleanup_interval_minutes: int = 60

    # Statistics update interval in minutes (hourly = 60)
    stats_update_interval_minutes: int = 60

    # Agent compliance paths
    logs_directory: str = str(LOGS_DIR)
    state_directory: str = str(STATE_DIR)
    agent_metadata: dict = AGENT_METADATA
 
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def all_dynamic_channels(self) -> list[int]:
        """Return all dynamic channels that need message counting."""
        return [
            self.channel_commits,
            self.channel_pull_requests,
            self.channel_code_merges,
            self.channel_issues,
            self.channel_releases,
            self.channel_deployment_status,
            self.channel_ci_builds,
        ]

    @property
    def all_stats_channels(self) -> list[int]:
        """Return all statistics channels that need API-based updates."""
        return [
            self.channel_stats_commits,
            self.channel_stats_pull_requests,
            self.channel_stats_merges,
            self.channel_stats_repos,
            self.channel_stats_contributions,
        ]


# Global settings instance
settings = Settings()
