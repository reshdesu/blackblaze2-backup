#!/usr/bin/env python3
"""
BlackBlaze B2 Backup Tool - GUI Layer
Uses the core business logic for testable architecture
"""

import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTime, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSystemTrayIcon,
    QTabWidget,
    QTextEdit,
    QTimeEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .core import BackupService


class ScheduleDialog(QDialog):
    """Dialog for setting up scheduled backups"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Schedule Automatic Backups")
        self.setModal(True)
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        # Schedule settings
        schedule_group = QGroupBox("Schedule Settings")
        schedule_layout = QFormLayout(schedule_group)

        # Backup frequency
        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(
            [
                "Every 1 minute",
                "Every 5 minutes",
                "Every 15 minutes",
                "Hourly",
                "Daily",
                "Every 2 days",
                "Weekly",
                "Every 2 weeks",
                "Monthly",
            ]
        )
        self.frequency_combo.currentTextChanged.connect(self.on_frequency_changed)
        schedule_layout.addRow("Frequency:", self.frequency_combo)

        # Backup time
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime(2, 0))  # Default to 2:00 AM
        self.time_label = QLabel("Time:")
        schedule_layout.addRow(self.time_label, self.time_edit)

        layout.addWidget(schedule_group)

        # Initialize the frequency change handler
        self.on_frequency_changed(self.frequency_combo.currentText())

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def on_frequency_changed(self, frequency):
        """Handle frequency selection change"""
        if frequency in [
            "Hourly",
            "Every 1 minute",
            "Every 5 minutes",
            "Every 15 minutes",
        ]:
            # Hide time selection for frequent backups
            self.time_label.hide()
            self.time_edit.hide()
        else:
            # Show time selection for other frequencies
            self.time_label.show()
            self.time_edit.show()

    def get_schedule_config(self):
        """Get the schedule configuration"""
        frequency_map = {
            "Every 1 minute": 0.017,  # 1 minute = 1/60 hours
            "Every 5 minutes": 0.083,  # 5 minutes = 5/60 hours
            "Every 15 minutes": 0.25,  # 15 minutes = 15/60 hours
            "Hourly": 1,
            "Daily": 24,
            "Every 2 days": 48,
            "Weekly": 168,
            "Every 2 weeks": 336,
            "Monthly": 720,
        }

        return {
            "enabled": True,  # Always enabled since we removed the checkbox
            "interval_hours": frequency_map[self.frequency_combo.currentText()],
            "time": (
                self.time_edit.time().toString("hh:mm")
                if self.frequency_combo.currentText()
                not in [
                    "Hourly",
                    "Every 1 minute",
                    "Every 5 minutes",
                    "Every 15 minutes",
                ]
                else None
            ),
            "run_background": True,  # Always run in background since app always minimizes
        }


class BackupWorker(QThread):
    """Worker thread for handling backup operations"""

    progress_updated = Signal(int)
    status_updated = Signal(str)
    error_occurred = Signal(str)
    backup_completed = Signal(bool)

    def __init__(self, backup_service: BackupService, incremental: bool = True):
        super().__init__()
        self.backup_service = backup_service
        self.incremental = incremental

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
            error_callback=error_callback,
            incremental=self.incremental,
        )

        self.backup_completed.emit(success)

    def cancel(self):
        """Cancel the backup operation"""
        self.backup_service.cancel_backup()


class BlackBlazeBackupApp(QMainWindow):
    """Main application window for BlackBlaze B2 Backup Tool"""

    def __init__(self):
        super().__init__()
        try:
            self.backup_service = BackupService()
            self.backup_worker = None
            self.tray_icon = None
            self.schedule_timer = None
            self.schedule_config = None
            self.auto_save_timer = None
            self.is_backup_running = False  # Track backup state

            self.setup_ui()
            self.setup_logging()
            self.setup_system_tray()
            self.toggle_bucket_mode(True)  # Initialize single bucket mode
            self.load_credentials_automatically()  # Auto-load saved credentials
            self.load_schedule_config()
            self.load_folder_config()
            self.load_incremental_backup_setting()  # Load incremental backup setting

            # Debug: Log window state
            self.logger.info(
                f"Window created - Visible: {self.isVisible()}, Geometry: {self.geometry()}"
            )
            self.update_schedule_status()
            self.setup_auto_save()
        except Exception as e:
            logging.error(f"Error initializing application: {e}")
            raise

    def setup_logging(self):
        """Setup logging configuration"""
        from .config import config

        # Use config directory for log file (user-accessible location)
        log_file_path = config.log_file

        # Custom handler for UI log display
        class UILogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget

            def emit(self, record):
                msg = self.format(record)
                # Use QMetaObject.invokeMethod to ensure thread safety
                from PySide6.QtCore import QMetaObject, Qt

                QMetaObject.invokeMethod(
                    self.text_widget, "append", Qt.QueuedConnection, msg
                )

        # Create handlers
        file_handler = logging.FileHandler(log_file_path)
        stream_handler = logging.StreamHandler()
        ui_handler = UILogHandler(self.log_text)

        # Set format
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        ui_formatter = logging.Formatter(
            "%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)
        ui_handler.setFormatter(ui_formatter)

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            handlers=[file_handler, stream_handler, ui_handler],
        )
        self.logger = logging.getLogger(__name__)

        # Add initial log message
        self.logger.info("BlackBlaze B2 Backup Tool started")
        self.logger.info(f"Log file location: {log_file_path}")

    def setup_auto_save(self):
        """Setup automatic saving of configuration"""
        # Auto-save every 30 seconds
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save_config)
        self.auto_save_timer.start(30000)  # 30 seconds

        # Update credentials status
        self.update_credentials_status()

    def auto_save_config(self):
        """Automatically save configuration"""
        try:
            # Save folder configuration
            self.save_folder_config()
            # Save schedule configuration
            if self.schedule_config:
                self.save_schedule_config()
            # Save incremental backup setting
            self.save_incremental_backup_setting()
        except Exception as e:
            self.logger.error(f"Error in auto-save: {e}")

    def save_incremental_backup_setting(self):
        """Save incremental backup setting to file"""
        try:
            config_dir = Path.home() / ".blackblaze_backup"
            config_dir.mkdir(exist_ok=True)

            config_file = config_dir / "incremental_backup.json"
            import json

            config = {
                "incremental_backup_enabled": self.incremental_backup_check.isChecked()
            }

            with open(config_file, "w") as f:
                json.dump(config, f)

        except Exception as e:
            self.logger.error(f"Error saving incremental backup setting: {e}")

    def load_incremental_backup_setting(self):
        """Load incremental backup setting from file"""
        try:
            config_file = Path.home() / ".blackblaze_backup" / "incremental_backup.json"
            if config_file.exists():
                import json

                with open(config_file) as f:
                    config = json.load(f)
                    self.incremental_backup_check.setChecked(
                        config.get("incremental_backup_enabled", True)
                    )
        except Exception as e:
            self.logger.error(f"Error loading incremental backup setting: {e}")
            # Default to enabled if loading fails
            self.incremental_backup_check.setChecked(True)

    def update_credentials_status(self):
        """Update credentials status display"""
        credentials = self.backup_service.credential_manager.load_credentials()
        if credentials:
            self.credentials_status.setText(" Credentials saved securely")
            self.credentials_status.setStyleSheet("color: #2E7D32; font-weight: bold;")
        else:
            self.credentials_status.setText("No credentials saved")
            self.credentials_status.setStyleSheet("color: #666; font-style: italic;")

    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("BlackBlaze B2 Backup Tool")
        self.setGeometry(100, 100, 650, 700)

        # Set window icon (use PNG for better cross-platform compatibility)
        icon_path = Path(__file__).parent / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

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

        # Credentials status
        self.credentials_status = QLabel("No credentials saved")
        self.credentials_status.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.credentials_status)

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
        self.single_bucket_check.setChecked(True)  # Default to single bucket mode
        self.single_bucket_check.toggled.connect(self.toggle_bucket_mode)
        bucket_layout.addWidget(self.single_bucket_check)

        # Single bucket input
        single_bucket_layout = QHBoxLayout()
        single_bucket_layout.addWidget(QLabel("Bucket Name:"))
        self.single_bucket_edit = QLineEdit()
        self.single_bucket_edit.setPlaceholderText("my-backup-bucket")
        self.single_bucket_edit.setText(
            "blackblaze2-backup-testing"
        )  # Default bucket name
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

        # Disable schedule button
        self.disable_schedule_btn = QPushButton("Disable Automatic Backups")
        self.disable_schedule_btn.clicked.connect(self.disable_schedule)
        self.disable_schedule_btn.setEnabled(False)  # Initially disabled
        controls_layout.addWidget(self.disable_schedule_btn)

        layout.addLayout(controls_layout)

        # Backup options
        options_group = QGroupBox("Backup Options")
        options_layout = QVBoxLayout(options_group)

        # Incremental backup checkbox
        self.incremental_backup_check = QCheckBox(
            "Enable incremental backup (only upload changed files)"
        )
        self.incremental_backup_check.setChecked(True)  # Default to enabled
        self.incremental_backup_check.setToolTip(
            "When enabled, only files that have changed will be uploaded, making backups faster and more efficient."
        )
        options_layout.addWidget(self.incremental_backup_check)

        layout.addWidget(options_group)

        # Schedule status display
        self.schedule_status = QLabel("No scheduled backups configured")
        self.schedule_status.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.schedule_status)

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
            if self.single_bucket_check.isChecked():
                bucket_name = self.single_bucket_edit.text()
            else:
                bucket_name = item.text(1)
            self.backup_service.add_folder_to_backup(folder_path, bucket_name)

            # Auto-save folder configuration
            self.save_folder_config()

    def remove_folder(self):
        """Remove selected folder from backup list"""
        current_item = self.folder_tree.currentItem()
        if current_item:
            folder_path = current_item.text(0)
            self.backup_service.remove_folder_from_backup(folder_path)
            self.folder_tree.takeTopLevelItem(
                self.folder_tree.indexOfTopLevelItem(current_item)
            )

            # Auto-save folder configuration
            self.save_folder_config()

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
        self.backup_service.configure_bucket_mode(
            checked, self.single_bucket_edit.text()
        )

        # Auto-save folder configuration
        self.save_folder_config()

    def test_connection(self):
        """Test connection to BackBlaze B2"""
        credentials = {
            "endpoint": self.endpoint_edit.text().strip(),
            "access_key": self.access_key_edit.text().strip(),
            "secret_key": self.secret_key_edit.text().strip(),
            "region": self.region_edit.text().strip(),
        }

        is_valid, message = self.backup_service.set_credentials(credentials)

        if is_valid:
            QMessageBox.information(self, "Connection Test", message)
            self.logger.info("Connection test successful")
        else:
            QMessageBox.critical(self, "Connection Test Failed", message)
            self.logger.error(f"Connection test failed: {message}")

    def save_credentials(self, silent=False):
        """Save credentials securely"""
        credentials = {
            "endpoint": self.endpoint_edit.text().strip(),
            "access_key": self.access_key_edit.text().strip(),
            "secret_key": self.secret_key_edit.text().strip(),
            "region": self.region_edit.text().strip(),
        }

        # Validate credentials before saving
        is_valid, message = self.backup_service.credential_manager.validate_credentials(
            credentials
        )
        if not is_valid:
            if not silent:
                QMessageBox.critical(
                    self,
                    "Invalid Credentials",
                    f"Cannot save credentials: {message}",
                )
            return False

        success = self.backup_service.credential_manager.save_credentials(credentials)

        if success:
            if not silent:
                QMessageBox.information(
                    self, "Credentials Saved", "Credentials saved securely!"
                )
            # Auto-save folder configuration when credentials are saved
            self.save_folder_config()
            # Update credentials status
            self.update_credentials_status()
            return True
        else:
            if not silent:
                QMessageBox.critical(self, "Save Failed", "Error saving credentials")
            return False

    def load_credentials(self):
        """Load saved credentials"""
        credentials = self.backup_service.credential_manager.load_credentials()

        if credentials:
            # Populate fields
            self.endpoint_edit.setText(credentials["endpoint"])
            self.access_key_edit.setText(credentials["access_key"])
            self.secret_key_edit.setText(credentials["secret_key"])
            self.region_edit.setText(credentials["region"])

            QMessageBox.information(
                self, "Credentials Loaded", "Credentials loaded successfully!"
            )
        else:
            QMessageBox.warning(
                self, "No Saved Credentials", "No saved credentials found."
            )

    def start_backup(self, is_scheduled=False):
        """Start the backup process with preview (only for manual uploads)"""
        # Validate credentials
        if not all(
            [
                self.endpoint_edit.text(),
                self.access_key_edit.text(),
                self.secret_key_edit.text(),
                self.region_edit.text(),
            ]
        ):
            QMessageBox.warning(
                self,
                "Missing Credentials",
                "Please configure your credentials first.",
            )
            return

        # Update backup service configuration
        self.backup_service.configure_bucket_mode(
            self.single_bucket_check.isChecked(),
            self.single_bucket_edit.text(),
        )

        # Validate backup configuration
        is_valid, message = self.backup_service.validate_backup_config()
        if not is_valid:
            QMessageBox.warning(self, "Invalid Configuration", message)
            return

        # Show upload preview only for manual uploads, not scheduled backups
        if is_scheduled:
            # For scheduled backups, start immediately without preview
            incremental_enabled = self.incremental_backup_check.isChecked()
            self.start_backup_immediately(incremental_enabled)
        else:
            # For manual uploads, show preview dialog
            self.show_upload_preview()

    def show_upload_preview(self):
        """Show what files will be uploaded in logs and start backup immediately"""
        try:
            # Get credentials and S3 client
            credentials = self.backup_service.credential_manager.load_credentials()
            if not credentials:
                self.logger.error("No saved credentials found")
                QMessageBox.warning(
                    self, "No Credentials", "No saved credentials found."
                )
                return

            s3_client = self.backup_service.backup_manager.create_s3_client(credentials)

            # Get backup plan
            backup_plan = self.backup_service.config.get_backup_plan()

            files_to_upload = []
            files_to_skip = []
            total_upload_size = 0
            total_skip_size = 0

            incremental_enabled = self.incremental_backup_check.isChecked()

            # Quick analysis of what will be uploaded
            for folder_path, bucket_name in backup_plan.items():
                try:
                    files = self.backup_service.backup_manager.get_files_to_backup(
                        folder_path
                    )
                    folder_path_obj = Path(folder_path)

                    for file_path in files:
                        s3_key = self.backup_service.backup_manager.calculate_s3_key(
                            file_path, folder_path_obj
                        )

                        should_upload = (
                            self.backup_service.backup_manager.should_upload_file(
                                s3_client,
                                file_path,
                                bucket_name,
                                s3_key,
                                incremental_enabled,
                            )
                        )

                        file_size = file_path.stat().st_size

                        if should_upload:
                            files_to_upload.append(file_path.name)
                            total_upload_size += file_size
                        else:
                            files_to_skip.append(file_path.name)
                            total_skip_size += file_size

                except Exception as e:
                    self.logger.warning(f"Error analyzing folder {folder_path}: {e}")
                    continue

            # Log upload preview information
            from .utils import format_file_size

            upload_count = len(files_to_upload)
            skip_count = len(files_to_skip)
            upload_size_str = format_file_size(total_upload_size)
            skip_size_str = format_file_size(total_skip_size)

            mode = "Incremental" if incremental_enabled else "Full"

            if upload_count == 0:
                self.logger.info(
                    f"Upload Analysis Complete - All files up to date! "
                    f"Mode: {mode}, Files to skip: {skip_count} ({skip_size_str})"
                )
                # Still start the backup process even if no files need uploading
                self.start_backup_immediately(incremental_enabled)
                return

            # Log detailed upload preview
            self.logger.info(
                f"Upload Analysis Complete - {mode} Mode: "
                f"{upload_count} files to upload ({upload_size_str}), "
                f"{skip_count} files to skip ({skip_size_str})"
            )

            # Log first few files to upload for visibility
            if files_to_upload:
                sample_files = files_to_upload[:5]  # Show first 5 files
                self.logger.info(f"Sample files to upload: {', '.join(sample_files)}")
                if len(files_to_upload) > 5:
                    self.logger.info(f"... and {len(files_to_upload) - 5} more files")

            # Start backup immediately without popup
            self.start_backup_immediately(incremental_enabled)

        except Exception as e:
            self.logger.error(f"Error in upload preview: {e}")
            QMessageBox.critical(
                self, "Preview Error", f"Failed to analyze files:\n{str(e)}"
            )

    def start_backup_immediately(self, incremental_enabled):
        """Start backup immediately after preview confirmation"""
        # Clear log display for new backup
        self.log_text.clear()

        # Reset cancellation state for new backup
        self.backup_service.reset_cancellation()

        # Start backup worker with incremental setting
        self.backup_worker = BackupWorker(
            self.backup_service, incremental=incremental_enabled
        )
        self.backup_worker.progress_updated.connect(self.update_progress)
        self.backup_worker.status_updated.connect(self.update_status)
        self.backup_worker.error_occurred.connect(self.handle_error)
        self.backup_worker.backup_completed.connect(self.backup_finished)

        self.start_backup_btn.setEnabled(False)
        self.cancel_backup_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_text.clear()
        self.log_text.clear()
        self.is_backup_running = True  # Set backup running flag

        self.backup_worker.start()

    def cancel_backup(self):
        """Cancel the backup process"""
        if self.backup_worker and self.backup_worker.isRunning():
            self.backup_worker.cancel()
            self.backup_worker.wait()

        # Reset UI state after cancellation
        self.start_backup_btn.setEnabled(True)
        self.cancel_backup_btn.setEnabled(False)
        self.is_backup_running = False  # Clear backup running flag

        # Update status message
        self.statusBar().showMessage("Backup cancelled by user", 5000)
        self.logger.info("Backup cancelled by user")

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
        self.is_backup_running = False  # Clear backup running flag

        if success:
            self.statusBar().showMessage(" Backup completed successfully!", 10000)
            if self.tray_icon:
                self.tray_icon.showMessage(
                    "Backup Complete",
                    "Backup completed successfully!",
                    QSystemTrayIcon.Information,
                    5000,
                )
        else:
            self.statusBar().showMessage(
                " Backup failed. Check the log for details.", 10000
            )
            if self.tray_icon:
                self.tray_icon.showMessage(
                    "Backup Failed",
                    "Backup failed. Check logs for details.",
                    QSystemTrayIcon.Critical,
                    5000,
                )

    def setup_system_tray(self):
        """Setup system tray icon - cross-platform solution for Windows 11 and Ubuntu"""
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.logger.warning("System tray is not available on this system")
            self.logger.info("Background operation will use window hiding instead")
            self.tray_icon = None
            return

        self.logger.info("Setting up cross-platform system tray icon...")

        # Create cross-platform compatible icon (use PNG for better Windows compatibility)
        icon_path = Path(__file__).parent / "icon.png"
        if icon_path.exists():
            # Use PNG icon (works better on Windows)
            icon = QIcon(str(icon_path))
        else:
            # Fallback: Create a simple programmatic icon
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)

            # Draw blue circle with "B2" text
            painter.setBrush(QBrush(QColor("#2E86AB")))
            painter.setPen(QPen(QColor("#1E40AF"), 2))
            painter.drawEllipse(2, 2, 28, 28)

            painter.setPen(QPen(QColor("white")))
            font = QFont("Arial", 12, QFont.Bold)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "B2")
            painter.end()

            icon = QIcon(pixmap)

        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("BlackBlaze B2 Backup Tool")

        # Create context menu
        menu = QMenu()

        # Show/Hide window action
        self.show_action = menu.addAction("Show Window")
        self.show_action.triggered.connect(self.show_window)

        # Start backup action
        start_backup_action = menu.addAction("Start Backup Now")
        start_backup_action.triggered.connect(self.start_backup)

        # Schedule action
        schedule_action = menu.addAction("Schedule Backups")
        schedule_action.triggered.connect(self.show_schedule_dialog)

        menu.addSeparator()

        # Exit action
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.force_exit)

        self.tray_icon.setContextMenu(menu)

        # Try to show the tray icon
        if self.tray_icon.show():
            self.logger.info("System tray icon created successfully")
        else:
            self.logger.error("Failed to show system tray icon")
            self.logger.info("Background operation will still work with window hiding")
            # Keep tray icon object for menu functionality even if not visible

    def show_window(self):
        """Show and activate the main window"""
        self.logger.info("Showing window from tray menu")
        self.show()
        self.raise_()
        self.activateWindow()

    def force_exit(self):
        """Force exit the application (bypass closeEvent)"""
        self.logger.info("Force exit requested from tray menu")
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()

    def show_schedule_dialog(self):
        """Show schedule dialog"""
        dialog = ScheduleDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.schedule_config = dialog.get_schedule_config()
            self.save_schedule_config()
            self.setup_schedule_timer()

    def disable_schedule(self):
        """Disable automatic backups"""
        # Clear schedule config
        self.schedule_config = None

        # Stop the timer
        if self.schedule_timer:
            self.schedule_timer.stop()
            self.schedule_timer = None

        # Update status
        self.update_schedule_status()

        # Save the disabled state
        self.save_schedule_config()

        # Show status message instead of popup
        self.statusBar().showMessage(
            "Automatic backups disabled. You can re-enable them using the Schedule button.",
            5000,
        )

    def load_schedule_config(self):
        """Load schedule configuration from file"""
        try:
            config_file = Path.home() / ".blackblaze_backup" / "schedule.json"
            if config_file.exists():
                import json

                with open(config_file) as f:
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

            with open(config_file, "w") as f:
                json.dump(self.schedule_config, f, indent=2)

            # Update button state after saving schedule
            self.update_schedule_status()
        except Exception as e:
            self.logger.error(f"Error saving schedule config: {e}")

    def load_credentials_automatically(self):
        """Automatically load saved credentials without user interaction"""
        try:
            credentials = self.backup_service.credential_manager.load_credentials()
            if credentials:
                # Populate the credential fields
                self.endpoint_edit.setText(credentials.get("endpoint", ""))
                self.access_key_edit.setText(credentials.get("access_key", ""))
                self.secret_key_edit.setText(credentials.get("secret_key", ""))
                self.region_edit.setText(credentials.get("region", ""))

                # Automatically save credentials to ensure they're current (silent mode)
                self.save_credentials(silent=True)

                self.logger.info("Credentials loaded and saved successfully")
                return True
            else:
                self.logger.info("No saved credentials found")
                return False
        except Exception as e:
            self.logger.error(f"Error loading credentials automatically: {e}")
            return False

    def load_folder_config(self):
        """Load folder configuration from file"""
        try:
            config_file = Path.home() / ".blackblaze_backup" / "folders.json"
            if config_file.exists():
                import json

                with open(config_file) as f:
                    folder_config = json.load(f)

                self.logger.info(f"Loading folder config: {folder_config}")

                # Restore folder selections
                folders = folder_config.get("folders", [])
                self.logger.info(f"Found {len(folders)} saved folders")

                for folder_path, bucket_name in folders:
                    item = QTreeWidgetItem(self.folder_tree)
                    item.setText(0, folder_path)
                    item.setText(1, bucket_name)
                    self.folder_tree.addTopLevelItem(item)

                    # Update backup service
                    self.backup_service.add_folder_to_backup(folder_path, bucket_name)
                    self.logger.info(f"Restored folder: {folder_path} -> {bucket_name}")

                # Restore bucket mode
                single_bucket = folder_config.get("single_bucket", False)
                bucket_name = folder_config.get("single_bucket_name", "")
                self.single_bucket_check.setChecked(single_bucket)
                self.single_bucket_edit.setText(bucket_name)
                self.toggle_bucket_mode(single_bucket)
                self.logger.info(
                    f"Restored bucket mode: single={single_bucket}, name='{bucket_name}'"
                )
            else:
                self.logger.info(
                    "No folder config file found, starting with empty configuration"
                )

        except Exception as e:
            self.logger.error(f"Error loading folder config: {e}")

    def save_folder_config(self):
        """Save folder configuration to file"""
        try:
            config_file = Path.home() / ".blackblaze_backup" / "folders.json"
            config_file.parent.mkdir(exist_ok=True)

            # Collect folder data
            folders = []
            for i in range(self.folder_tree.topLevelItemCount()):
                item = self.folder_tree.topLevelItem(i)
                folder_path = item.text(0)
                if self.single_bucket_check.isChecked():
                    bucket_name = self.single_bucket_edit.text()
                else:
                    bucket_name = item.text(1)
                folders.append([folder_path, bucket_name])

            folder_config = {
                "folders": folders,
                "single_bucket": self.single_bucket_check.isChecked(),
                "single_bucket_name": self.single_bucket_edit.text(),
            }

            # Only save if we have folders or if this is a meaningful change
            # Don't overwrite existing folder data with empty data during startup
            if folders or not config_file.exists():
                import json

                with open(config_file, "w") as f:
                    json.dump(folder_config, f, indent=2)

                self.logger.info(f"Saving folder config: {folder_config}")
                self.logger.info(f"Saved {len(folders)} folders to configuration")
            else:
                self.logger.debug("Skipping save of empty folder config during startup")

        except Exception as e:
            self.logger.error(f"Error saving folder config: {e}")

    def update_schedule_status(self):
        """Update the schedule status display"""
        if not self.schedule_config or not self.schedule_config.get("enabled", False):
            self.schedule_status.setText("No scheduled backups configured")
            self.schedule_status.setStyleSheet("color: #666; font-style: italic;")
            # Disable the disable button when no schedule is active
            self.disable_schedule_btn.setEnabled(False)
            return

        # Enable the disable button when schedule is active
        self.disable_schedule_btn.setEnabled(True)

        frequency = self.schedule_config.get("interval_hours", 24)
        time_str = self.schedule_config.get("time")

        if frequency == 0.017:  # Every 1 minute
            status_text = "Scheduled: Backups every 1 minute"
            status_style = "color: #2E7D32; font-weight: bold;"
        elif frequency == 0.083:  # Every 5 minutes
            status_text = "Scheduled: Backups every 5 minutes"
            status_style = "color: #2E7D32; font-weight: bold;"
        elif frequency == 0.25:  # Every 15 minutes
            status_text = "Scheduled: Backups every 15 minutes"
            status_style = "color: #2E7D32; font-weight: bold;"
        elif frequency == 1:
            status_text = "Scheduled: Hourly backups"
            status_style = "color: #2E7D32; font-weight: bold;"
        elif frequency == 24:
            status_text = f"Scheduled: Daily backups at {time_str}"
            status_style = "color: #2E7D32; font-weight: bold;"
        elif frequency == 48:
            status_text = f"Scheduled: Every 2 days at {time_str}"
            status_style = "color: #2E7D32; font-weight: bold;"
        elif frequency == 168:
            status_text = f"Scheduled: Weekly backups at {time_str}"
            status_style = "color: #2E7D32; font-weight: bold;"
        elif frequency == 336:
            status_text = f"Scheduled: Every 2 weeks at {time_str}"
            status_style = "color: #2E7D32; font-weight: bold;"
        elif frequency == 720:
            status_text = f"Scheduled: Monthly backups at {time_str}"
            status_style = "color: #2E7D32; font-weight: bold;"
        else:
            status_text = f"Scheduled: Every {frequency} hours"
            status_style = "color: #2E7D32; font-weight: bold;"

        self.schedule_status.setText(status_text)
        self.schedule_status.setStyleSheet(status_style)

    def setup_schedule_timer(self):
        """Setup scheduled backup timer"""
        if self.schedule_timer:
            self.schedule_timer.stop()

        if not self.schedule_config or not self.schedule_config.get("enabled", False):
            self.update_schedule_status()
            return

        # Check every minute for scheduled backups
        self.schedule_timer = QTimer()
        self.schedule_timer.timeout.connect(self.check_scheduled_backup)
        self.schedule_timer.start(60000)  # 1 minute

        self.update_schedule_status()
        self.logger.info("Scheduled backups enabled")

    def check_scheduled_backup(self):
        """Check if it's time for a scheduled backup"""
        if not self.schedule_config or not self.schedule_config.get("enabled", False):
            return

        # Check if a backup is already running
        if self.backup_worker and self.backup_worker.isRunning():
            self.logger.info(
                "Skipping scheduled backup - manual backup already in progress"
            )
            return

        # Additional check using backup state flag
        if self.is_backup_running:
            self.logger.info("Skipping scheduled backup - backup already in progress")
            return

        import datetime

        now = datetime.datetime.now()
        interval_hours = self.schedule_config.get("interval_hours", 24)

        # Check if we haven't run recently (within the interval)
        last_run_file = Path.home() / ".blackblaze_backup" / "last_backup"
        if last_run_file.exists():
            last_run = datetime.datetime.fromtimestamp(last_run_file.stat().st_mtime)
            if (now - last_run).total_seconds() < interval_hours * 3600:
                return

        # For frequent backups, run based on interval regardless of time
        if interval_hours <= 1:
            # Start scheduled backup
            if interval_hours == 0.017:  # Every 1 minute
                self.logger.info("Starting scheduled backup (every 1 minute)")
            elif interval_hours == 0.083:  # Every 5 minutes
                self.logger.info("Starting scheduled backup (every 5 minutes)")
            elif interval_hours == 0.25:  # Every 15 minutes
                self.logger.info("Starting scheduled backup (every 15 minutes)")
            else:  # Hourly
                self.logger.info("Starting scheduled hourly backup")
            self.start_backup(is_scheduled=True)
            last_run_file.touch()
            return

        # For other frequencies, check specific time
        scheduled_time_str = self.schedule_config.get("time")
        if scheduled_time_str:
            scheduled_time = datetime.datetime.strptime(
                scheduled_time_str, "%H:%M"
            ).time()

            # Check if it's the right time (within 1 minute)
            if (
                abs(
                    (now.time().hour * 60 + now.time().minute)
                    - (scheduled_time.hour * 60 + scheduled_time.minute)
                )
                <= 1
            ):
                # Start scheduled backup
                self.logger.info("Starting scheduled backup")
                self.start_backup(is_scheduled=True)

                # Update last run time
                last_run_file.touch()

    def closeEvent(self, event):
        """Handle application close event"""
        self.logger.info("Close event triggered")

        if self.tray_icon:
            self.logger.info("System tray is available, minimizing to tray")

            if self.schedule_config and self.schedule_config.get(
                "run_background", False
            ):
                # Hide to tray instead of closing
                self.logger.info("Hiding to tray (scheduled backups enabled)")
                self.hide()
                self.tray_icon.showMessage(
                    "Running in Background",
                    "BlackBlaze Backup is running in the background.\n"
                    "Double-click the tray icon to show the window.",
                    QSystemTrayIcon.Information,
                    5000,
                )
            else:
                # Always minimize to tray
                self.logger.info("Minimizing to tray")
                self.hide()
                self.tray_icon.showMessage(
                    "Minimized to Tray",
                    "BlackBlaze Backup is running in the background.\n"
                    "Right-click the tray icon for options.",
                    QSystemTrayIcon.Information,
                    3000,
                )
            event.ignore()
        else:
            self.logger.info("System tray not available, minimizing to background")

            # Always minimize to background
            self.hide()
            event.ignore()

    def minimize_to_background(self):
        """Minimize application to background (Ubuntu compatible)"""
        self.logger.info("Minimizing to background")

        if self.tray_icon and self.tray_icon.isVisible():
            # Use system tray if available
            self.hide()
            self.tray_icon.showMessage(
                "Minimized to Background",
                "BlackBlaze Backup is running in the background.\n"
                "Right-click the tray icon for options.",
                QSystemTrayIcon.Information,
                3000,
            )
        else:
            # Fallback for systems without system tray
            self.hide()


def main():
    """Main application entry point"""
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
