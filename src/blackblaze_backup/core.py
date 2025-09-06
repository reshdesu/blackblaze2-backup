#!/usr/bin/env python3
"""
BlackBlaze B2 Backup Tool - Core Business Logic
Separated from GUI for better testability
"""

import json
import logging
from pathlib import Path
from typing import Optional

import boto3
import keyring
from cryptography.fernet import Fernet


class CredentialManager:
    """Manages secure storage and retrieval of BackBlaze B2 credentials"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def save_credentials(self, credentials: dict[str, str]) -> bool:
        """Save credentials securely to system keyring"""
        try:
            # Generate encryption key
            key = Fernet.generate_key()
            cipher_suite = Fernet(key)

            # Encrypt credentials
            encrypted_data = cipher_suite.encrypt(json.dumps(credentials).encode())

            # Save to keyring
            keyring.set_password(
                "blackblaze_backup", "credentials", encrypted_data.decode()
            )
            keyring.set_password("blackblaze_backup", "key", key.decode())

            self.logger.info("Credentials saved securely")
            return True

        except Exception as e:
            self.logger.error(f"Error saving credentials: {str(e)}")
            return False

    def load_credentials(self) -> Optional[dict[str, str]]:
        """Load credentials from system keyring"""
        try:
            encrypted_data = keyring.get_password("blackblaze_backup", "credentials")
            key = keyring.get_password("blackblaze_backup", "key")

            if not encrypted_data or not key:
                return None

            # Decrypt credentials
            cipher_suite = Fernet(key.encode())
            decrypted_data = cipher_suite.decrypt(encrypted_data.encode())
            credentials = json.loads(decrypted_data.decode())

            self.logger.info("Credentials loaded successfully")
            return credentials

        except Exception as e:
            self.logger.error(f"Error loading credentials: {str(e)}")
            return None

    def validate_credentials(self, credentials: dict[str, str]) -> tuple[bool, str]:
        """Validate credentials by testing connection to BackBlaze B2"""
        try:
            s3_client = boto3.client(
                "s3",
                endpoint_url=f"https://{credentials['endpoint']}",
                aws_access_key_id=credentials["access_key"],
                aws_secret_access_key=credentials["secret_key"],
                region_name=credentials["region"],
            )

            # Test by listing buckets
            s3_client.list_buckets()
            return True, "Connection successful"

        except Exception as e:
            return False, f"Connection failed: {str(e)}"


class BackupManager:
    """Manages backup operations and file processing"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cancelled = False

    def cancel_backup(self):
        """Cancel the current backup operation"""
        self.cancelled = True
        self.logger.info("Backup cancellation requested")

    def get_files_to_backup(self, folder_path: str) -> list[Path]:
        """Get all files in a folder that need to be backed up"""
        folder_path_obj = Path(folder_path)
        if not folder_path_obj.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        files = list(folder_path_obj.rglob("*"))
        return [f for f in files if f.is_file()]

    def calculate_s3_key(self, file_path: Path, base_folder: Path) -> str:
        """Calculate the S3 key for a file based on its relative path"""
        relative_path = file_path.relative_to(base_folder)
        # Create a folder with the same name as the base folder and put files inside it
        folder_name = base_folder.name
        return f"{folder_name}/{relative_path}".replace("\\", "/")

    def should_upload_file(
        self, s3_client, file_path: Path, bucket_name: str, s3_key: str, incremental: bool = True
    ) -> bool:
        """Check if file should be uploaded (incremental backup logic)"""
        # If incremental backup is disabled, always upload
        if not incremental:
            return True
            
        try:
            # Check if file exists in S3
            try:
                response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                s3_size = response.get('ContentLength', 0)
                s3_etag = response.get('ETag', '').strip('"')
                
                # Get local file info
                local_size = file_path.stat().st_size
                
                # If sizes are different, definitely need to upload
                if local_size != s3_size:
                    self.logger.debug(f"File size changed: {file_path.name} ({local_size} vs {s3_size})")
                    return True
                
                # If sizes are same, check hash for more accuracy
                from .utils import get_file_hash
                local_hash = get_file_hash(file_path, "md5")
                
                # S3 ETag is usually MD5 hash for single-part uploads
                if local_hash and s3_etag and local_hash != s3_etag:
                    self.logger.debug(f"File hash changed: {file_path.name}")
                    return True
                
                # File is identical, skip upload
                self.logger.debug(f"Skipping unchanged file: {file_path.name}")
                return False
                
            except s3_client.exceptions.NoSuchKey:
                # File doesn't exist in S3, need to upload
                self.logger.debug(f"New file: {file_path.name}")
                return True
                
        except Exception as e:
            # If we can't check, err on the side of uploading
            self.logger.warning(f"Could not check file status for {file_path.name}: {e}")
            return True

    def upload_file(
        self, s3_client, file_path: Path, bucket_name: str, s3_key: str
    ) -> bool:
        """Upload a single file to S3"""
        try:
            s3_client.upload_file(str(file_path), bucket_name, s3_key)
            return True
        except Exception as e:
            self.logger.error(f"Error uploading {file_path}: {str(e)}")
            return False

    def create_s3_client(self, credentials: dict[str, str]):
        """Create and return an S3 client"""
        return boto3.client(
            "s3",
            endpoint_url=f"https://{credentials['endpoint']}",
            aws_access_key_id=credentials["access_key"],
            aws_secret_access_key=credentials["secret_key"],
            region_name=credentials["region"],
        )


