#!/usr/bin/env python3
"""
BlackBlaze B2 Backup Tool - GUI Layer
Uses the core business logic for testable architecture
"""

import importlib.metadata
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


class PreviewWorker(QThread):
    """Worker thread for handling preview analysis"""

    preview_completed = Signal(
        list, list, int, int
    )  # files_to_upload, files_to_skip, total_upload_size, total_skip_size
    preview_failed = Signal(str)

    def __init__(self, backup_service, incremental_enabled):
        super().__init__()
        self.backup_service = backup_service
        self.incremental_enabled = incremental_enabled

    def run(self):
        """Execute the preview analysis"""
        try:
            # Get credentials and S3 client
            credentials = self.backup_service.credential_manager.load_credentials()
            if not credentials:
                raise Exception("No saved credentials found")

            s3_client = self.backup_service.backup_manager.create_s3_client(credentials)

            # Get backup plan
            backup_plan = self.backup_service.config.get_backup_plan()

            files_to_upload = []
            files_to_skip = []
            total_upload_size = 0
            total_skip_size = 0

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
                                self.incremental_enabled,
                            )
                        )

                        file_size = file_path.stat().st_size

                        if should_upload:
                            files_to_upload.append(file_path.name)
                            total_upload_size += file_size
                        else:
                            files_to_skip.append(file_path.name)
                            total_skip_size += file_size

                except Exception:  # nosec B112
                    # Log error but continue with other folders
                    continue

            # Emit completion signal
            self.preview_completed.emit(
                files_to_upload, files_to_skip, total_upload_size, total_skip_size
            )

        except Exception as e:
            self.preview_failed.emit(str(e))


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
        self.backup_service = BackupService()
        self.backup_worker = None
        self.tray_icon = None
        self.schedule_timer = None
        self.schedule_config = None
        self.auto_save_timer = None
        self.is_backup_running = False  # Track backup state
        self.progress_animation_timer = None  # Timer for progress animation

        try:
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

            # Debug: Log icon setup
            icon_path = Path(__file__).parent / "icon.png"
            if icon_path.exists():
                self.logger.info(f"Window icon loaded from {icon_path}")
            else:
                self.logger.warning(f"Icon file not found at {icon_path}")

            self.update_schedule_status()
            self.setup_auto_save()
            self.setup_single_instance_listener()
            self.setup_signal_handler()
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
                # Format the message with timestamp using the UI formatter
                from datetime import datetime

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                msg = f"{timestamp} - {record.getMessage()}"
                # Debug: print to console to verify this is being called
                print(f"UI Handler called: {msg}")
                # Use QTimer.singleShot for thread safety
                from PySide6.QtCore import QTimer

                def append_to_ui():
                    self.text_widget.append(msg)
                    # Auto-scroll to bottom to show latest messages
                    cursor = self.text_widget.textCursor()
                    cursor.movePosition(cursor.MoveOperation.End)
                    self.text_widget.setTextCursor(cursor)

                QTimer.singleShot(0, append_to_ui)

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

        # Ensure UI handler is added to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(ui_handler)
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

    def get_version(self):
        """Get the current application version dynamically"""
        try:
            # Method 1: Try to get version from package metadata (works when installed)
            version = importlib.metadata.version("blackblaze-backup-tool")
            return version
        except importlib.metadata.PackageNotFoundError:
            pass

        try:
            # Method 2: Try to read from pyproject.toml (works in development)
            pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
            if pyproject_path.exists():
                import tomllib

                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                    version = data.get("project", {}).get("version", "Unknown")
                    if version != "Unknown":
                        return version
        except Exception:  # nosec B110
            pass

        try:
            # Method 3: Try to read from __init__.py version attribute
            from blackblaze_backup import __version__

            return __version__
        except (ImportError, AttributeError):
            pass

        try:
            # Method 4: Try to read from setup.py or similar
            setup_path = Path(__file__).parent.parent.parent / "setup.py"
            if setup_path.exists():
                with open(setup_path) as f:
                    content = f.read()
                    import re

                    version_match = re.search(
                        r'version\s*=\s*["\']([^"\']+)["\']', content
                    )
                    if version_match:
                        return version_match.group(1)
        except Exception:  # nosec B110
            pass

        # Fallback: return a default version (this should rarely be used)
        return "Unknown"

    def setup_ui(self):
        """Setup the user interface"""
        version = self.get_version()
        self.setWindowTitle(f"BlackBlaze B2 Backup Tool v{version}")
        self.setGeometry(100, 100, 650, 700)

        # Force window to be visible from the start
        self.setVisible(True)

        # Set proper window class for Ubuntu/Unity icon recognition
        self.setObjectName("BlackBlazeBackupTool")
        self.setProperty("class", "BlackBlazeBackupTool")

        # Set window icon (try both PNG and ICO for better compatibility)
        icon_path_png = Path(__file__).parent / "icon.png"
        icon_path_ico = Path(__file__).parent / "icon.ico"

        if icon_path_ico.exists():
            # Try ICO first for better Windows/Linux compatibility
            ico_icon = QIcon(str(icon_path_ico))
            self.setWindowIcon(ico_icon)
            print(f"DEBUG: Window icon set from ICO {icon_path_ico}")
        elif icon_path_png.exists():
            # Fallback to PNG
            original_pixmap = QPixmap(str(icon_path_png))
            # Scale to 64x64 for better visibility in taskbar/dock
            scaled_pixmap = original_pixmap.scaled(
                64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            large_icon = QIcon(scaled_pixmap)
            self.setWindowIcon(large_icon)
            print(
                f"DEBUG: Window icon set from PNG {icon_path_png}, size: {original_pixmap.size()}"
            )
        else:
            print("DEBUG: No icon files found")

        # Additional Unity/Linux compatibility - set window properties
        try:
            import os

            if os.environ.get("XDG_CURRENT_DESKTOP") == "Unity":
                # For Unity, try to set additional window properties
                # Remove the WindowStaysOnTopHint as it might cause issues
                print("DEBUG: Applied Unity-specific window properties")
        except Exception as e:
            print(f"DEBUG: Unity compatibility setup failed: {e}")

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

        # Add status bar with version info
        version = self.get_version()
        self.statusBar().showMessage(f"Ready - Version {version}")

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
        self.add_folder_btn = QPushButton("Add Folder")
        self.add_folder_btn.clicked.connect(self.add_folder)
        folder_layout.addWidget(self.add_folder_btn)

        # Folder tree
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderLabels(["Folder Path", "Target Bucket"])
        folder_layout.addWidget(self.folder_tree)

        # Remove folder button
        self.remove_folder_btn = QPushButton("Remove Selected Folder")
        self.remove_folder_btn.clicked.connect(self.remove_folder)
        folder_layout.addWidget(self.remove_folder_btn)

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

    def show_version_info(self):
        """Show version information in the log text area"""
        version = self.get_version()

        # Get additional system info
        import platform

        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        version_info = f"""
=== VERSION INFORMATION ===
BlackBlaze B2 Backup Tool
Version: {version}
Python: {python_version}
Platform: {platform.system()} {platform.release()}
Architecture: {platform.machine()}
Built with PySide6 for cross-platform compatibility
===============================

"""

        # Add version info to the log text area
        self.log_text.append(version_info)

        # Log it as well
        self.logger.info(f"Version info displayed: {version}")

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

        # Add version info button
        self.version_info_btn = QPushButton("ℹ️")
        self.version_info_btn.setToolTip("Show version information")
        self.version_info_btn.setMaximumWidth(30)
        self.version_info_btn.clicked.connect(self.show_version_info)
        controls_layout.addWidget(self.version_info_btn)

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

        # Progress bar (starts inactive, becomes indeterminate during backup)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)  # Normal mode by default
        self.progress_bar.setValue(0)  # Start at 0
        self.progress_bar.setFormat("")  # No text format
        # Ensure the progress bar shows activity on all platforms
        self.progress_bar.setVisible(True)
        self.progress_bar.setEnabled(True)
        # Ubuntu-specific styling for better visual appeal
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid #404040;
                border-radius: 8px;
                background-color: #2D2D2D;
                height: 20px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00D4AA, stop: 1 #00A8CC);
                border-radius: 6px;
                margin: 1px;
            }
        """
        )
        layout.addWidget(self.progress_bar)

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

            # Show message if backup is currently running
            if self.is_backup_running:
                folder_name = Path(folder_path).name
                self.logger.info(
                    f"Folder '{folder_name}' added and will be included in the next backup"
                )
                self.statusBar().showMessage(
                    f"Folder '{folder_name}' added - will be backed up in next run",
                    5000,
                )

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
            self.start_backup_immediately(incremental_enabled, is_scheduled=True)
        else:
            # For manual uploads, show preview dialog
            self.show_upload_preview()

    def show_upload_preview(self):
        """Show what files will be uploaded in logs and start backup immediately"""
        # Start preview in background thread to avoid UI hanging
        self.logger.info("Starting backup preview...")
        self.log_text.append("Analyzing files to upload...")

        # Disable start backup button during preview
        self.start_backup_btn.setEnabled(False)
        self.start_backup_btn.setText("Analyzing...")

        # Show progress bar during analysis
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Start preview worker thread
        self.preview_worker = PreviewWorker(
            self.backup_service, self.incremental_backup_check.isChecked()
        )
        self.preview_worker.preview_completed.connect(self.on_preview_completed)
        self.preview_worker.preview_failed.connect(self.on_preview_failed)
        self.preview_worker.start()

    def on_preview_completed(
        self, files_to_upload, files_to_skip, total_upload_size, total_skip_size
    ):
        """Handle completed preview analysis"""
        print(
            f"DEBUG: Preview completed - Upload: {len(files_to_upload)}, Skip: {len(files_to_skip)}"
        )
        self.start_backup_btn.setEnabled(True)
        self.start_backup_btn.setText("Start Backup")

        # Store preview results for display
        self.preview_results = {
            "files_to_upload": files_to_upload,
            "files_to_skip": files_to_skip,
            "total_upload_size": total_upload_size,
            "total_skip_size": total_skip_size,
            "upload_count": len(files_to_upload),
            "skip_count": len(files_to_skip),
        }

        # Show preview results in a dedicated summary area
        preview_text = f"""
