#!/usr/bin/env python3
"""
BlackBlaze B2 Backup Tool - GUI Layer
Uses the core business logic for testable architecture
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QLineEdit, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QCheckBox, QComboBox, QProgressBar, QMessageBox, QFileDialog,
    QSplitter, QTabWidget, QFormLayout, QSpinBox, QFrame, QSystemTrayIcon,
    QMenu, QDialog, QDialogButtonBox, QTimeEdit, QCalendarWidget
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QTime
from PySide6.QtGui import QFont, QIcon, QPixmap, QAction

from .core import BackupService


class ScheduleDialog(QDialog):
    """Dialog for setting up scheduled backups"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Schedule Automatic Backups")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Enable scheduled backups
        self.enable_schedule = QCheckBox("Enable automatic backups")
        layout.addWidget(self.enable_schedule)
        
        # Schedule settings
        schedule_group = QGroupBox("Schedule Settings")
        schedule_layout = QFormLayout(schedule_group)
        
        # Backup frequency
        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems([
            "Daily", "Every 2 days", "Weekly", "Every 2 weeks", "Monthly"
        ])
        schedule_layout.addRow("Frequency:", self.frequency_combo)
        
        # Backup time
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime(2, 0))  # Default to 2:00 AM
        schedule_layout.addRow("Time:", self.time_edit)
        
        # Run in background
        self.run_background = QCheckBox("Run in background (minimize to system tray)")
        self.run_background.setChecked(True)
        schedule_layout.addRow("", self.run_background)
        
        layout.addWidget(schedule_group)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_schedule_config(self):
        """Get the schedule configuration"""
        frequency_map = {
            "Daily": 24,
            "Every 2 days": 48,
            "Weekly": 168,
            "Every 2 weeks": 336,
            "Monthly": 720
        }
        
        return {
            "enabled": self.enable_schedule.isChecked(),
            "interval_hours": frequency_map[self.frequency_combo.currentText()],
            "time": self.time_edit.time().toString("hh:mm"),
            "run_background": self.run_background.isChecked()
        }


class BackupWorker(QThread):
    """Worker thread for handling backup operations"""
    progress_updated = Signal(int)
    status_updated = Signal(str)
    error_occurred = Signal(str)
    backup_completed = Signal(bool)
    
    def __init__(self, backup_service: BackupService):
        super().__init__()
        self.backup_service = backup_service
    
    def run(self):
        """Execute the backup process"""
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
    
    def cancel(self):
        """Cancel the backup operation"""
        self.backup_service.cancel_backup()


