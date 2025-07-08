Listens to the unified GitHub webhook.

Parses the event type (from headers like X-GitHub-Event and payload content).

Routes to the correct Discord channel ID based on a dispatch map.

🧠 Router Agent Blueprint: github_event_router
🧩 Inputs:
Webhook POST from GitHub at:
https://discordapp.com/api/webhooks/1392205631016145006/.../github

📦 Dispatcher Logic:
push → 1392213436720615504 (Commits)

pull_request →

if action == 'closed' & merged == true → 1392213492156727387 (Code-Merges)

else → 1392213464377724928 (Pull-Requests)

issues → 1392213509382737991

release → 1392213528542445628

deployment_status → 1392213551665381486

gollum → 1392213582963540028

Unknown/Other → 1392213610167664670 (Bot Logs)

🛠️ Processing Steps:
Parse X-GitHub-Event from headers.

Extract subfields (action, merged, ref, etc.) to refine routing.

Format a clean Discord embed or message.

POST to the appropriate Discord channel via bot API or Webhook ID.

📡 GitHub Event Routing Blueprint
GitHub Event Type	Discord Channel ID	Purpose
push (commits)	1392213436720615504	Log each commit with author & message.
pull_request	1392213464377724928	Opened, closed, merged, review events.
pull_request.merged	1392213492156727387	Special case for merged PRs.
issues	1392213509382737991	New issues, closures, comments.
release	1392213528542445628	New releases or draft updates.
deployment_status	1392213551665381486	GitHub Actions or CI/CD events.
gollum (wiki)	1392213582963540028	Wiki page edits or creations.
* (fallback)	1392213610167664670	Logs unmatched or malformed events.

🧱 Discord GitHub Router Integration Plan
1. Webhook Entry Point
Your existing endpoint (e.g., Flask/FastAPI):

python
Copy
Edit
@app.post("/github")
async def github_webhook(request: Request):
    event_type = request.headers.get("X-GitHub-Event")
    payload = await request.json()
    await router_agent(event_type, payload)
2. Router Agent Logic (router_agent)
   python
   Copy
   Edit
   async def router_agent(event_type: str, payload: dict):
    channel_map = {
        "push": "1392213436720615504",  # Commits
        "pull_request": handle_pr_event,
        "issues": "1392213509382737991",
        "release": "1392213528542445628",
        "deployment_status": "1392213551665381486",
        "gollum": "1392213582963540028"
    }

    handler = channel_map.get(event_type, "1392213610167664670")  # fallback: bot logs

    if callable(handler):
        await handler(payload)
    else:
        message = format_generic_event(event_type, payload)
        await send_to_discord(handler, message)
3. Special Case Handler: Pull Requests
   python
   Copy
   Edit
   async def handle_pr_event(payload: dict):
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    is_merged = pr.get("merged", False)

    if action == "closed" and is_merged:
        channel_id = "1392213492156727387"  # Code-Merges
    else:
        channel_id = "1392213464377724928"  # Pull-Requests

    message = format_pr_event(action, pr)
    await send_to_discord(channel_id, message)
4. Formatters
Define per-event formatters like format_generic_event() and format_pr_event() to create clean embeds or text for Discord.

5. Send Function
   python
   Copy
   Edit
   async def send_to_discord(channel_id: str, content: str):
    channel = bot.get_channel(int(channel_id))
    if channel:
        await channel.send(content)