=== BACKUP PREVIEW RESULTS ===
Files to upload: {len(files_to_upload)}
Files to skip: {len(files_to_skip)}
Upload size: {self._format_size(total_upload_size)}
Skip size: {self._format_size(total_skip_size)}
===============================

"""

        # Insert preview at the beginning of the log
        current_text = self.log_text.toPlainText()
        self.log_text.setPlainText(preview_text + current_text)

        # Scroll to top to show preview
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        self.log_text.setTextCursor(cursor)

        # Reset progress bar to normal state
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # Start backup immediately after preview
        incremental_enabled = self.incremental_backup_check.isChecked()
        self.start_backup_immediately(incremental_enabled, is_scheduled=False)

    def on_preview_failed(self, error_message):
        """Handle preview analysis failure"""
        print(f"DEBUG: Preview failed: {error_message}")
        self.start_backup_btn.setEnabled(True)
        self.start_backup_btn.setText("Start Backup")
        self.logger.error(f"Preview failed: {error_message}")
        QMessageBox.warning(
            self, "Preview Failed", f"Could not analyze files: {error_message}"
        )

        # Reset progress bar to normal state
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

    def _format_size(self, size_bytes):
        """Format file size in human readable format"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def show_session_summary(self):
        """Show a summary of the current backup session analysis"""
        if not hasattr(self, "preview_results"):
            return

        results = self.preview_results
        summary_text = f"""
CURRENT SESSION SUMMARY:
   • Files to upload: {results["upload_count"]}
   • Files to skip: {results["skip_count"]}
   • Upload size: {self._format_size(results["total_upload_size"])}
   • Skip size: {self._format_size(results["total_skip_size"])}
   • Total files analyzed: {results["upload_count"] + results["skip_count"]}
"""
        self.log_text.append(summary_text)

    def start_backup_immediately(self, incremental_enabled, is_scheduled=False):
        """Start backup immediately after preview confirmation"""
        # Always show preview results if available, regardless of backup type
        preview_section = ""

        # First, try to extract from current log
        current_text = self.log_text.toPlainText()
        if "=== BACKUP PREVIEW RESULTS ===" in current_text:
            # Extract the preview section
            lines = current_text.split("\n")
            preview_lines = []
            in_preview = False

            for line in lines:
                if "=== BACKUP PREVIEW RESULTS ===" in line:
                    in_preview = True
                if in_preview:
                    preview_lines.append(line)
                    if line.strip() == "===============================":
                        break

            if preview_lines:
                preview_section = "\n".join(preview_lines) + "\n\n"
                # Also preserve session summary if it exists
                if "CURRENT SESSION SUMMARY:" in current_text:
                    summary_start = current_text.find("CURRENT SESSION SUMMARY:")
                    if summary_start != -1:
                        summary_end = current_text.find("\n\n", summary_start)
                        if summary_end == -1:
                            summary_end = len(current_text)
                        summary_section = (
                            current_text[summary_start:summary_end] + "\n\n"
                        )
                        preview_section += summary_section

        # If no preview in log, try stored preview results
        if not preview_section and hasattr(self, "preview_results"):
            preview_text = f"""
=== BACKUP PREVIEW RESULTS ===
Files to upload: {self.preview_results["upload_count"]}
Files to skip: {self.preview_results["skip_count"]}
Upload size: {self._format_size(self.preview_results["total_upload_size"])}
Skip size: {self._format_size(self.preview_results["total_skip_size"])}
===============================

"""
            preview_section = preview_text
            # Debug: print to console
            print(
                f"DEBUG: Restoring preview results from stored data: {self.preview_results}"
            )

        # Handle log clearing based on backup type
        if is_scheduled:
            # For scheduled backups, clear log but preserve preview results
            self.log_text.clear()
            if preview_section:
                self.log_text.setPlainText(preview_section)
        else:
            # For manual backups, just add a separator to show backup is starting
            # Don't modify the log text since preview results are already displayed
            self.log_text.append("\n=== STARTING BACKUP ===\n")

            # Show current session summary if available
            if hasattr(self, "preview_results"):
                self.show_session_summary()

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

        # Update UI immediately to show backup is starting
        self.start_backup_btn.setEnabled(False)
        self.cancel_backup_btn.setEnabled(True)
        self.progress_bar.setRange(0, 0)  # Set to indeterminate mode
        # Don't clear log for manual backups since preview results are already displayed
        if is_scheduled:
            self.log_text.clear()
        self.is_backup_running = True  # Set backup running flag

        # Show immediate feedback that backup is starting
        self.logger.info("Starting backup...")
        self.statusBar().showMessage("Starting backup...", 0)

        # Handle folder management based on backup type
        if is_scheduled:
            # For scheduled backups: Allow adding folders with messaging
            self.remove_folder_btn.setEnabled(False)
            self.folder_tree.setEnabled(False)
            self.add_folder_btn.setText("Add Folder (Next Backup)")
        else:
            # For manual backups: Disable all folder management
            self.add_folder_btn.setEnabled(False)
            self.remove_folder_btn.setEnabled(False)
            self.folder_tree.setEnabled(False)

        # Start the backup worker
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

        # Re-enable folder management after cancellation
        self.add_folder_btn.setEnabled(True)
        self.add_folder_btn.setText("Add Folder")  # Restore original text
        self.remove_folder_btn.setEnabled(True)
        self.folder_tree.setEnabled(True)

        # Reset progress bar to normal mode
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # Update status message
        self.statusBar().showMessage("Backup cancelled by user", 5000)
        self.logger.info("Backup cancelled by user")

    def update_progress(self, value):
        """Update progress bar (simplified for better performance)"""
        # For indeterminate progress bar, we don't need to update values
        # The bar will show activity without specific percentages
        pass

    def update_status(self, message):
        """Update status text"""
        self.logger.info(message)

    def handle_error(self, error_message):
        """Handle backup errors"""
        self.logger.error(error_message)

    def backup_finished(self, success):
        """Handle backup completion"""
        self.start_backup_btn.setEnabled(True)
        self.cancel_backup_btn.setEnabled(False)
        self.is_backup_running = False  # Clear backup running flag

        # Re-enable folder management after backup
        self.add_folder_btn.setEnabled(True)
        self.add_folder_btn.setText("Add Folder")  # Restore original text
        self.remove_folder_btn.setEnabled(True)
        self.folder_tree.setEnabled(True)

        # Reset progress bar to normal mode
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        if success:
            # The detailed message will come from the status callback
            # Just show a generic success message in status bar
            self.statusBar().showMessage("Backup completed successfully!", 10000)
            if self.tray_icon:
                self.tray_icon.showMessage(
                    "Backup Complete",
                    "Backup completed successfully!",
                    QSystemTrayIcon.Information,
                    5000,
                )
        else:
            self.statusBar().showMessage(
                "Backup failed. Check the log for details.", 10000
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

        # Windows-specific system tray availability check
        import platform

        if platform.system() == "Windows":
            # On Windows, sometimes the system tray is available but not properly initialized
            # We'll try to create a temporary tray icon to test
            try:
                test_icon = QSystemTrayIcon(self)
                if not test_icon.isSystemTrayAvailable():
                    self.logger.warning("Windows system tray not properly initialized")
                    self.logger.info(
                        "Background operation will use window hiding instead"
                    )
                    self.tray_icon = None
                    return
            except Exception as e:
                self.logger.warning(f"Windows system tray test failed: {e}")
                self.logger.info("Background operation will use window hiding instead")
                self.tray_icon = None
                return

        self.logger.info("Setting up cross-platform system tray icon...")

        # Create cross-platform compatible icon (use PNG for better Windows compatibility)
        icon_path = Path(__file__).parent / "icon.png"
        if icon_path.exists():
            # Create system tray icon with proper Windows compatibility
            original_pixmap = QPixmap(str(icon_path))
            # Windows prefers 16x16 or 32x32 icons for system tray
            # Scale to 32x32 for better Windows compatibility
            scaled_pixmap = original_pixmap.scaled(
                32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            icon = QIcon(scaled_pixmap)
        else:
            # Fallback: Create a simple programmatic icon with 2.5x zoom
            pixmap = QPixmap(32, 32)  # Standard system tray size
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)

            # Draw blue circle with "B2" text (2.5x zoom effect)
            painter.setBrush(QBrush(QColor("#2E86AB")))
            painter.setPen(QPen(QColor("#1E40AF"), 5))  # 2.5x thicker border
            painter.drawEllipse(4, 4, 24, 24)  # 2.5x smaller circle

            painter.setPen(QPen(QColor("white")))
            font = QFont("Arial", 5, QFont.Bold)  # 2.5x smaller font
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

        # Windows-specific system tray icon fixes
        try:
            # Set the icon again to ensure it's properly set
            self.tray_icon.setIcon(icon)

            # For Windows, we need to ensure the icon is visible
            # Try multiple approaches to make it work
            if self.tray_icon.show():
                self.logger.info("System tray icon created successfully")
            else:
                # Windows fallback: try to show again after a short delay
                self.logger.warning(
                    "Initial tray icon show failed, trying Windows-specific fix..."
                )

                # Try setting the icon again and showing
                self.tray_icon.setIcon(icon)
                self.tray_icon.setVisible(True)

                if self.tray_icon.isVisible():
                    self.logger.info(
                        "System tray icon created successfully (Windows fix applied)"
                    )
                else:
                    self.logger.error(
                        "Failed to show system tray icon - show() returned False"
                    )
                    self.logger.info(
                        "Background operation will still work with window hiding"
                    )
                    # Keep tray icon object for menu functionality even if not visible
        except Exception as e:
            self.logger.error(f"Exception while showing system tray icon: {e}")
            self.logger.info("Background operation will still work with window hiding")

    def show_window(self):
        """Show and activate the main window"""
        self.logger.info("Showing window from tray menu")
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

    def force_exit(self):
        """Force exit the application (bypass closeEvent)"""
        self.logger.info("Force exit requested")

        # Clean up single instance lock file
        app = QApplication.instance()
        if hasattr(app, "_instance_lock_file"):
            try:
                app._instance_lock_file.unlink(missing_ok=True)
            except Exception as e:
                self.logger.warning(f"Error cleaning up instance lock file: {e}")

        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()

    def setup_single_instance_listener(self):
        """Setup listener for single instance communication"""
        # This method is kept for compatibility but now uses signals
        pass

    def _bring_to_front(self):
        """Bring the window to the front and focus it"""
        self.logger.info("Bringing window to front")

        # Show the window if it's hidden
        if self.isHidden():
            self.show()

        # Bring to front and focus
        self.raise_()
        self.activateWindow()

        # On some systems, we need to set the window state
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)

    def setup_signal_handler(self):
        """Setup signal handler for single instance communication (Unix only)"""
        import signal

        def signal_handler(signum, frame):
            if hasattr(signal, "SIGUSR1") and signum == signal.SIGUSR1:
                self.logger.info(
                    "Another instance tried to start - bringing window to front"
                )
                self._bring_to_front()

        # Only setup signal handler on Unix systems
        if hasattr(signal, "SIGUSR1"):
            signal.signal(signal.SIGUSR1, signal_handler)

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


