#!/usr/bin/env python3
"""
Script to add GitHub webhooks to ALL repositories using GitHub API.
"""

import json
import requests
import time
from typing import List, Dict

# Configuration - Replace with your actual values
WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_URL_HERE"
WEBHOOK_SECRET = "YOUR_WEBHOOK_SECRET_HERE"
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN_HERE"
GITHUB_USERNAME = "YOUR_GITHUB_USERNAME_HERE"

def get_all_repositories() -> List[str]:
    """
    Get all repositories for the user from GitHub API (including private ones).
    """
    url = f"https://api.github.com/user/repos"  # Use /user/repos for authenticated user
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    params = {
        "per_page": 100,
        "visibility": "all",
        "affiliation": "owner"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            repos = response.json()
            repo_names = [repo['name'] for repo in repos]
            print(f"Found {len(repo_names)} repositories")
            return repo_names
        else:
            print(f"Error fetching repositories: {response.status_code}")
            print(f"Response: {response.text}")
            return []
            
    except Exception as e:
        print(f"Error fetching repositories: {str(e)}")
        return []

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
    print("🔍 Fetching all repositories...")
    repositories = get_all_repositories()
    
    if not repositories:
        print("❌ No repositories found or error occurred")
        return
    
    print(f"🚀 Adding GitHub webhooks to {len(repositories)} repositories...")
    print(f"📡 Webhook URL: {WEBHOOK_URL}")
    print("-" * 50)
    
    success_count = 0
    failed_repos = []
    existing_webhooks = 0
    
    for repo in repositories:
        result = add_webhook_to_repo(repo)
        if result:
            success_count += 1
        else:
            # Check if it's an existing webhook (422 error)
            if "already exist" in str(result):
                existing_webhooks += 1
            else:
                failed_repos.append(repo)
        
        # Add a small delay to avoid rate limiting
        time.sleep(1)
    
    print("-" * 50)
    print(f"📊 Summary:")
    print(f"✅ Successfully added: {success_count}")
    print(f"⚠️  Already existed: {existing_webhooks}")
    print(f"❌ Failed: {len(failed_repos)}")
    print(f"📦 Total repositories: {len(repositories)}")
    
    if failed_repos:
        print(f"Failed repositories: {', '.join(failed_repos)}")
    
    print("\n🎉 Webhook setup complete!")

if __name__ == "__main__":
    main()
