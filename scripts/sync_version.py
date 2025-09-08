#!/usr/bin/env python3
"""
Version synchronization script
Automatically updates __init__.py version from pyproject.toml
"""

from pathlib import Path

import tomllib


def sync_version():
    """Sync version from pyproject.toml to __init__.py"""
    # Read version from pyproject.toml
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    init_path = (
        Path(__file__).parent.parent / "src" / "blackblaze_backup" / "__init__.py"
    )

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            version = data.get("project", {}).get("version", "1.0.0")

        # Read current __init__.py
        with open(init_path) as f:
            content = f.read()

        # Update version line
        import re

        pattern = r'__version__ = "[^"]*"'
        replacement = f'__version__ = "{version}"'
        new_content = re.sub(pattern, replacement, content)

        # Write back if changed
        if new_content != content:
            with open(init_path, "w") as f:
                f.write(new_content)
            print(f"Updated __init__.py version to {version}")
        else:
            print(f"Version {version} already up to date")

    except Exception as e:
        print(f"Error syncing version: {e}")


if __name__ == "__main__":
    sync_version()
