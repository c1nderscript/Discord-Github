# Discord-Github

FastAPI-based webhook router that forwards GitHub events to Discord channels.

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
