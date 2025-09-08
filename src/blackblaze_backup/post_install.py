#!/usr/bin/env python3
"""
Post-install script to set up desktop entry and icon for Ubuntu/Unity
"""

import shutil
import subprocess
from pathlib import Path


def install_desktop_entry():
    """Install desktop entry and icon for the application"""
    try:
        # Get the package installation directory
        import blackblaze_backup

        package_dir = Path(blackblaze_backup.__file__).parent

        # Paths for installation
        desktop_dir = Path.home() / ".local" / "share" / "applications"
        icon_dir = (
            Path.home() / ".local" / "share" / "icons" / "hicolor" / "256x256" / "apps"
        )

        # Create directories if they don't exist
        desktop_dir.mkdir(parents=True, exist_ok=True)
        icon_dir.mkdir(parents=True, exist_ok=True)

        # Copy desktop entry
        desktop_source = package_dir / "blackblaze-backup-tool.desktop"
        desktop_target = desktop_dir / "blackblaze-backup-tool.desktop"

        if desktop_source.exists():
            shutil.copy2(desktop_source, desktop_target)
            print(f"Installed desktop entry: {desktop_target}")

        # Copy icon
        icon_source = package_dir / "icon.png"
        icon_target = icon_dir / "blackblaze-backup-tool.png"

        if icon_source.exists():
            shutil.copy2(icon_source, icon_target)
            print(f"Installed icon: {icon_target}")

        # Update desktop database
        try:
            subprocess.run(
                ["update-desktop-database", str(desktop_dir)],
                check=True,
                capture_output=True,
            )
            print("Updated desktop database")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Warning: Could not update desktop database")

        # Update icon cache
        try:
            subprocess.run(
                ["gtk-update-icon-cache", "-f", "-t", str(icon_dir.parent)],
                check=True,
                capture_output=True,
            )
            print("Updated icon cache")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Warning: Could not update icon cache")

        print("Desktop integration completed successfully!")

    except Exception as e:
        print(f"Warning: Could not install desktop integration: {e}")


if __name__ == "__main__":
    install_desktop_entry()
