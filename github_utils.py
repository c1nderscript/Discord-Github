"""GitHub webhook utilities for signature verification."""

import hashlib
import hmac
from fastapi import Request, HTTPException

from config import settings


async def verify_github_signature(request: Request, body: bytes) -> None:
    """Verify the GitHub webhook signature."""
    if not settings.github_webhook_secret:
        # If no secret is configured, skip verification
        return

    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(
            status_code=401, detail="Missing X-Hub-Signature-256 header"
        )

    # Calculate the expected signature
    expected_signature = hmac.new(
        settings.github_webhook_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()

    # GitHub prefixes the signature with "sha256="
    expected_signature = f"sha256={expected_signature}"

    # Compare signatures
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")


def is_github_event_relevant(event_type: str, payload: dict) -> bool:
    """Check if the GitHub event is relevant and should be processed."""
    # Skip some events that might be too noisy
    skip_actions = {
        "pull_request": ["synchronize", "edited", "review_requested"],
        "issues": ["edited", "labeled", "unlabeled"],
        "push": [],  # Process all push events
    }

    if event_type in skip_actions:
        action = payload.get("action")
        if action in skip_actions[event_type]:
            return False

    return True