class BackupConfig:
    """Configuration management for backup operations"""

    def __init__(self):
        self.folders_to_backup: dict[str, str] = {}
        self.single_bucket_mode = False
        self.single_bucket_name = ""

    def add_folder(self, folder_path: str, bucket_name: str = ""):
        """Add a folder to backup configuration"""
        self.folders_to_backup[folder_path] = bucket_name

    def remove_folder(self, folder_path: str):
        """Remove a folder from backup configuration"""
        if folder_path in self.folders_to_backup:
            del self.folders_to_backup[folder_path]

    def set_single_bucket_mode(self, enabled: bool, bucket_name: str = ""):
        """Configure single bucket mode"""
        self.single_bucket_mode = enabled
        if enabled:
            self.single_bucket_name = bucket_name

    def get_backup_plan(self) -> dict[str, str]:
        """Get the final backup plan with folder->bucket mappings"""
        if self.single_bucket_mode:
            return dict.fromkeys(self.folders_to_backup.keys(), self.single_bucket_name)
        else:
            return self.folders_to_backup.copy()

    def validate_config(self) -> tuple[bool, str]:
        """Validate the backup configuration"""
        if not self.folders_to_backup:
            return False, "No folders selected for backup"

        if self.single_bucket_mode:
            if not self.single_bucket_name:
                return False, "Single bucket name is required"
        else:
            for folder, bucket in self.folders_to_backup.items():
                if not bucket:
                    return False, f"Bucket name required for folder: {folder}"

        return True, "Configuration is valid"


class BackupProgressTracker:
    """Tracks and reports backup progress"""

    def __init__(self):
        self.total_folders = 0
        self.completed_folders = 0
        self.total_files = 0
        self.completed_files = 0
        self.current_folder = ""
        self.current_file = ""

    def start_backup(self, folders: dict[str, str]):
        """Initialize progress tracking for a backup operation"""
        self.total_folders = len(folders)
        self.completed_folders = 0
        self.total_files = 0
        self.completed_files = 0
        self.current_folder = ""
        self.current_file = ""

    def start_folder(self, folder_path: str, file_count: int):
        """Start processing a new folder"""
        self.current_folder = folder_path
        self.total_files += file_count
        self.completed_files = 0

    def complete_file(self):
        """Mark a file as completed"""
        self.completed_files += 1

    def complete_folder(self):
        """Mark a folder as completed"""
        self.completed_folders += 1

    def get_overall_progress(self) -> int:
        """Get overall backup progress percentage"""
        if self.total_folders == 0:
            return 0

        # If all folders are completed, we're at 100%
        if self.completed_folders >= self.total_folders:
            return 100

        # Calculate progress based on completed folders
        folder_progress = self.completed_folders / self.total_folders

        # Add progress from current folder if we're working on it
        if self.current_folder and self.total_files > 0:
            current_folder_progress = self.completed_files / self.total_files
            folder_progress += current_folder_progress / self.total_folders

        return int(folder_progress * 100)

    def get_folder_progress(self) -> int:
        """Get current folder progress percentage"""
        if self.total_files == 0:
            return 0
        return int((self.completed_files / self.total_files) * 100)

    def get_status_message(self) -> str:
        """Get current status message"""
        if self.current_folder:
            return f"Backing up: {self.current_folder}"
        return "Preparing backup..."


