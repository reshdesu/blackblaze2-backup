#!/usr/bin/env python3
"""
BlackBlaze B2 Backup Tool - System Tray Mode
Runs in system tray for background backups
"""

import sys
import json
import time
import threading
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PySide6.QtCore import QTimer, Signal, QObject
from PySide6.QtGui import QIcon, QPixmap

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent / "src"))

from blackblaze_backup.core import BackupService
from blackblaze_backup.gui import BlackBlazeBackupApp


class BackupWorker(QObject):
    """Background backup worker"""
    progress_updated = Signal(int)
    status_updated = Signal(str)
    backup_completed = Signal(bool)
    error_occurred = Signal(str)
    
    def __init__(self, config_file: str):
        super().__init__()
        self.config_file = config_file
        self.backup_service = BackupService()
        self.running = False
    
    def load_config(self) -> Dict:
        """Load backup configuration"""
        with open(self.config_file, 'r') as f:
            return json.load(f)
    
    def run_backup(self):
        """Run backup in background thread"""
        try:
            self.running = True
            config = self.load_config()
            credentials = config.get('credentials', {})
            
            # Set credentials
            is_valid, message = self.backup_service.set_credentials(credentials)
            if not is_valid:
                self.error_occurred.emit(f"Invalid credentials: {message}")
                return
            
            # Configure backup
            if config.get('single_bucket_mode', False):
                self.backup_service.configure_bucket_mode(True, config.get('single_bucket_name', ''))
            else:
                self.backup_service.configure_bucket_mode(False)
            
            # Add folders
            for folder_config in config.get('folders', []):
                folder_path = folder_config['path']
                bucket_name = folder_config.get('bucket', '')
                self.backup_service.add_folder_to_backup(folder_path, bucket_name)
            
            # Execute backup
            def progress_callback(value):
                self.progress_updated.emit(value)
            
            def status_callback(message):
                self.status_updated.emit(message)
            
            def error_callback(message):
                self.error_occurred.emit(message)
            
            success = self.backup_service.execute_backup(
                progress_callback=progress_callback,
                status_callback=status_callback,
                error_callback=error_callback
            )
            
            self.backup_completed.emit(success)
            
        except Exception as e:
            self.error_occurred.emit(f"Backup error: {str(e)}")
        finally:
            self.running = False
    
    def stop_backup(self):
        """Stop the backup process"""
        self.running = False
        self.backup_service.cancel_backup()


