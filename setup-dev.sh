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

# Run comprehensive format check
echo "Running comprehensive format check..."
python scripts/check-formatting.py

# Sync version from pyproject.toml to __init__.py
echo "Syncing version information..."
python scripts/sync_version.py

echo "✅ Development environment setup complete!"
echo ""
echo "Pre-commit hooks are now active and will automatically:"
echo "- Format code with ruff"
echo "- Remove trailing whitespace"
echo "- Fix end-of-file issues"
echo "- Check YAML syntax"
echo "- Prevent large files and merge conflicts"
echo "- Check all Python files are formatted"
echo ""
echo "Additional tools available:"
echo "- python scripts/check-formatting.py (check formatting)"
echo "- python scripts/check-formatting.py --fix (fix formatting)"
echo "- python scripts/setup-precommit.sh (reinstall pre-commit hooks)"
echo ""
echo "These hooks will run automatically before each commit."
