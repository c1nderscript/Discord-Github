# Discord GitHub Bot Documentation

This directory contains extended documentation for setting up and operating the bot.

## Setup

### Webhook Secret
1. In GitHub, open your repository **Settings** → **Webhooks** and click **Add webhook**.
2. Enter the payload URL of your running bot (e.g. `https://example.com/github`).
3. Choose `application/json` as the content type.
4. Set a **secret** to secure incoming requests.
5. Add the same value to your `.env` file under `GITHUB_WEBHOOK_SECRET`.

### Discord Permissions
1. Create a Discord bot in the [Developer Portal](https://discord.com/developers/applications).
2. On the **Bot** tab enable the permissions your channels require (e.g. `Send Messages`, `Embed Links`).
3. Invite the bot to your server with these permissions.
4. Record the channel IDs for each target channel and set them in your `.env`.

## Troubleshooting

### Hitting Rate Limits
- GitHub or Discord may throttle requests when activity spikes.
- Reduce message volume or batch updates to avoid bursts.

### Missing Channels
- If the bot logs errors about unknown channel IDs, verify the IDs in `.env`.
- Ensure the bot has access to each channel and the required permissions to post.

## Extending Event Formatters

Formatter functions in `formatters.py` create rich embeds from webhook payloads.
To support a new GitHub event:
1. Add a new `format_<event>` function to `formatters.py`.
2. Include any icons or colors that distinguish the event.
3. Update the router in `main.py` to call the new formatter and direct messages to the correct channel.
4. Write tests covering the formatter logic and routing.

