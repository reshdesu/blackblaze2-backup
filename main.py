#!/usr/bin/env python3
"""
BlackBlaze B2 Backup Tool - Main Entry Point
"""

import logging
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PySide6.QtWidgets import QApplication

from blackblaze_backup.gui import BlackBlazeBackupApp


def setup_logging():
    """Setup logging configuration"""
    from blackblaze_backup.config import config

    # Use config directory for log file (user-accessible location)
    log_file_path = config.log_file

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file_path), logging.StreamHandler()],
    )


def main():
    """Main application entry point"""
    import os
    import subprocess

    # Kill any existing instances before starting
    try:
        # Find and kill existing bb2backup processes
        result = subprocess.run(
            ["pgrep", "-f", "bb2backup"], capture_output=True, text=True
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                if pid and pid != str(os.getpid()):  # Don't kill ourselves
                    try:
                        subprocess.run(["kill", pid], check=True)
                        print(f"Killed existing bb2backup process (PID: {pid})")
                    except subprocess.CalledProcessError:
                        pass  # Process might have already exited
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass  # pgrep or kill commands not available, continue anyway

    setup_logging()

    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("BlackBlaze B2 Backup Tool")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("BlackBlaze Backup")

    # Create and show main window
    try:
        window = BlackBlazeBackupApp()

        # Ensure window is visible on Windows
        window.show()
        window.raise_()
        window.activateWindow()

        logging.info("Main window created and shown")

        # Start event loop
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"Error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
