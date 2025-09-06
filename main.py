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
    setup_logging()
    
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("BlackBlaze B2 Backup Tool")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("BlackBlaze Backup")
    
    # Create and show main window
    window = BlackBlazeBackupApp()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()