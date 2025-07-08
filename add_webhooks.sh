#!/bin/bash

# Script to add GitHub webhook to all repositories

# Webhook URL and Secret - Replace with your actual values
WEBHOOK_URL="YOUR_WEBHOOK_URL_HERE"
WEBHOOK_SECRET="YOUR_WEBHOOK_SECRET_HERE"

# GitHub API Token for Authorization
GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"

# Get all repository names
github_repos=(
    "Development-Setup"
    "Custom-MCP-Server"
    "Go-Lang-Docs"
    "Discord-Github"
    "Redis-Docs"
    "Trading-Docs"
    "Warp-Terminal-Docs"
    "Cinder-s-Webscraper"
    "Cinder-Development"
    "Python-Lang-Docs"
    "mobile-developer-git"
    "Password-Store"
    "Keffals"
    "Agents.md-Builder"
    "github-docs"
    "Master-Aliases"
    "Rust-Lang-Docs"
)

# Loop over repositories to add webhook
for repo in "${github_repos[@]}"; do
  curl -X POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    https://api.github.com/repos/c1nderscript/$repo/hooks \
    -d "{ \"name\": \"web\", \"active\": true, \"events\": [\"push\", \"pull_request\"], \"config\": { \"url\": \"$WEBHOOK_URL\", \"content_type\": \"json\", \"secret\": \"$WEBHOOK_SECRET\" } }"
done
