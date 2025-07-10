# Channel Mapping

This page describes how GitHub events are routed to Discord channels. Channel IDs are configured via environment variables in `.env` and loaded by `config.py`.

## Event to Channel Map

| GitHub Event | Discord Channel Environment Variable |
|--------------|--------------------------------------|
| `push` | `CHANNEL_COMMITS` |
| `pull_request` (merged) | `CHANNEL_CODE_MERGES` |
| `pull_request` (other actions) | `CHANNEL_PULL_REQUESTS` |
| `issues` | `CHANNEL_ISSUES` |
| `release` | `CHANNEL_RELEASES` |
| `deployment_status` | `CHANNEL_DEPLOYMENT_STATUS` |
| `gollum` | `CHANNEL_GOLLUM` |
| any other | `CHANNEL_BOT_LOGS` |

Overview channels aggregate daily summaries:

- `CHANNEL_COMMITS_OVERVIEW`
- `CHANNEL_PULL_REQUESTS_OVERVIEW`
- `CHANNEL_MERGES_OVERVIEW`

If sending a message fails, the bot falls back to `CHANNEL_BOT_LOGS`.

[Deployment guide](Deployment.md) ← Previous | [Unmergeable PR report](../unmergeable_prs_report.md) →
