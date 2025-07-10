# Deployment

This guide describes how to run the bot in production.

## Docker Compose

A `docker-compose.yml` file is provided. It builds the application image, mounts a `logs/` volume and exposes port `8000`.

```bash
docker compose up -d
```

Traefik labels in the compose file expose the bot through a reverse proxy defined in `traefik.yml`.

## Systemd

The `discord-github-bot.service` unit runs the bot with `python run.py` in a virtual environment. Copy the file to `/etc/systemd/system/` and enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now discord-github-bot
```

## Supervisor

A sample `supervisor.conf` is included. Place it in `/etc/supervisor/conf.d/` and run `supervisorctl reread && supervisorctl update`.

For additional options, see [Channel mapping](ChannelMapping.md).

[Channel mapping](ChannelMapping.md) ← Previous | [Project README](../README.md) →
