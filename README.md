# Discord-Github

A webhook router that receives GitHub events and posts rich messages to Discord. It uses FastAPI for the HTTP layer and `discord.py` for interacting with Discord.

## Architecture

- **`main.py`** – FastAPI application exposing `/github` and `/health` endpoints.
- **`discord_bot.py`** – Discord client used to send embeds to channels.
- **`run.py`** – simple launcher that runs the app with Uvicorn.
- **Utilities** – scripts like `add_all_webhooks.py` and `cleanup_pr_messages.py` help manage webhooks and message history.

See the [Channel mapping](docs/ChannelMapping.md) document for routing details.

## Setup

1. Copy `.env.template` to `.env` and fill in the required values.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the bot:
   ```bash
   python run.py
   ```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `DISCORD_BOT_TOKEN` | Bot token used to connect to Discord |
| `DISCORD_WEBHOOK_URL` | Optional Discord webhook URL for message delivery |
| `GITHUB_WEBHOOK_SECRET` | Secret used to validate GitHub webhooks |
| `GITHUB_TOKEN` | Personal access token for GitHub API calls |
| `GITHUB_USERNAME` | GitHub username used by helper scripts |
| `WEBHOOK_URL` | Base webhook URL when creating webhooks |
| `HOST` | Bind address for the FastAPI server |
| `PORT` | Listening port for the FastAPI server |
| `CHANNEL_COMMITS` | Channel for push events |
| `CHANNEL_PULL_REQUESTS` | Channel for pull request events |
| `CHANNEL_CODE_MERGES` | Channel for merged pull requests |
| `CHANNEL_ISSUES` | Channel for issue events |
| `CHANNEL_RELEASES` | Channel for releases |
| `CHANNEL_DEPLOYMENT_STATUS` | Channel for deployment notifications |
| `CHANNEL_GOLLUM` | Channel for wiki updates |
| `CHANNEL_BOT_LOGS` | Fallback channel for errors |
| `CHANNEL_COMMITS_OVERVIEW` | Optional overview channel for commits |
| `CHANNEL_PULL_REQUESTS_OVERVIEW` | Optional overview channel for PRs |
| `CHANNEL_MERGES_OVERVIEW` | Optional overview channel for merges |

`MESSAGE_RETENTION_DAYS` can be set to automatically prune older messages (default `30`).

## Docker

The repository includes a `docker-compose.yml` that builds the image and exposes port `8000`. Run the service with:

```bash
docker compose up -d
```

Traefik configuration is included via `traefik.yml`.

## Systemd & Supervisor

`discord-github-bot.service` and `supervisor.conf` provide examples for running the bot as a service. Adjust the paths inside the files and enable either systemd or supervisor on your host.

## Tests

Install the requirements and run:

```bash
pytest -q
```

## Documentation

Additional guides live in the [docs/](docs) folder:

- [Channel Mapping](docs/ChannelMapping.md)
- [Deployment](docs/Deployment.md)
- [Unmergeable PR Report](unmergeable_prs_report.md)