def _handle_existing_instance(pid, current_pid):
    """Handle the case where another instance is already running"""
    import logging
    import os
    import signal

    # Send focus signal to existing instance (Unix only)
    try:
        if hasattr(signal, "SIGUSR1"):
            os.kill(pid, signal.SIGUSR1)  # Send signal to existing instance
    except (OSError, ProcessLookupError):
        pass  # Signal failed, but that's okay

    # Log that another instance is running
    logging.info(
        f"Another instance is already running (PID: {pid}), current PID: {current_pid}"
    )

    # Try to bring existing window to focus (Windows-specific)
    try:
        import platform

        if platform.system() == "Windows":
            # Use Windows API to find and activate the existing window
            import ctypes

            # Define Windows constants
            SW_RESTORE = 9

            # Try multiple window finding methods
            hwnd = None

            # Method 1: Find by exact title
            hwnd = ctypes.windll.user32.FindWindowW(None, "BlackBlaze B2 Backup Tool")
            if hwnd:
                logging.info(f"Found window by title (HWND: {hwnd})")
            else:
                # Method 2: Find by Qt class name
                hwnd = ctypes.windll.user32.FindWindowW(
                    "Qt5QWindowIcon", "BlackBlaze B2 Backup Tool"
                )
                if hwnd:
                    logging.info(f"Found window by Qt class (HWND: {hwnd})")
                else:
                    # Method 3: Find by partial title match
                    hwnd = ctypes.windll.user32.FindWindowW(None, "BlackBlaze")
                    if hwnd:
                        logging.info(f"Found window by partial title (HWND: {hwnd})")

            if hwnd:
                # Bring window to front with multiple methods
                try:
                    # Method 1: SetForegroundWindow
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    logging.info("SetForegroundWindow called")

                    # Method 2: ShowWindow with restore
                    ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
                    logging.info("ShowWindow SW_RESTORE called")

                    # Method 3: Bring to top
                    ctypes.windll.user32.BringWindowToTop(hwnd)
                    logging.info("BringWindowToTop called")

                    # Method 4: Set active window
                    ctypes.windll.user32.SetActiveWindow(hwnd)
                    logging.info("SetActiveWindow called")

                    logging.info("Successfully brought existing window to focus")

                except Exception as e:
                    logging.info(f"Error bringing window to focus: {e}")
            else:
                logging.info("Could not find existing window to focus")
    except Exception as e:
        logging.info(f"Could not bring existing window to focus: {e}")

    return False


