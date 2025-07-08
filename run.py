#!/usr/bin/env python3
"""Startup script for the GitHub Discord bot."""

import asyncio
import logging
import uvicorn
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Main function to start the server."""
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
        reload=False
    )

if __name__ == "__main__":
    main()