class BlackBlazeBackupApp(QMainWindow):
    """Main application window for BlackBlaze B2 Backup Tool"""
    
    def __init__(self):
        super().__init__()
        self.backup_service = BackupService()
        self.backup_worker = None
        self.tray_icon = None
        self.schedule_timer = None
        self.schedule_config = None
        self.setup_ui()
        self.setup_logging()
        self.setup_system_tray()
        self.load_schedule_config()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('blackblaze_backup.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("BlackBlaze B2 Backup Tool")
        self.setGeometry(100, 100, 1000, 700)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Create tabs
        self.setup_credentials_tab(tab_widget)
        self.setup_folders_tab(tab_widget)
        self.setup_backup_tab(tab_widget)
        
        # Add status bar
        self.statusBar().showMessage("Ready")
    
    def setup_credentials_tab(self, tab_widget):
        """Setup credentials configuration tab"""
        credentials_widget = QWidget()
        layout = QVBoxLayout(credentials_widget)
        
        # Credentials group
        cred_group = QGroupBox("BackBlaze B2 S3 Credentials")
        cred_layout = QFormLayout(cred_group)
        
        # Endpoint
        self.endpoint_edit = QLineEdit()
        self.endpoint_edit.setPlaceholderText("s3.us-west-001.backblazeb2.com")
        cred_layout.addRow("S3 Endpoint:", self.endpoint_edit)
        
        # Access Key
        self.access_key_edit = QLineEdit()
        self.access_key_edit.setEchoMode(QLineEdit.Password)
        self.access_key_edit.setPlaceholderText("Your Application Key ID")
        cred_layout.addRow("Access Key ID:", self.access_key_edit)
        
        # Secret Key
        self.secret_key_edit = QLineEdit()
        self.secret_key_edit.setEchoMode(QLineEdit.Password)
        self.secret_key_edit.setPlaceholderText("Your Application Key")
        cred_layout.addRow("Secret Access Key:", self.secret_key_edit)
        
        # Region
        self.region_edit = QLineEdit()
        self.region_edit.setPlaceholderText("us-west-001")
        cred_layout.addRow("Region:", self.region_edit)
        
        layout.addWidget(cred_group)
        
        # Test connection button
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self.test_connection)
        layout.addWidget(test_btn)
        
        # Save credentials button
        save_btn = QPushButton("Save Credentials")
        save_btn.clicked.connect(self.save_credentials)
        layout.addWidget(save_btn)
        
        # Load saved credentials
        load_btn = QPushButton("Load Saved Credentials")
        load_btn.clicked.connect(self.load_credentials)
        layout.addWidget(load_btn)
        
        layout.addStretch()
        tab_widget.addTab(credentials_widget, "Credentials")
    
    def setup_folders_tab(self, tab_widget):
        """Setup folder selection tab"""
        folders_widget = QWidget()
        layout = QVBoxLayout(folders_widget)
        
        # Folder selection group
        folder_group = QGroupBox("Select Folders to Backup")
        folder_layout = QVBoxLayout(folder_group)
        
        # Add folder button
        add_folder_btn = QPushButton("Add Folder")
        add_folder_btn.clicked.connect(self.add_folder)
        folder_layout.addWidget(add_folder_btn)
        
        # Folder tree
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderLabels(["Folder Path", "Target Bucket"])
        folder_layout.addWidget(self.folder_tree)
        
        # Remove folder button
        remove_folder_btn = QPushButton("Remove Selected Folder")
        remove_folder_btn.clicked.connect(self.remove_folder)
        folder_layout.addWidget(remove_folder_btn)
        
        layout.addWidget(folder_group)
        
        # Bucket configuration group
        bucket_group = QGroupBox("Bucket Configuration")
        bucket_layout = QVBoxLayout(bucket_group)
        
        # Single bucket option
        self.single_bucket_check = QCheckBox("Use single bucket for all folders")
        self.single_bucket_check.toggled.connect(self.toggle_bucket_mode)
        bucket_layout.addWidget(self.single_bucket_check)
        
        # Single bucket input
        single_bucket_layout = QHBoxLayout()
        single_bucket_layout.addWidget(QLabel("Bucket Name:"))
        self.single_bucket_edit = QLineEdit()
        self.single_bucket_edit.setPlaceholderText("my-backup-bucket")
        single_bucket_layout.addWidget(self.single_bucket_edit)
        bucket_layout.addLayout(single_bucket_layout)
        
        layout.addWidget(bucket_group)
        layout.addStretch()
        
        tab_widget.addTab(folders_widget, "Folders")
    
    def setup_backup_tab(self, tab_widget):
        """Setup backup execution tab"""
        backup_widget = QWidget()
        layout = QVBoxLayout(backup_widget)
        
        # Backup controls
        controls_layout = QHBoxLayout()
        
        self.start_backup_btn = QPushButton("Start Backup")
        self.start_backup_btn.clicked.connect(self.start_backup)
        controls_layout.addWidget(self.start_backup_btn)
        
        self.cancel_backup_btn = QPushButton("Cancel Backup")
        self.cancel_backup_btn.clicked.connect(self.cancel_backup)
        self.cancel_backup_btn.setEnabled(False)
        controls_layout.addWidget(self.cancel_backup_btn)
        
        # Schedule button
        schedule_btn = QPushButton("Schedule Automatic Backups")
        schedule_btn.clicked.connect(self.show_schedule_dialog)
        controls_layout.addWidget(schedule_btn)
        
        layout.addLayout(controls_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(200)
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)
        
        # Log text
        log_group = QGroupBox("Backup Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        tab_widget.addTab(backup_widget, "Backup")
    
    def add_folder(self):
        """Add a folder to the backup list"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder to Backup")
        if folder_path:
            # Create tree item
            item = QTreeWidgetItem(self.folder_tree)
            item.setText(0, folder_path)
            
            # Add bucket selection if not using single bucket
            if not self.single_bucket_check.isChecked():
                bucket_name = f"backup-{Path(folder_path).name.lower()}"
                item.setText(1, bucket_name)
                # Make bucket name editable
                item.setFlags(item.flags() | Qt.ItemIsEditable)
            
            self.folder_tree.addTopLevelItem(item)
            
            # Update backup service
            bucket_name = item.text(1) if not self.single_bucket_check.isChecked() else ""
            self.backup_service.add_folder_to_backup(folder_path, bucket_name)
    
    def remove_folder(self):
        """Remove selected folder from backup list"""
        current_item = self.folder_tree.currentItem()
        if current_item:
            folder_path = current_item.text(0)
            self.backup_service.remove_folder_from_backup(folder_path)
            self.folder_tree.takeTopLevelItem(self.folder_tree.indexOfTopLevelItem(current_item))
    
    def toggle_bucket_mode(self, checked):
        """Toggle between single and multiple bucket modes"""
        if checked:
            # Single bucket mode - clear bucket names
            for i in range(self.folder_tree.topLevelItemCount()):
                item = self.folder_tree.topLevelItem(i)
                item.setText(1, "")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        else:
            # Multiple bucket mode - make bucket names editable
            for i in range(self.folder_tree.topLevelItemCount()):
                item = self.folder_tree.topLevelItem(i)
                folder_name = Path(item.text(0)).name.lower()
                item.setText(1, f"backup-{folder_name}")
                item.setFlags(item.flags() | Qt.ItemIsEditable)
        
        # Update backup service
        self.backup_service.configure_bucket_mode(checked, self.single_bucket_edit.text())
    
    def test_connection(self):
        """Test connection to BackBlaze B2"""
        credentials = {
            'endpoint': self.endpoint_edit.text(),
            'access_key': self.access_key_edit.text(),
            'secret_key': self.secret_key_edit.text(),
            'region': self.region_edit.text()
        }
        
        is_valid, message = self.backup_service.set_credentials(credentials)
        
        if is_valid:
            QMessageBox.information(self, "Connection Test", message)
            self.logger.info("Connection test successful")
        else:
            QMessageBox.critical(self, "Connection Test Failed", message)
            self.logger.error(f"Connection test failed: {message}")
    
    def save_credentials(self):
        """Save credentials securely"""
        credentials = {
            'endpoint': self.endpoint_edit.text(),
            'access_key': self.access_key_edit.text(),
            'secret_key': self.secret_key_edit.text(),
            'region': self.region_edit.text()
        }
        
        success = self.backup_service.credential_manager.save_credentials(credentials)
        
        if success:
            QMessageBox.information(self, "Credentials Saved", "Credentials saved securely!")
        else:
            QMessageBox.critical(self, "Save Failed", "Error saving credentials")
    
    def load_credentials(self):
        """Load saved credentials"""
        credentials = self.backup_service.credential_manager.load_credentials()
        
        if credentials:
            # Populate fields
            self.endpoint_edit.setText(credentials['endpoint'])
            self.access_key_edit.setText(credentials['access_key'])
            self.secret_key_edit.setText(credentials['secret_key'])
            self.region_edit.setText(credentials['region'])
            
            QMessageBox.information(self, "Credentials Loaded", "Credentials loaded successfully!")
        else:
            QMessageBox.warning(self, "No Saved Credentials", "No saved credentials found.")
    
    def start_backup(self):
        """Start the backup process"""
        # Validate credentials
        if not all([self.endpoint_edit.text(), self.access_key_edit.text(), 
                   self.secret_key_edit.text(), self.region_edit.text()]):
            QMessageBox.warning(self, "Missing Credentials", "Please configure your credentials first.")
            return
        
        # Update backup service configuration
        self.backup_service.configure_bucket_mode(
            self.single_bucket_check.isChecked(),
            self.single_bucket_edit.text()
        )
        
        # Validate backup configuration
        is_valid, message = self.backup_service.validate_backup_config()
        if not is_valid:
            QMessageBox.warning(self, "Invalid Configuration", message)
            return
        
        # Start backup worker
        self.backup_worker = BackupWorker(self.backup_service)
        self.backup_worker.progress_updated.connect(self.update_progress)
        self.backup_worker.status_updated.connect(self.update_status)
        self.backup_worker.error_occurred.connect(self.handle_error)
        self.backup_worker.backup_completed.connect(self.backup_finished)
        
        self.start_backup_btn.setEnabled(False)
        self.cancel_backup_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_text.clear()
        self.log_text.clear()
        
        self.backup_worker.start()
    
    def cancel_backup(self):
        """Cancel the backup process"""
        if self.backup_worker and self.backup_worker.isRunning():
            self.backup_worker.cancel()
            self.backup_worker.wait()
    
    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)
    
    def update_status(self, message):
        """Update status text"""
        self.status_text.append(message)
        self.logger.info(message)
    
    def handle_error(self, error_message):
        """Handle backup errors"""
        self.status_text.append(f"ERROR: {error_message}")
        self.logger.error(error_message)
    
    def backup_finished(self, success):
        """Handle backup completion"""
        self.start_backup_btn.setEnabled(True)
        self.cancel_backup_btn.setEnabled(False)
        
        if success:
            QMessageBox.information(self, "Backup Complete", "Backup completed successfully!")
            if self.tray_icon:
                self.tray_icon.showMessage(
                    "Backup Complete",
                    "Backup completed successfully!",
                    QSystemTrayIcon.Information,
                    5000
                )
        else:
            QMessageBox.warning(self, "Backup Failed", "Backup failed. Check the log for details.")
            if self.tray_icon:
                self.tray_icon.showMessage(
                    "Backup Failed",
                    "Backup failed. Check logs for details.",
                    QSystemTrayIcon.Critical,
                    5000
                )
    
    def setup_system_tray(self):
        """Setup system tray icon"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        # Create a simple icon
        pixmap = QPixmap(32, 32)
        pixmap.fill("blue")
        icon = QIcon(pixmap)
        
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("BlackBlaze B2 Backup Tool")
        
        # Create context menu
        menu = QMenu()
        
        # Show/Hide window action
        self.show_action = menu.addAction("Show Window")
        self.show_action.triggered.connect(self.show)
        
        # Start backup action
        start_backup_action = menu.addAction("Start Backup Now")
        start_backup_action.triggered.connect(self.start_backup)
        
        # Schedule action
        schedule_action = menu.addAction("Schedule Backups")
        schedule_action.triggered.connect(self.show_schedule_dialog)
        
        menu.addSeparator()
        
        # Exit action
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.quit)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
    
    def tray_icon_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()
    
    def show_schedule_dialog(self):
        """Show schedule dialog"""
        dialog = ScheduleDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.schedule_config = dialog.get_schedule_config()
            self.save_schedule_config()
            self.setup_schedule_timer()
            
            if self.schedule_config.get('run_background', False):
                QMessageBox.information(
                    self, 
                    "Background Mode", 
                    "Scheduled backups will run in the background.\n"
                    "You can minimize the window to system tray."
                )
    
    def load_schedule_config(self):
        """Load schedule configuration from file"""
        try:
            config_file = Path.home() / ".blackblaze_backup" / "schedule.json"
            if config_file.exists():
                import json
                with open(config_file, 'r') as f:
                    self.schedule_config = json.load(f)
                self.setup_schedule_timer()
        except Exception as e:
            self.logger.error(f"Error loading schedule config: {e}")
    
    def save_schedule_config(self):
        """Save schedule configuration to file"""
        try:
            config_file = Path.home() / ".blackblaze_backup" / "schedule.json"
            config_file.parent.mkdir(exist_ok=True)
            
            import json
            with open(config_file, 'w') as f:
                json.dump(self.schedule_config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving schedule config: {e}")
    
    def setup_schedule_timer(self):
        """Setup scheduled backup timer"""
        if self.schedule_timer:
            self.schedule_timer.stop()
        
        if not self.schedule_config or not self.schedule_config.get('enabled', False):
            return
        
        # Check every minute for scheduled backups
        self.schedule_timer = QTimer()
        self.schedule_timer.timeout.connect(self.check_scheduled_backup)
        self.schedule_timer.start(60000)  # 1 minute
        
        self.logger.info("Scheduled backups enabled")
    
    def check_scheduled_backup(self):
        """Check if it's time for a scheduled backup"""
        if not self.schedule_config or not self.schedule_config.get('enabled', False):
            return
        
        # Simple time-based scheduling (you can enhance this)
        import datetime
        now = datetime.datetime.now()
        scheduled_time = datetime.datetime.strptime(
            self.schedule_config.get('time', '02:00'), 
            '%H:%M'
        ).time()
        
        # Check if it's the right time (within 1 minute)
        if abs((now.time().hour * 60 + now.time().minute) - 
               (scheduled_time.hour * 60 + scheduled_time.minute)) <= 1:
            
            # Check if we haven't run recently (within the interval)
            last_run_file = Path.home() / ".blackblaze_backup" / "last_backup"
            if last_run_file.exists():
                last_run = datetime.datetime.fromtimestamp(last_run_file.stat().st_mtime)
                interval_hours = self.schedule_config.get('interval_hours', 24)
                if (now - last_run).total_seconds() < interval_hours * 3600:
                    return
            
            # Start scheduled backup
            self.logger.info("Starting scheduled backup")
            self.start_backup()
            
            # Update last run time
            last_run_file.touch()
    
    def closeEvent(self, event):
        """Handle application close event"""
        if self.tray_icon and self.tray_icon.isVisible():
            if self.schedule_config and self.schedule_config.get('run_background', False):
                # Hide to tray instead of closing
                self.hide()
                self.tray_icon.showMessage(
                    "Running in Background",
                    "BlackBlaze Backup is running in the background.\n"
                    "Double-click the tray icon to show the window.",
                    QSystemTrayIcon.Information,
                    5000
                )
                event.ignore()
            else:
                # Ask user if they want to close or minimize to tray
                reply = QMessageBox.question(
                    self, 
                    "Exit Application",
                    "Do you want to exit the application or minimize to system tray?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.No:
                    self.hide()
                    self.tray_icon.showMessage(
                        "Minimized to Tray",
                        "BlackBlaze Backup is running in the background.",
                        QSystemTrayIcon.Information,
                        3000
                    )
                    event.ignore()
                else:
                    event.accept()
        else:
            event.accept()


def main():
    """Main application entry point"""
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
