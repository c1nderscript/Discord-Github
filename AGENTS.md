5. 

3. ------

   ## name: "Discord GitHub Webhook Bot" description: "A FastAPI-based webhook router that receives GitHub events and intelligently distributes them to specific Discord channels based on event type and context" category: "Backend Service" author: "Discord-GitHub Integration Team" tags: ["python", "fastapi", "discord", "github", "webhooks", "automation", "bot"] lastUpdated: "2025-07-08"

   # Discord GitHub Webhook Bot

   ## Project Overview

   This project is a sophisticated webhook router service that bridges GitHub repositories with Discord channels. It receives GitHub webhook events via FastAPI, intelligently parses event types and context, then routes formatted messages to appropriate Discord channels. The bot handles various GitHub events including commits, pull requests, issues, releases, deployments, and wiki updates with rich Discord embeds and proper error handling.

   **Core Functionality:**

   - Receives GitHub webhook POST requests
   - Parses GitHub event types from headers and payload
   - Routes events to specific Discord channels based on event type and context
   - Formats events as rich Discord embeds with appropriate colors and icons
   - Handles special cases (e.g., merged PRs go to different channel than opened PRs)
   - Provides error handling and fallback routing to bot logs channel

   ## Tech Stack

   - **Backend Framework**: FastAPI 0.104.1 with Python 3.8+
   - **Discord Integration**: discord.py 2.3.2
   - **HTTP Client**: aiohttp 3.9.0
   - **Configuration**: pydantic 2.5.0 + python-dotenv 1.0.0
   - **ASGI Server**: uvicorn 0.24.0
   - **Webhook Security**: GitHub webhook secret validation (optional)

   ## Project Structure

   ```
   discord-github/
   ├── config.py              # Centralized configuration with Pydantic settings
   ├── discord_bot.py          # Discord bot client and message sending logic
   ├── formatters.py           # Event formatters for rich Discord embeds
   ├── main.py                 # FastAPI webhook endpoint and router logic
   ├── requirements.txt        # Python dependencies
   ├── .env                    # Environment variables (not in repo)
   ├── AGENTS.md              # This file - AI agent instructions
   └── README.md              # Project documentation
   ```

   ## Development Guidelines

   ### Key Principles

   - **Event-Driven Architecture**: All functionality revolves around GitHub webhook events
   - **Asynchronous Processing**: Use async/await throughout for Discord API calls
   - **Rich Formatting**: Every event should have a well-formatted Discord embed
   - **Error Resilience**: Failed channel sends should fallback to bot logs channel
   - **Type Safety**: Use Pydantic models for configuration and data validation
   - **Separation of Concerns**: Keep routing logic, formatting, and Discord client separate

   ### Code Style Standards

   - Follow PEP 8 Python style guidelines
   - Use type hints for all function parameters and return values
   - Prefer f-strings for string formatting
   - Use descriptive variable names that indicate the GitHub event context
   - Keep functions focused on single responsibilities
   - Use async/await for all I/O operations (Discord API, HTTP requests)

   ### Naming Conventions

   - **Files**: lowercase with underscores (`discord_bot.py`)
   - **Functions**: lowercase with underscores (`format_push_event`)
   - **Classes**: PascalCase (`DiscordBot`, `Settings`)
   - **Constants**: UPPERCASE with underscores (`CHANNEL_COMMITS`)
   - **Environment Variables**: UPPERCASE with underscores (`DISCORD_BOT_TOKEN`)

   ## Channel Routing Strategy

   ### Discord Channel Mapping

   The bot routes GitHub events to specific Discord channels based on event type and context:

   ```python
   CHANNEL_MAP = {
       "push": settings.channel_commits,                    # 1392213436720615504
       "pull_request": handle_pr_routing,                   # Special handler
       "issues": settings.channel_issues,                   # 1392213509382737991
       "release": settings.channel_releases,                # 1392213528542445628
       "deployment_status": settings.channel_deployment_status, # 1392213551665381486
       "gollum": settings.channel_gollum,                   # 1392213582963540028
       "default": settings.channel_bot_logs                 # 1392213610167664670
   }
   ```

   Overview channels aggregate summaries for high-level discussion:

   - `channel_commits_overview` – 1392467209162592266
   - `channel_pull_requests_overview` – 1392467228624158730
   - `channel_merges_overview` – 1392467252711919666

   ### Special Routing Logic

   **Pull Request Events** require context-aware routing:

   - `action == "closed" AND merged == true` → Code Merges channel (1392213492156727387)
   - All other PR actions → Pull Requests channel (1392485974398861354)

   **Error Handling**: Any failed channel sends should attempt fallback to bot logs channel.

   ## Event Processing Pipeline

   ### 1. Webhook Reception

   ```python
   @app.post("/github")
   async def github_webhook(request: Request):
       # Extract GitHub event type from headers
       event_type = request.headers.get("X-GitHub-Event")
       signature = request.headers.get("X-Hub-Signature-256")
       
       # Validate webhook secret if configured
       payload = await request.json()
       
       # Route to appropriate handler
       await router_agent(event_type, payload)
   ```

   ### 2. Event Routing

   ```python
   async def router_agent(event_type: str, payload: dict):
       # Determine target channel based on event type
       # Handle special cases (e.g., merged PRs)
       # Call appropriate formatter
       # Send to Discord channel with error handling
   ```

   ### 3. Event Formatting

   Each event type should have a dedicated formatter that creates rich Discord embeds:

   - **Color coding** based on event type and status
   - **Appropriate icons** for visual recognition
   - **Clickable links** to GitHub resources
   - **Truncated descriptions** for long content
   - **Author/actor information** prominently displayed

   ### 4. Discord Delivery

   ```python
   async def send_to_discord(channel_id: int, embed: discord.Embed):
       # Get Discord channel by ID
       # Send embed with error handling
       # Fallback to bot logs channel on failure
       # Log all send attempts for debugging
   ```

   ## Configuration Management

   ### Environment Variables

   ```env
   # Required
   DISCORD_BOT_TOKEN=your_discord_bot_token
   
   # Optional
   GITHUB_WEBHOOK_SECRET=your_webhook_secret
   
   # Server Configuration
   HOST=0.0.0.0
   PORT=8000
   
   # Discord Channel IDs (can override defaults)
   CHANNEL_COMMITS=1392213436720615504
   CHANNEL_PULL_REQUESTS=1392485974398861354
   CHANNEL_CODE_MERGES=1392213492156727387
   CHANNEL_ISSUES=1392213509382737991
   CHANNEL_RELEASES=1392213528542445628
   CHANNEL_DEPLOYMENT_STATUS=1392213551665381486
   CHANNEL_GOLLUM=1392213582963540028
   CHANNEL_BOT_LOGS=1392213610167664670
   CHANNEL_COMMITS_OVERVIEW=1392467209162592266
   CHANNEL_PULL_REQUESTS_OVERVIEW=1392467228624158730
   CHANNEL_MERGES_OVERVIEW=1392467252711919666
   ```

   ### Pydantic Settings Model

   Use the `Settings` class in `config.py` for type-safe configuration loading with automatic environment variable parsing and validation.

   ## Testing Strategy

   ### Unit Testing Framework

   - **Primary**: pytest with pytest-asyncio for async testing
   - **Discord Mocking**: Use unittest.mock for Discord client methods
   - **Webhook Testing**: Test with sample GitHub webhook payloads

   ### Test Coverage Requirements

   - **Minimum Coverage**: 80% overall
   - **Critical Components**: 95% coverage for routing logic and formatters
   - **Edge Cases**: Test all special routing conditions (merged PRs, error fallbacks)

   ### Test Organization

   ```
   tests/
   ├── test_config.py          # Configuration loading tests
   ├── test_formatters.py      # Event formatting tests
   ├── test_routing.py         # Event routing logic tests
   ├── test_discord_client.py  # Discord bot client tests
   ├── fixtures/               # Sample GitHub webhook payloads
   │   ├── push_event.json
   │   ├── pr_opened.json
   │   ├── pr_merged.json
   │   └── ...
   └── conftest.py            # Pytest configuration and fixtures
   ```

   ### Sample Test Pattern

   ```python
   @pytest.mark.asyncio
   async def test_pull_request_merge_routing():
       """Test that merged PRs route to code-merges channel."""
       payload = load_fixture("pr_merged.json")
       
       with mock.patch('discord_bot.send_to_discord') as mock_send:
           await router_agent("pull_request", payload)
           
           mock_send.assert_called_once_with(
               settings.channel_code_merges,
               mock.ANY  # Discord embed
           )
   ```

   ## Current Development Focus

   ### Priority Features

   1. **Webhook Secret Validation**: Implement GitHub webhook secret verification for security
   2. **Rate Limiting**: Add rate limiting to prevent Discord API abuse
   3. **Retry Logic**: Implement exponential backoff for failed Discord sends
   4. **Health Checks**: Add health check endpoint for monitoring

   ### Active Tasks

   - **Formatter Enhancement**: Improve embed formatting for better visual appeal
   - **Error Monitoring**: Add structured logging for better debugging
   - **Configuration Validation**: Ensure all required channels exist on startup
   - **Documentation**: Complete API documentation and deployment guides

   ### Known Issues

   - Need to handle Discord rate limiting gracefully
   - Large commit pushes may exceed Discord message limits
   - Bot restart handling needs improvement

   ## Deployment Configuration

   ### Environment Setup

   ```bash
   # Install dependencies
   pip install -r requirements.txt
   
   # Set environment variables
   export DISCORD_BOT_TOKEN="your_token_here"
   export GITHUB_WEBHOOK_SECRET="your_secret_here"
   
   # Run the application
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

   ### Docker Deployment

   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY . .
   
   EXPOSE 8000
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

   ### GitHub Webhook Configuration

   - **Payload URL**: `https://your-domain.com/github`
   - **Content Type**: `application/json`
   - **Events**: Select specific events or choose "Send me everything"
   - **Secret**: Set webhook secret for security validation

   ## Security Considerations

   ### Webhook Security

   - **Secret Validation**: Always validate GitHub webhook signatures in production
   - **HTTPS Only**: Never accept webhooks over HTTP in production
   - **IP Allowlisting**: Consider restricting webhook source IPs

   ### Discord Bot Security

   - **Token Protection**: Store Discord bot token securely, never commit to repo
   - **Permission Scope**: Use minimal required Discord permissions
   - **Rate Limit Handling**: Implement proper rate limiting to avoid API abuse

   ### Error Information

   - **Log Sanitization**: Never log sensitive information like tokens
   - **Error Messages**: Avoid exposing internal implementation details
   - **Monitoring**: Set up alerts for unusual error patterns

   ## Performance Optimization

   ### Async Best Practices

   - Use `asyncio.gather()` for concurrent Discord sends when appropriate
   - Implement connection pooling for Discord API requests
   - Cache Discord channel objects to reduce API calls

   ### Memory Management

   - Process webhooks in batches during high activity
   - Implement payload size limits to prevent memory exhaustion
   - Use structured logging instead of keeping logs in memory

   ### Discord API Efficiency

   - Batch related messages when possible
   - Use Discord webhook URLs for high-volume channels
   - Implement intelligent retry strategies with exponential backoff

   ## Monitoring and Observability

   ### Logging Strategy

   ```python
   import logging
   
   # Structured logging for better observability
   logger = logging.getLogger(__name__)
   
   # Log levels by event type
   # INFO: Successful webhook processing
   # WARNING: Retries and fallbacks
   # ERROR: Failed processing or Discord sends
   # DEBUG: Detailed event payload information
   ```

   ### Health Monitoring

   - **Webhook Endpoint**: Monitor response times and success rates
   - **Discord Connectivity**: Regular Discord API health checks
   - **Channel Accessibility**: Verify bot can access all configured channels

   ### Metrics Collection

   - Track webhook processing times
   - Monitor Discord API rate limit usage
   - Count events by type and routing destination
   - Alert on error rate thresholds

   ## Common Issues and Solutions

   ### Issue: Discord Channel Not Found

   **Symptoms**: Bot logs show channel ID errors **Solution**: Verify channel IDs are correct and bot has access permissions

   ### Issue: Webhook Signature Validation Fails

   **Symptoms**: All webhooks rejected with 403 errors **Solution**: Verify GitHub webhook secret matches environment variable

   ### Issue: Large Payload Handling

   **Symptoms**: Messages truncated or Discord API errors **Solution**: Implement smart truncation in formatters, respect Discord limits

   ### Issue: Bot Startup Failures

   **Symptoms**: Discord bot won't connect on startup **Solution**: Check bot token validity and network connectivity

   ## AI Agent Instructions

   When working on this project, AI agents should:

   1. **Understand Event Context**: Always consider the GitHub event type and payload structure when implementing features
   2. **Preserve Async Patterns**: Maintain async/await throughout the codebase
   3. **Follow Channel Mapping**: Use the established channel routing logic, don't hardcode channel IDs
   4. **Rich Formatting**: Always create visually appealing Discord embeds with proper colors and icons
   5. **Error Resilience**: Implement proper error handling with fallback to bot logs channel
   6. **Type Safety**: Use type hints and Pydantic models for data validation
   7. **Test Coverage**: Write tests for all new routing logic and formatters
   8. **Security First**: Never expose tokens or sensitive data in logs or error messages

   ### Common Development Patterns

   **Adding New Event Type**:

   1. Add formatter function in `formatters.py`
   2. Add routing logic in main router
   3. Add channel configuration in `config.py`
   4. Write comprehensive tests
   5. Update this documentation

   **Modifying Embed Format**:

   1. Update relevant formatter function
   2. Test with sample payload
   3. Verify Discord rendering
   4. Check character limits and truncation

   **Adding Configuration Option**:

   1. Add to `Settings` class in `config.py`
   2. Update environment variable documentation
   3. Add validation if needed
   4. Test with different configurations

   ## Reference Resources

   - [FastAPI Documentation](https://fastapi.tiangolo.com/)
   - [discord.py Documentation](https://discordpy.readthedocs.io/)
   - [GitHub Webhooks Documentation](https://docs.github.com/en/developers/webhooks-and-events/webhooks)
   - [Pydantic Settings Management](https://pydantic-docs.helpmanual.io/usage/settings/)
   - [Discord Developer Portal](https://discord.com/developers/docs/)

   ------

   **Note**: This agents.md file should be updated whenever new event types are added, channel mappings change, or significant architectural modifications are made to the webhook routing system.

   ## Changelog

   ### 2025-07-09
   - Updated pull requests channel mapping to ID 1392485974398861354
