#!/bin/bash
# Simple script to run BlackBlaze B2 Backup Tool with uv

echo "Starting BlackBlaze B2 Backup Tool..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

# Run the application
uv run python main.py
