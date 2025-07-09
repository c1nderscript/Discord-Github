"""Configuration settings for the GitHub-Discord bot."""

from pydantic_settings import BaseSettings
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
    webhook_url: Optional[str] = None
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Discord Channel IDs
    channel_commits: int = 1392213436720615504
    channel_pull_requests: int = 1392485974398861354
    channel_code_merges: int = 1392213492156727387
    channel_issues: int = 1392213509382737991
    channel_releases: int = 1392213528542445628
    channel_deployment_status: int = 1392213551665381486
    channel_ci_builds: int = 1392457950169268334
    channel_gollum: int = 1392213582963540028
    channel_bot_logs: int = 1392213610167664670

    # Message retention configuration
    message_retention_days: int = 30
    
    # Agent compliance paths
    logs_directory: str = str(LOGS_DIR)
    state_directory: str = str(STATE_DIR)
    agent_metadata: dict = AGENT_METADATA
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
