#!/bin/bash
# Build script for Ubuntu 24.04 using uv

echo "Building BlackBlaze B2 Backup Tool for Ubuntu..."

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[build]"

# Create executable
pyinstaller --onefile --windowed --name "BlackBlaze-Backup-Tool" main.py

echo "Build complete! Executable created in dist/ directory"
echo "To run: ./dist/BlackBlaze-Backup-Tool"