class SystemTrayApp(QApplication):
    """System tray application"""
    
    def __init__(self, config_file: str):
        super().__init__(sys.argv)
        
        self.config_file = config_file
        self.tray_icon = None
        self.backup_worker = None
        self.backup_thread = None
        self.last_backup_time = None
        self.backup_timer = None
        
        self.setup_tray_icon()
        self.setup_backup_scheduler()
    
    def setup_tray_icon(self):
        """Setup system tray icon"""
        # Create a simple icon (you can replace this with a real icon)
        pixmap = QPixmap(32, 32)
        pixmap.fill("blue")  # Simple blue square
        
        icon = QIcon(pixmap)
        
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("BlackBlaze B2 Backup Tool")
        
        # Create context menu
        menu = QMenu()
        
        # Show status action
        self.status_action = menu.addAction("Status: Ready")
        self.status_action.setEnabled(False)
        
        menu.addSeparator()
        
        # Start backup action
        self.start_action = menu.addAction("Start Backup")
        self.start_action.triggered.connect(self.start_backup)
        
        # Stop backup action
        self.stop_action = menu.addAction("Stop Backup")
        self.stop_action.triggered.connect(self.stop_backup)
        self.stop_action.setEnabled(False)
        
        menu.addSeparator()
        
        # Open GUI action
        open_gui_action = menu.addAction("Open GUI")
        open_gui_action.triggered.connect(self.open_gui)
        
        # Settings action
        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.show_settings)
        
        menu.addSeparator()
        
        # Exit action
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.quit)
        
        self.tray_icon.setContextMenu(menu)
        
        # Handle tray icon activation
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # Show tray icon
        self.tray_icon.show()
    
    def setup_backup_scheduler(self):
        """Setup automatic backup scheduling"""
        # Check for scheduled backups every minute
        self.backup_timer = QTimer()
        self.backup_timer.timeout.connect(self.check_scheduled_backup)
        self.backup_timer.start(60000)  # Check every minute
    
    def check_scheduled_backup(self):
        """Check if it's time for a scheduled backup"""
        try:
            config = self.load_config()
            schedule = config.get('schedule', {})
            
            if not schedule.get('enabled', False):
                return
            
            interval_hours = schedule.get('interval_hours', 24)
            if not self.last_backup_time:
                self.last_backup_time = time.time()
                return
            
            time_since_last = time.time() - self.last_backup_time
            if time_since_last >= interval_hours * 3600:
                self.start_backup()
                
        except Exception as e:
            print(f"Error checking schedule: {e}")
    
    def load_config(self) -> Dict:
        """Load backup configuration"""
        with open(self.config_file, 'r') as f:
            return json.load(f)
    
    def start_backup(self):
        """Start backup process"""
        if self.backup_worker and self.backup_worker.running:
            return
        
        self.status_action.setText("Status: Starting backup...")
        self.start_action.setEnabled(False)
        self.stop_action.setEnabled(True)
        
        # Create backup worker
        self.backup_worker = BackupWorker(self.config_file)
        self.backup_worker.progress_updated.connect(self.on_progress_updated)
        self.backup_worker.status_updated.connect(self.on_status_updated)
        self.backup_worker.backup_completed.connect(self.on_backup_completed)
        self.backup_worker.error_occurred.connect(self.on_error_occurred)
        
        # Run in separate thread
        self.backup_thread = threading.Thread(target=self.backup_worker.run_backup)
        self.backup_thread.daemon = True
        self.backup_thread.start()
    
    def stop_backup(self):
        """Stop backup process"""
        if self.backup_worker:
            self.backup_worker.stop_backup()
        
        self.status_action.setText("Status: Stopped")
        self.start_action.setEnabled(True)
        self.stop_action.setEnabled(False)
    
    def on_progress_updated(self, value):
        """Handle progress updates"""
        self.status_action.setText(f"Status: Backup {value}%")
    
    def on_status_updated(self, message):
        """Handle status updates"""
        self.status_action.setText(f"Status: {message}")
    
    def on_backup_completed(self, success):
        """Handle backup completion"""
        self.last_backup_time = time.time()
        
        if success:
            self.status_action.setText("Status: Backup completed")
            self.tray_icon.showMessage(
                "Backup Complete",
                "BlackBlaze B2 backup completed successfully",
                QSystemTrayIcon.Information,
                5000
            )
        else:
            self.status_action.setText("Status: Backup failed")
            self.tray_icon.showMessage(
                "Backup Failed",
                "BlackBlaze B2 backup failed. Check logs for details.",
                QSystemTrayIcon.Critical,
                5000
            )
        
        self.start_action.setEnabled(True)
        self.stop_action.setEnabled(False)
    
    def on_error_occurred(self, message):
        """Handle backup errors"""
        self.status_action.setText(f"Status: Error - {message}")
        self.tray_icon.showMessage(
            "Backup Error",
            message,
            QSystemTrayIcon.Critical,
            5000
        )
    
    def tray_icon_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.open_gui()
    
    def open_gui(self):
        """Open the main GUI application"""
        try:
            # Import and run the main GUI
            from blackblaze_backup.gui import BlackBlazeBackupApp
            self.gui_window = BlackBlazeBackupApp()
            self.gui_window.show()
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to open GUI: {str(e)}")
    
    def show_settings(self):
        """Show settings dialog"""
        QMessageBox.information(
            None,
            "Settings",
            f"Configuration file: {self.config_file}\n"
            f"Last backup: {self.last_backup_time or 'Never'}\n"
            f"Status: {self.status_action.text()}"
        )


def main():
    """Main entry point for system tray app"""
    import argparse
    
    parser = argparse.ArgumentParser(description="BlackBlaze B2 Backup Tool - System Tray")
    parser.add_argument('--config', '-c', required=True, help='Path to backup configuration file')
    
    args = parser.parse_args()
    
    # Check if system tray is available
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("System tray is not available on this system")
        return 1
    
    # Create and run application
    app = SystemTrayApp(args.config)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
