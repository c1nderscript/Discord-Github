#!/usr/bin/env python3
"""
Script to add GitHub webhooks to all repositories using GitHub API.
"""

import json
import requests
import time
from typing import List, Dict

# Configuration - Replace with your actual values
WEBHOOK_URL = "YOUR_WEBHOOK_URL_HERE"  # Use your server IP
WEBHOOK_SECRET = "YOUR_WEBHOOK_SECRET_HERE"
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN_HERE"
GITHUB_USERNAME = "YOUR_GITHUB_USERNAME_HERE"

# Repository list (complete list - 25 repositories)
repositories = [
    "Development-Setup",
    "Custom-MCP-Server", 
    "Go-Lang-Docs",
    "Discord-Github",
    "Redis-Docs",
    "Trading-Docs",
    "Warp-Terminal-Docs",
    "Cinder-s-Webscraper",
    "Cinder-Development",
    "Python-Lang-Docs",
    "mobile-developer-git",
    "Password-Store",
    "Keffals",
    "Agents.md-Builder",
    "github-docs",
    "Main",
    "Master-Aliases",
    "Rust-Lang-Docs",
    # Additional repositories from complete search
    "keffals.gg",
    "github-mcp-server",
    "discordmcp",
    "Cinder-s-Webscraper",  # Note: might be duplicate
    "Password-Store",       # Note: might be duplicate
    "Keffals",              # Note: might be duplicate
    "Agents.md-Builder"     # Note: might be duplicate
]

def add_webhook_to_repo(repo_name: str) -> bool:
    """
    Add a webhook to a specific repository.
    """
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/hooks"
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    webhook_data = {
        "name": "web",
        "active": True,
        "events": [
            "push",
            "pull_request", 
            "issues",
            "release",
            "deployment_status",
            "gollum"
        ],
        "config": {
            "url": WEBHOOK_URL,
            "content_type": "json",
            "secret": WEBHOOK_SECRET,
            "insecure_ssl": "0"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=webhook_data)
        
        if response.status_code == 201:
            print(f"✅ Successfully added webhook to {repo_name}")
            return True
        elif response.status_code == 422:
            # Webhook might already exist
            print(f"⚠️  Webhook might already exist for {repo_name} (422 error)")
            return False
        else:
            print(f"❌ Failed to add webhook to {repo_name}: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error adding webhook to {repo_name}: {str(e)}")
        return False

def main():
    """
    Main function to add webhooks to all repositories.
    """
    print(f"🚀 Adding GitHub webhooks to {len(repositories)} repositories...")
    print(f"📡 Webhook URL: {WEBHOOK_URL}")
    print("-" * 50)
    
    success_count = 0
    failed_repos = []
    
    for repo in repositories:
        if add_webhook_to_repo(repo):
            success_count += 1
        else:
            failed_repos.append(repo)
        
        # Add a small delay to avoid rate limiting
        time.sleep(1)
    
    print("-" * 50)
    print(f"📊 Summary:")
    print(f"✅ Successfully added: {success_count}/{len(repositories)}")
    print(f"❌ Failed: {len(failed_repos)}")
    
    if failed_repos:
        print(f"Failed repositories: {', '.join(failed_repos)}")
    
    print("\n🎉 Webhook setup complete!")

if __name__ == "__main__":
    main()