class BackupService:
    """Main service class that orchestrates backup operations"""

    def __init__(self):
        self.credential_manager = CredentialManager()
        self.backup_manager = BackupManager()
        self.config = BackupConfig()
        self.progress_tracker = BackupProgressTracker()
        self.logger = logging.getLogger(__name__)

    def set_credentials(self, credentials: dict[str, str]) -> tuple[bool, str]:
        """Set and validate credentials"""
        is_valid, message = self.credential_manager.validate_credentials(credentials)
        if is_valid:
            self.credential_manager.save_credentials(credentials)
        return is_valid, message

    def add_folder_to_backup(self, folder_path: str, bucket_name: str = ""):
        """Add a folder to the backup configuration"""
        self.config.add_folder(folder_path, bucket_name)

    def remove_folder_from_backup(self, folder_path: str):
        """Remove a folder from the backup configuration"""
        self.config.remove_folder(folder_path)

    def configure_bucket_mode(self, single_bucket: bool, bucket_name: str = ""):
        """Configure bucket backup mode"""
        self.config.set_single_bucket_mode(single_bucket, bucket_name)

    def validate_backup_config(self) -> tuple[bool, str]:
        """Validate the current backup configuration"""
        return self.config.validate_config()

    def execute_backup(
        self, progress_callback=None, status_callback=None, error_callback=None, incremental=True
    ) -> bool:
        """Execute the backup operation with callbacks for progress updates"""
        try:
            # Validate configuration
            is_valid, message = self.validate_backup_config()
            if not is_valid:
                if error_callback:
                    error_callback(message)
                return False

            # Get credentials
            credentials = self.credential_manager.load_credentials()
            if not credentials:
                if error_callback:
                    error_callback("No saved credentials found")
                return False

            # Create S3 client
            s3_client = self.backup_manager.create_s3_client(credentials)

            # Get backup plan
            backup_plan = self.config.get_backup_plan()

            # Initialize progress tracking
            self.progress_tracker.start_backup(backup_plan)

            # Execute backup
            for folder_path, bucket_name in backup_plan.items():
                if self.backup_manager.cancelled:
                    break

                if status_callback:
                    status_callback(f"Backing up: {folder_path}")

                # Get files to backup
                files = self.backup_manager.get_files_to_backup(folder_path)
                self.progress_tracker.start_folder(folder_path, len(files))

                # Upload files (incremental backup)
                folder_path_obj = Path(folder_path)
                for _i, file_path in enumerate(files):
                    if self.backup_manager.cancelled:
                        break

                    s3_key = self.backup_manager.calculate_s3_key(
                        file_path, folder_path_obj
                    )
                    
                    # Check if file needs to be uploaded (incremental backup)
                    should_upload = self.backup_manager.should_upload_file(
                        s3_client, file_path, bucket_name, s3_key, incremental=incremental
                    )
                    
                    if should_upload:
                        # Update status for each file
                        if status_callback:
                            status_callback(f"Uploading: {Path(file_path).name}")
                        
                        success = self.backup_manager.upload_file(
                            s3_client, file_path, bucket_name, s3_key
                        )
                        
                        if success:
                            self.progress_tracker.complete_file()
                            if progress_callback:
                                progress_callback(
                                    self.progress_tracker.get_overall_progress()
                                )
                        else:
                            if error_callback:
                                error_callback(f"Failed to upload: {file_path}")
                    else:
                        # File unchanged, skip upload but still count as completed
                        if status_callback:
                            status_callback(f"Skipping unchanged: {Path(file_path).name}")
                        self.progress_tracker.complete_file()
                        if progress_callback:
                            progress_callback(
                                self.progress_tracker.get_overall_progress()
                            )

                self.progress_tracker.complete_folder()
                if progress_callback:
                    progress_callback(self.progress_tracker.get_overall_progress())

            if not self.backup_manager.cancelled:
                if status_callback:
                    status_callback("Backup completed successfully!")
                # Ensure progress shows 100% when backup completes
                if progress_callback:
                    progress_callback(100)
                return True
            else:
                if status_callback:
                    status_callback("Backup cancelled")
                return False

        except Exception as e:
            if error_callback:
                error_callback(f"Backup failed: {str(e)}")
            return False

    def cancel_backup(self):
        """Cancel the current backup operation"""
        self.backup_manager.cancel_backup()
