#!/usr/bin/env python3
"""
BlackBlaze B2 Backup Tool - Main Entry Point
"""

import sys
import logging
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent / "src"))

from blackblaze_backup.gui import BlackBlazeBackupApp
from PySide6.QtWidgets import QApplication


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('blackblaze_backup.log'),
            logging.StreamHandler()
        ]
    )


def main():
    """Main application entry point"""
    import subprocess
    import os
    
    # Kill any existing instances before starting
    try:
        # Find and kill existing bb2backup processes
        result = subprocess.run(['pgrep', '-f', 'bb2backup'], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid and pid != str(os.getpid()):  # Don't kill ourselves
                    try:
                        subprocess.run(['kill', pid], check=True)
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
        window.show()
        
        # Start event loop
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"Error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()