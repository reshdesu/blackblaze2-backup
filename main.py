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


def _ensure_single_instance(app):
    """Ensure only one instance of the application is running.

    Returns True if this is the first instance, False if another instance is already running.
    If another instance is running, it will be brought to focus and this instance will exit.
    """
    import os
    import signal
    import tempfile
    from pathlib import Path

    # Create a unique lock file for this application
    lock_name = "blackblaze_backup_tool_single_instance.lock"
    temp_dir = Path(tempfile.gettempdir())
    lock_file = temp_dir / lock_name

    # Check if lock file exists
    if lock_file.exists():
        try:
            # Read the PID from the lock file
            with open(lock_file) as f:
                pid = int(f.read().strip())

            # Check if the process is still running
            try:
                os.kill(pid, 0)  # This will raise an exception if process doesn't exist
                # Process is still running, another instance exists
                # Send focus signal to existing instance (Unix only)
                try:
                    if hasattr(signal, "SIGUSR1"):
                        os.kill(pid, signal.SIGUSR1)  # Send signal to existing instance
                except (OSError, ProcessLookupError):
                    pass  # Signal failed, but that's okay

                return False
            except (OSError, ProcessLookupError):
                # Process doesn't exist, remove stale lock file
                lock_file.unlink(missing_ok=True)

        except (ValueError, FileNotFoundError):
            # Invalid lock file, remove it
            lock_file.unlink(missing_ok=True)

    # Create lock file with current PID
    try:
        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))

        # Store the lock file path for cleanup
        app._instance_lock_file = lock_file

        return True

    except Exception as e:
        print(f"Error creating lock file: {e}")
        return True  # Continue anyway


def main():
    """Main application entry point"""
    setup_logging()

    app = QApplication(sys.argv)

    # Get dynamic version
    try:
        from blackblaze_backup import __version__

        dynamic_version = __version__
    except ImportError:
        dynamic_version = "Unknown"

    # Set application properties
    app.setApplicationName("BlackBlaze B2 Backup Tool")
    app.setApplicationVersion(dynamic_version)
    app.setOrganizationName("BlackBlaze Backup")

    # Single instance check
    if not _ensure_single_instance(app):
        return 0  # Exit gracefully if another instance is already running

    # Create and show main window
    try:
        window = BlackBlazeBackupApp()

        # Setup signal handler for single instance communication (Unix only)
        import signal

        def signal_handler(signum, frame):
            if hasattr(signal, "SIGUSR1") and signum == signal.SIGUSR1:
                logging.info(
                    "Another instance tried to start - bringing window to front"
                )
                window._bring_to_front()

        # Only setup signal handler on Unix systems
        if hasattr(signal, "SIGUSR1"):
            signal.signal(signal.SIGUSR1, signal_handler)

        window.show()

        # Start event loop
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"Error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