def _ensure_single_instance(app):
    """Ensure only one instance of the application is running.

    Returns True if this is the first instance, False if another instance is already running.
    If another instance is running, it will be brought to focus and this instance will exit.
    """
    import os
    import tempfile
    from pathlib import Path

    current_pid = os.getpid()
    logging.info(f"Single instance check started (PID: {current_pid})")

    # Create a unique lock file for this application
    lock_name = "blackblaze_backup_tool_single_instance.lock"
    temp_dir = Path(tempfile.gettempdir())
    lock_file = temp_dir / lock_name

    # Log the lock file path for debugging
    logging.info(
        f"Checking single instance lock file: {lock_file} (PID: {current_pid})"
    )

    # Ensure temp directory exists (Windows-specific)
    try:
        temp_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logging.info(f"Could not create temp directory: {e}")

    # Atomic lock file creation with retry mechanism
    max_retries = 3
    retry_delay = 0.1  # 100ms delay between retries

    for attempt in range(max_retries):
        logging.info(
            f"Single instance check attempt {attempt + 1}/{max_retries} (PID: {current_pid})"
        )

        # Check if lock file exists
        if lock_file.exists():
            logging.info(
                f"Lock file exists, checking if process is still running (PID: {current_pid})"
            )
            try:
                # Read the PID from the lock file
                with open(lock_file) as f:
                    pid = int(f.read().strip())

                logging.info(
                    f"Found lock file with PID: {pid}, checking if process is still running"
                )

                # Check if the process is still running
                try:
                    import platform

                    if platform.system() == "Windows":
                        # Windows-specific process check
                        import subprocess

                        try:
                            # Use tasklist to check if process is running
                            result = subprocess.run(
                                ["tasklist", "/FI", f"PID eq {pid}"],
                                capture_output=True,
                                text=True,
                                check=False,
                            )
                            logging.info(
                                f"Tasklist result for PID {pid}: {result.stdout}"
                            )
                            if str(pid) not in result.stdout:
                                # Process not found, remove stale lock file
                                logging.info(
                                    f"Process {pid} not found in tasklist, removing stale lock file (PID: {current_pid})"
                                )
                                lock_file.unlink(missing_ok=True)
                                # Continue to lock file creation below
                            else:
                                logging.info(
                                    f"Process {pid} is still running, another instance exists"
                                )
                                # Process is still running, handle existing instance
                                return _handle_existing_instance(pid, current_pid)
                        except Exception as e:
                            logging.info(f"Error checking process with tasklist: {e}")
                            # Fallback to os.kill
                            try:
                                os.kill(pid, 0)
                                # Process is still running, handle existing instance
                                return _handle_existing_instance(pid, current_pid)
                            except (OSError, ProcessLookupError):
                                # Process doesn't exist, remove stale lock file
                                logging.info(
                                    f"Process {pid} not found via os.kill, removing stale lock file"
                                )
                                lock_file.unlink(missing_ok=True)

                        # Additional check: Look for any BlackBlaze processes running
                        try:
                            result = subprocess.run(
                                [
                                    "tasklist",
                                    "/FI",
                                    "IMAGENAME eq BlackBlaze-Backup-Tool.exe",
                                ],
                                capture_output=True,
                                text=True,
                                check=False,
                            )
                            logging.info(f"All BlackBlaze processes: {result.stdout}")
                            # If we find other BlackBlaze processes, treat as existing instance
                            if (
                                "BlackBlaze-Backup-Tool.exe" in result.stdout
                                and str(current_pid) not in result.stdout
                            ):
                                logging.info(
                                    "Found other BlackBlaze processes running, treating as existing instance"
                                )
                                return _handle_existing_instance(pid, current_pid)
                        except Exception as e:
                            logging.info(
                                f"Error checking for BlackBlaze processes: {e}"
                            )
                    else:
                        # Unix/Linux process check
                        try:
                            os.kill(
                                pid, 0
                            )  # This will raise an exception if process doesn't exist
                            # Process is still running, handle existing instance
                            return _handle_existing_instance(pid, current_pid)
                        except (OSError, ProcessLookupError):
                            # Process doesn't exist, remove stale lock file
                            logging.info(
                                f"Process {pid} not found via os.kill, removing stale lock file"
                            )
                            lock_file.unlink(missing_ok=True)
                except Exception as e:
                    logging.info(f"Error checking process: {e}")
                    # Continue to lock file creation below

            except (ValueError, FileNotFoundError):
                # Invalid lock file, remove it
                logging.info(
                    f"Invalid lock file found, removing it (PID: {current_pid})"
                )
                lock_file.unlink(missing_ok=True)

    # No lock file exists, create one atomically with retry mechanism
    logging.info(f"No lock file found, creating new one (PID: {current_pid})")

    # Try to create lock file atomically with retry mechanism
    max_retries = 3
    retry_delay = 0.1  # 100ms delay between retries

    for attempt in range(max_retries):
        try:
            # Use atomic file creation with exclusive lock
            with open(
                lock_file, "x"
            ) as f:  # 'x' mode creates file exclusively, fails if exists
                f.write(str(current_pid))
                f.flush()
                os.fsync(f.fileno())  # Force write to disk

            logging.info(
                f"Lock file created atomically on attempt {attempt + 1} (PID: {current_pid})"
            )

            # Store the lock file path for cleanup
            app._instance_lock_file = lock_file

            # Verify lock file was created successfully
            if lock_file.exists():
                logging.info(f"Lock file verification successful (PID: {current_pid})")
                return True
            else:
                logging.error(
                    f"Lock file verification failed - file not found after creation (PID: {current_pid})"
                )
                return True  # Continue anyway

        except FileExistsError:
            # Lock file was created by another instance between our check and creation
            logging.info(
                f"Lock file created by another instance during attempt {attempt + 1} (PID: {current_pid})"
            )
            if attempt < max_retries - 1:
                import time

                time.sleep(retry_delay)
                continue
            else:
                # Final attempt failed, another instance exists
                logging.info(
                    f"All retry attempts failed, another instance exists (PID: {current_pid})"
                )
                return False

        except Exception as e:
            logging.error(
                f"Error creating lock file on attempt {attempt + 1}: {e} (PID: {current_pid})"
            )
            if attempt < max_retries - 1:
                import time

                time.sleep(retry_delay)
                continue
            else:
                logging.error(
                    f"All retry attempts failed, continuing anyway (PID: {current_pid})"
                )
                return True  # Continue anyway

    # If we get here, all retries failed
    logging.error(
        f"Failed to create lock file after {max_retries} attempts (PID: {current_pid})"
    )
    return True  # Continue anyway


