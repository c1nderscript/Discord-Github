# Discord-Github

FastAPI-based webhook router that forwards GitHub events to Discord channels. This document provides a complete setup guide and instructions for maintaining each component, including GitHub webhooks.

## How to Re-run the Webhook Script

To re-run the webhook script `add_all_webhooks.py` when new repositories are created, follow these steps:

1. Ensure your `.env` file is correctly configured with the following variables:
   - `GITHUB_TOKEN`: Your GitHub personal access token with repository access.
   - `GITHUB_WEBHOOK_SECRET`: The secret for verifying webhooks.
   - `GITHUB_USERNAME`: Your GitHub username.
   - `WEBHOOK_URL`: The URL for the webhook destination (e.g., your service endpoint).

2. Run the script using:
   ```bash
   python add_all_webhooks.py
   ```

This will add the necessary webhooks to all repositories associated with your GitHub account.

### Automated Weekly Execution

The repository includes a GitHub Actions workflow that automatically runs the webhook script every Sunday at 2 AM UTC to ensure all repositories have the required webhooks.

**To enable the automated workflow:**

1. Set up the following repository secrets in your GitHub repository settings:
   - Go to your repository → Settings → Secrets and variables → Actions
   - Click "New repository secret" for each of the following:
     - `GITHUB_TOKEN`: Your GitHub personal access token (with repo permissions)
     - `GITHUB_WEBHOOK_SECRET`: The secret for webhook verification
     - `GITHUB_USERNAME`: Your GitHub username
     - `WEBHOOK_URL`: The URL for the webhook destination (e.g., `http://65.21.253.0:8000/github`)

2. The workflow will automatically run weekly, or you can trigger it manually from the Actions tab.

3. If the workflow fails, it will automatically create an issue in the repository for investigation.

## Setup

1. Copy `.env.template` to `.env` and add your configuration:
   ```bash
   cp .env.template .env
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the bot:
   ```bash
   python run.py
   ```

### Environment Variables

Set `DISCORD_WEBHOOK_URL` in your `.env` file to the Discord webhook you want to
use for sending messages. For example:

```ini
DISCORD_WEBHOOK_URL=https://discordapp.com/api/webhooks/your_webhook_id/your_webhook_token/github
```

## Pull Request Message Cleanup

When a pull request is opened or marked ready for review, the bot records the Discord message ID in `pr_message_map.json`.
Once the pull request is closed (merged or not), the stored message is automatically deleted from the `#pull-requests` channel.
The JSON file maps `repo_name#pr_number` to the associated Discord message ID and is created at runtime in the project root.
