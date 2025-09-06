#!/usr/bin/env python3
"""
BlackBlaze B2 Backup Tool
A cross-platform GUI application for backing up local folders to BackBlaze B2 S3 buckets.
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import keyring
from cryptography.fernet import Fernet

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QLineEdit, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QCheckBox, QComboBox, QProgressBar, QMessageBox, QFileDialog,
    QSplitter, QTabWidget, QFormLayout, QSpinBox, QFrame
)
from PySide6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmap

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


class BackupWorker(QThread):
    """Worker thread for handling backup operations"""
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    backup_completed = pyqtSignal(bool)
    
    def __init__(self, folders_to_backup: Dict[str, str], credentials: Dict[str, str]):
        super().__init__()
        self.folders_to_backup = folders_to_backup
        self.credentials = credentials
        self.cancelled = False
    
    def run(self):
        """Execute the backup process"""
        try:
            # Initialize S3 client
            s3_client = boto3.client(
                's3',
                endpoint_url=f"https://{self.credentials['endpoint']}",
                aws_access_key_id=self.credentials['access_key'],
                aws_secret_access_key=self.credentials['secret_key'],
                region_name=self.credentials['region']
            )
            
            total_folders = len(self.folders_to_backup)
            completed_folders = 0
            
            for folder_path, bucket_name in self.folders_to_backup.items():
                if self.cancelled:
                    break
                    
                self.status_updated.emit(f"Backing up: {folder_path}")
                
                # Get all files in the folder
                folder_path_obj = Path(folder_path)
                if not folder_path_obj.exists():
                    self.error_occurred.emit(f"Folder not found: {folder_path}")
                    continue
                
                files = list(folder_path_obj.rglob('*'))
                files = [f for f in files if f.is_file()]
                
                total_files = len(files)
                uploaded_files = 0
                
                for file_path in files:
                    if self.cancelled:
                        break
                    
                    try:
                        # Calculate relative path for S3 key
                        relative_path = file_path.relative_to(folder_path_obj)
                        s3_key = str(relative_path).replace('\\', '/')
                        
                        # Upload file
                        s3_client.upload_file(
                            str(file_path),
                            bucket_name,
                            s3_key
                        )
                        
                        uploaded_files += 1
                        progress = int((uploaded_files / total_files) * 100)
                        self.progress_updated.emit(progress)
                        
                    except Exception as e:
                        self.error_occurred.emit(f"Error uploading {file_path}: {str(e)}")
                
                completed_folders += 1
                overall_progress = int((completed_folders / total_folders) * 100)
                self.progress_updated.emit(overall_progress)
            
            if not self.cancelled:
                self.status_updated.emit("Backup completed successfully!")
                self.backup_completed.emit(True)
            else:
                self.status_updated.emit("Backup cancelled")
                self.backup_completed.emit(False)
                
        except Exception as e:
            self.error_occurred.emit(f"Backup failed: {str(e)}")
            self.backup_completed.emit(False)
    
    def cancel(self):
        """Cancel the backup operation"""
        self.cancelled = True


class BlackBlazeBackupApp(QMainWindow):
    """Main application window for BlackBlaze B2 Backup Tool"""
    
    def __init__(self):
        super().__init__()
        self.backup_worker = None
        self.setup_ui()
        self.setup_logging()
        
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
    
    def remove_folder(self):
        """Remove selected folder from backup list"""
        current_item = self.folder_tree.currentItem()
        if current_item:
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
    
    def test_connection(self):
        """Test connection to BackBlaze B2"""
        try:
            s3_client = boto3.client(
                's3',
                endpoint_url=f"https://{self.endpoint_edit.text()}",
                aws_access_key_id=self.access_key_edit.text(),
                aws_secret_access_key=self.secret_key_edit.text(),
                region_name=self.region_edit.text()
            )
            
            # Test by listing buckets
            response = s3_client.list_buckets()
            QMessageBox.information(self, "Connection Test", "Connection successful!")
            self.logger.info("Connection test successful")
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Test Failed", f"Error: {str(e)}")
            self.logger.error(f"Connection test failed: {str(e)}")
    
    def save_credentials(self):
        """Save credentials securely"""
        try:
            # Generate encryption key
            key = Fernet.generate_key()
            cipher_suite = Fernet(key)
            
            credentials = {
                'endpoint': self.endpoint_edit.text(),
                'access_key': self.access_key_edit.text(),
                'secret_key': self.secret_key_edit.text(),
                'region': self.region_edit.text()
            }
            
            # Encrypt credentials
            encrypted_data = cipher_suite.encrypt(json.dumps(credentials).encode())
            
            # Save to keyring
            keyring.set_password("blackblaze_backup", "credentials", encrypted_data.decode())
            keyring.set_password("blackblaze_backup", "key", key.decode())
            
            QMessageBox.information(self, "Credentials Saved", "Credentials saved securely!")
            
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Error saving credentials: {str(e)}")
    
    def load_credentials(self):
        """Load saved credentials"""
        try:
            encrypted_data = keyring.get_password("blackblaze_backup", "credentials")
            key = keyring.get_password("blackblaze_backup", "key")
            
            if not encrypted_data or not key:
                QMessageBox.warning(self, "No Saved Credentials", "No saved credentials found.")
                return
            
            # Decrypt credentials
            cipher_suite = Fernet(key.encode())
            decrypted_data = cipher_suite.decrypt(encrypted_data.encode())
            credentials = json.loads(decrypted_data.decode())
            
            # Populate fields
            self.endpoint_edit.setText(credentials['endpoint'])
            self.access_key_edit.setText(credentials['access_key'])
            self.secret_key_edit.setText(credentials['secret_key'])
            self.region_edit.setText(credentials['region'])
            
            QMessageBox.information(self, "Credentials Loaded", "Credentials loaded successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Load Failed", f"Error loading credentials: {str(e)}")
    
    def start_backup(self):
        """Start the backup process"""
        # Validate credentials
        if not all([self.endpoint_edit.text(), self.access_key_edit.text(), 
                   self.secret_key_edit.text(), self.region_edit.text()]):
            QMessageBox.warning(self, "Missing Credentials", "Please configure your credentials first.")
            return
        
        # Validate folders
        if self.folder_tree.topLevelItemCount() == 0:
            QMessageBox.warning(self, "No Folders", "Please add folders to backup.")
            return
        
        # Prepare folders to backup
        folders_to_backup = {}
        for i in range(self.folder_tree.topLevelItemCount()):
            item = self.folder_tree.topLevelItem(i)
            folder_path = item.text(0)
            
            if self.single_bucket_check.isChecked():
                bucket_name = self.single_bucket_edit.text()
                if not bucket_name:
                    QMessageBox.warning(self, "Missing Bucket", "Please specify a bucket name.")
                    return
            else:
                bucket_name = item.text(1)
                if not bucket_name:
                    QMessageBox.warning(self, "Missing Bucket", f"Please specify a bucket for folder: {folder_path}")
                    return
            
            folders_to_backup[folder_path] = bucket_name
        
        # Prepare credentials
        credentials = {
            'endpoint': self.endpoint_edit.text(),
            'access_key': self.access_key_edit.text(),
            'secret_key': self.secret_key_edit.text(),
            'region': self.region_edit.text()
        }
        
        # Start backup worker
        self.backup_worker = BackupWorker(folders_to_backup, credentials)
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
        else:
            QMessageBox.warning(self, "Backup Failed", "Backup failed. Check the log for details.")


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
