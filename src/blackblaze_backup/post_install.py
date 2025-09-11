#!/usr/bin/env python3
"""
Post-install script to set up desktop entry and icon for Ubuntu/Unity
"""

import shutil
import subprocess  # nosec B404
from pathlib import Path


def install_desktop_entry():
    """Install desktop entry and icon for the application (idempotent)"""
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

        # Copy desktop entry (only if needed)
        desktop_source = package_dir / "blackblaze-backup-tool.desktop"
        desktop_target = desktop_dir / "blackblaze-backup-tool.desktop"

        needs_update = False

        if desktop_source.exists():
            if (
                not desktop_target.exists()
                or desktop_source.stat().st_mtime > desktop_target.stat().st_mtime
            ):
                shutil.copy2(desktop_source, desktop_target)
                print(f"Installed desktop entry: {desktop_target}")
                needs_update = True

        # Copy icon (only if needed)
        icon_source = package_dir / "icon.png"
        icon_target = icon_dir / "blackblaze-backup-tool.png"

        if icon_source.exists():
            if (
                not icon_target.exists()
                or icon_source.stat().st_mtime > icon_target.stat().st_mtime
            ):
                shutil.copy2(icon_source, icon_target)
                print(f"Installed icon: {icon_target}")
                needs_update = True

        # Only update databases if something changed
        if needs_update:
            # Update desktop database
            try:
                subprocess.run(  # nosec B603, B607
                    ["update-desktop-database", str(desktop_dir)],
                    check=True,
                    capture_output=True,
                )
                print("Updated desktop database")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("Warning: Could not update desktop database")

            # Update icon cache
            try:
                subprocess.run(  # nosec B603, B607
                    ["gtk-update-icon-cache", "-f", "-t", str(icon_dir.parent)],
                    check=True,
                    capture_output=True,
                )
                print("Updated icon cache")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("Warning: Could not update icon cache")

            print("Desktop integration completed successfully!")
        # else: silently skip if nothing needs updating

    except Exception as e:
        print(f"Warning: Could not install desktop integration: {e}")


if __name__ == "__main__":
    install_desktop_entry()
