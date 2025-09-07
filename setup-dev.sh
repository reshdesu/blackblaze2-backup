#!/bin/bash
# Setup script for BlackBlaze B2 Backup Tool development

echo "Setting up BlackBlaze B2 Backup Tool development environment..."

# Install pre-commit if not already installed
if ! command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit..."
    uv pip install pre-commit
fi

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install

# Run pre-commit on all files to fix any existing issues
echo "Running pre-commit hooks on all files..."
pre-commit run --all-files

echo "✅ Development environment setup complete!"
echo ""
echo "Pre-commit hooks are now active and will automatically:"
echo "- Format code with ruff"
echo "- Remove trailing whitespace"
echo "- Fix end-of-file issues"
echo "- Check YAML syntax"
echo "- Prevent large files and merge conflicts"
echo ""
echo "These hooks will run automatically before each commit."
