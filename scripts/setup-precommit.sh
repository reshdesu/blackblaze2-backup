#!/bin/bash
"""
Setup script to ensure pre-commit hooks are properly configured and tested.
"""

set -e

echo "🔧 Setting up pre-commit hooks..."

# Install pre-commit if not already installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    uv pip install pre-commit
fi

# Install pre-commit hooks
echo "🔗 Installing pre-commit hooks..."
uv run pre-commit install

# Test pre-commit hooks on all files
echo "🧪 Testing pre-commit hooks on all files..."
uv run pre-commit run --all-files

echo "✅ Pre-commit setup complete!"
echo ""
echo "💡 Tips:"
echo "   - Pre-commit hooks will now run automatically on every commit"
echo "   - Run 'uv run pre-commit run --all-files' to check all files"
echo "   - Run 'python scripts/check-formatting.py' to check formatting manually"
echo "   - Run 'python scripts/check-formatting.py --fix' to fix formatting issues"
