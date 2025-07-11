#!/bin/bash

# Restart script for Discord GitHub Bot

SERVICE_NAME="discord-github.service"

# Stop the service
systemctl stop $SERVICE_NAME

# Start the service
systemctl start $SERVICE_NAME

# Check the status
systemctl status $SERVICE_NAME --no-pager