def setup_logging():
    """Setup logging configuration"""
    from .config import config

    log_file_path = config.log_file
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file_path), logging.StreamHandler()],
    )


def main():
    """Main application entry point"""
    setup_logging()

    # Log startup with PID
    import os

    current_pid = os.getpid()
    logging.info(f"BlackBlaze B2 Backup Tool started (PID: {current_pid})")

    app = QApplication(sys.argv)

    # Get dynamic version
    try:
        from . import __version__

        dynamic_version = __version__
    except ImportError:
        dynamic_version = "Unknown"

    # Set application properties
    app.setApplicationName("BlackBlaze B2 Backup Tool")
    app.setApplicationVersion(dynamic_version)
    app.setOrganizationName("BlackBlaze Backup")

    # Single instance check
    logging.info(f"Checking single instance protection (PID: {current_pid})")
    single_instance_result = _ensure_single_instance(app)
    logging.info(
        f"Single instance check result: {single_instance_result} (PID: {current_pid})"
    )
    if not single_instance_result:
        logging.info(f"Another instance is running, exiting (PID: {current_pid})")
        return 0  # Exit gracefully if another instance is already running

    logging.info(f"Single instance check passed, continuing (PID: {current_pid})")

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
            logging.info("Signal handler setup for single instance communication")

        window.show()

        # Start event loop
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"Error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
