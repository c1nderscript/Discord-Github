# Discord-Github

A webhook router that receives GitHub events and posts rich messages to Discord. It uses FastAPI for the HTTP layer and `discord.py` for interacting with Discord.


## Architecture

Additional setup and troubleshooting details can be found in the [docs directory](docs/README.md).

## How to Re-run the Webhook Script


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

For a quicker start you can run the helper script:

```bash
./setup.sh
```

It installs all dependencies inside `.venv` and copies `.env.template` to `.env`
if needed. See **AGENTS.md** for guidelines on keeping this script current.

### Environment Variables


Set `DISCORD_WEBHOOK_URL` in your `.env` file to the Discord webhook you want to
use for sending messages. For example:

```ini
DISCORD_WEBHOOK_URL=https://discordapp.com/api/webhooks/your_webhook_id/your_webhook_token/github
```

Set `AGENTS_DIR` to specify where logs and state files are stored. If not set, the
current working directory is used.

You can control how long messages stay in key channels by setting `MESSAGE_RETENTION_DAYS`.
If not set, messages older than 30 days are removed.


The bot posts messages to multiple Discord channels. Override their IDs in `.env` if your server uses different channels:

- `CHANNEL_COMMITS`
- `CHANNEL_COMMITS_OVERVIEW`
- `CHANNEL_PULL_REQUESTS`
- `CHANNEL_PULL_REQUESTS_OVERVIEW`
- `CHANNEL_CODE_MERGES`
- `CHANNEL_MERGES_OVERVIEW`
- `CHANNEL_ISSUES`
- `CHANNEL_RELEASES`
- `CHANNEL_DEPLOYMENT_STATUS`
- `CHANNEL_GOLLUM`
- `CHANNEL_BOT_LOGS`
- `PR_CLEANUP_INTERVAL_MINUTES`

The bot can send high-level summaries to dedicated overview channels. Set these IDs in your `.env` file if you want to use them:

Copy `.env.template` to `.env` and edit each section. The template groups
variables for easier configuration. A shortened example is shown below:


```ini
# Discord settings
DISCORD_BOT_TOKEN=your_token
DISCORD_WEBHOOK_URL=https://discordapp.com/api/webhooks/...

# GitHub settings
GITHUB_WEBHOOK_SECRET=secret
GITHUB_TOKEN=token
GITHUB_USERNAME=username
WEBHOOK_URL=http://your-server/github

# Server settings
HOST=0.0.0.0
PORT=8000

# Discord channel IDs
CHANNEL_COMMITS=1392213436720615504
CHANNEL_PULL_REQUESTS=1392485974398861354
CHANNEL_CODE_MERGES=1392213492156727387
CHANNEL_ISSUES=1392213509382737991
CHANNEL_RELEASES=1392213528542445628
CHANNEL_DEPLOYMENT_STATUS=1392213551665381486
CHANNEL_CI_BUILDS=1392457950169268334
CHANNEL_GOLLUM=1392213582963540028
CHANNEL_BOT_LOGS=1392213610167664670
CHANNEL_COMMITS_OVERVIEW=1392467209162592266
CHANNEL_PULL_REQUESTS_OVERVIEW=1392467228624158730
CHANNEL_MERGES_OVERVIEW=1392467252711919666
PR_CLEANUP_INTERVAL_MINUTES=60
```

You can control how long messages stay in key channels by setting
`MESSAGE_RETENTION_DAYS` (default `30`). Overview channels are optional and can
be customised if your Discord server uses different IDs.


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
| `PR_CLEANUP_INTERVAL_MINUTES` | Interval (minutes) between checks for resolved PRs |

`MESSAGE_RETENTION_DAYS` can be set to automatically prune older messages (default `30`).
`PR_CLEANUP_INTERVAL_MINUTES` controls how often the bot checks for resolved pull requests (default `60`).

## Docker

The repository includes a `docker-compose.yml` that builds the image and exposes port `8000`. Run the service with:

```bash
docker compose up -d
```

Traefik configuration is included via `traefik.yml`.


## Systemd & Supervisor

`discord-github-bot.service` and `supervisor.conf` provide examples for running the bot as a service. Adjust the paths inside the files and enable either systemd or supervisor on your host.

## Tests

Before running the tests, execute the setup script so the environment has all
required packages installed:

```bash
./setup.sh
```

This installs everything from `requirements.txt` &ndash; including `discord.py`,
`aiohttp`, and `httpx` &ndash; inside `.venv`. Once setup is complete, run:

```bash
pytest -q
```


## Documentation

This script checks each entry in `pr_message_map.json`, queries the GitHub API to see if the PR is closed, and deletes the corresponding Discord message from the `#pull-requests` channel.

## Clearing the Pull Requests Channel

To quickly remove **all** messages from the pull requests channel, type:

```bash
!clear
```

The command purges the configured pull requests channel and clears the PR map so the list can be repopulated.

## Continuous Integration

Automated tests run with GitHub Actions. The workflow defined in
`.github/workflows/ci.yml` installs Python 3.11, installs the project
dependencies along with `pytest`, and executes the test suite with
`pytest -q` for each push and pull request.

## Discord Bot Commands

The bot provides a few convenience commands when interacting directly in Discord.

- `!update` (alias `!pr`) &ndash; Fetch all open pull requests across your repositories and repost them in the pull-requests channel. This is useful if the bot was offline when events occurred.
- `!clear` &ndash; Remove all messages from the pull-requests channel.
- `!setup` &ndash; Create missing channels automatically so the bot can operate in a new server.




Additional guides live in the [docs/](docs) folder:

- [Channel Mapping](docs/ChannelMapping.md)
- [Deployment](docs/Deployment.md)
- [Unmergeable PR Report](unmergeable_prs_report.md)

