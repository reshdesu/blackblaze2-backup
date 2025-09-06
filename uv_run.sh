#!/bin/bash
# UV Run Script for BlackBlaze B2 Backup Tool

echo "BlackBlaze B2 Backup Tool - UV Runner"
echo "======================================"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

# Try different approaches to run with uv
echo "Starting BlackBlaze B2 Backup Tool..."

# Method 1: Try uv run with specific Python version
if uv run --python 3.12 python main.py 2>/dev/null; then
    echo "Application started successfully!"
    exit 0
fi

# Method 2: Create venv and install dependencies
echo "Creating virtual environment and installing dependencies..."
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .

# Run the application
echo "Starting application..."
python main.py
