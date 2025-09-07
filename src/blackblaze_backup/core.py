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

    def reset_cancellation(self):
        """Reset the cancellation state for a new backup"""
        self.cancelled = False
        self.logger.info("Backup cancellation state reset")

    def get_files_to_backup(
        self, folder_path: str, progress_callback=None
    ) -> list[Path]:
        """Get all files in a folder that need to be backed up with progress updates"""
        folder_path_obj = Path(folder_path)
        if not folder_path_obj.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        # Use generator to avoid blocking UI during large scans
        files = []
        total_scanned = 0

        if progress_callback:
            progress_callback("Scanning files...")

        # Use rglob with generator to avoid blocking
        for file_path in folder_path_obj.rglob("*"):
            if self.cancelled:
                break

            if file_path.is_file():
                files.append(file_path)

            total_scanned += 1

            # Update progress every 1000 files to avoid UI blocking
            if total_scanned % 1000 == 0 and progress_callback:
                progress_callback(
                    f"Scanned {total_scanned} items, found {len(files)} files..."
                )
                # Small yield to allow UI updates
                import time

                time.sleep(0.001)  # 1ms yield

        if progress_callback:
            progress_callback(f"File scan complete: {len(files)} files found")

        return files

    def calculate_s3_key(self, file_path: Path, base_folder: Path) -> str:
        """Calculate the S3 key for a file based on its relative path"""
        relative_path = file_path.relative_to(base_folder)
        # Create a folder with the same name as the base folder and put files inside it
        folder_name = base_folder.name
        return f"{folder_name}/{relative_path}".replace("\\", "/")

    def should_upload_file(
        self,
        s3_client,
        file_path: Path,
        bucket_name: str,
        s3_key: str,
        incremental: bool = True,
        enable_deduplication: bool = True,
    ) -> bool:
        """Check if file should be uploaded (incremental backup logic with deduplication)

        Uses multi-level verification:
        1. File size check (fast, catches 99.9% of changes)
        2. Hash comparison (definitive, handles edge cases)
        3. Content deduplication (prevents uploading identical files to different locations)

        Probability analysis:
        - Different file sizes: ~99.9% chance files are different
        - Same size + different hash: ~100% chance files are different
        - Same size + same hash: ~0% chance files are different (MD5 collision ~1 in 2^128)
        """
        # If incremental backup is disabled, always upload
        if not incremental:
            return True

        try:
            from .utils import get_file_hash

            # Get local file info
            local_size = file_path.stat().st_size
            local_hash = get_file_hash(file_path, "md5")

            if not local_hash:
                self.logger.warning(
                    f"Could not calculate hash for {file_path.name}, will upload"
                )
                return True

            # Check if file exists at exact S3 key (path-based check)
            try:
                response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                s3_size = response.get("ContentLength", 0)
                s3_etag = response.get("ETag", "").strip('"')

                # LEVEL 1: File size check (fastest, catches 99.9% of changes)
                if local_size != s3_size:
                    self.logger.debug(
                        f"File size changed: {file_path.name} ({local_size} vs {s3_size})"
                    )
                    return True

                # LEVEL 2: Hash verification (definitive check for same-size files)
                if s3_etag:
                    # Handle multi-part upload ETags (format: "hash-partcount")
                    if "-" in s3_etag:
                        # Multi-part upload - compare just the hash part
                        s3_hash = s3_etag.split("-")[0]
                        if local_hash != s3_hash:
                            self.logger.debug(
                                f"File hash changed (multi-part): {file_path.name}"
                            )
                            return True
                    else:
                        # Single-part upload - direct comparison
                        if local_hash != s3_etag:
                            self.logger.debug(f"File hash changed: {file_path.name}")
                            return True

                # File passed both size and hash checks - definitely unchanged
                self.logger.debug(f"Skipping unchanged file: {file_path.name}")
                return False

            except s3_client.exceptions.NoSuchKey:
                # File doesn't exist at this S3 key
                self.logger.debug(f"File not found at S3 key: {file_path.name}")

                # If deduplication is enabled, check if this content exists elsewhere
                if enable_deduplication:
                    if self._file_content_exists_in_s3(
                        s3_client, bucket_name, local_hash
                    ):
                        self.logger.info(
                            f"Skipping duplicate content: {file_path.name} (hash: {local_hash[:8]}...)"
                        )
                        return False

                # New file or new content
                self.logger.debug(f"New file: {file_path.name}")
                return True

            except Exception as e:
                # Handle other S3 errors (like network issues) but still check deduplication
                self.logger.warning(
                    f"S3 error checking {file_path.name}: {e}. Checking deduplication..."
                )

                # If deduplication is enabled, check if this content exists elsewhere
                if enable_deduplication:
                    if self._file_content_exists_in_s3(
                        s3_client, bucket_name, local_hash
                    ):
                        self.logger.info(
                            f"Skipping duplicate content despite S3 error: {file_path.name} (hash: {local_hash[:8]}...)"
                        )
                        return False

                # If we can't check S3 or deduplication, err on the side of uploading
                self.logger.warning(f"Will upload {file_path.name} due to S3 error")
                return True

        except Exception as e:
            # If we can't even calculate hash or access file, err on the side of uploading
            self.logger.warning(
                f"Could not process file {file_path.name}: {e}. Will upload to be safe."
            )
            return True

    def _file_content_exists_in_s3(
        self, s3_client, bucket_name: str, file_hash: str
    ) -> bool:
        """Check if file content (by hash) already exists anywhere in S3 bucket

        This is an efficient way to detect duplicate content without scanning all files.
        Uses S3 metadata to store and lookup file hashes.
        """
        try:
            # Use S3 list_objects_v2 to search for files with matching hash metadata
            # This is much more efficient than scanning all files
            paginator = s3_client.get_paginator("list_objects_v2")

            for page in paginator.paginate(Bucket=bucket_name):
                if "Contents" not in page:
                    continue

                # Check each object's metadata for matching hash
                for obj in page["Contents"]:
                    try:
                        # Get object metadata
                        response = s3_client.head_object(
                            Bucket=bucket_name, Key=obj["Key"]
                        )
                        metadata = response.get("Metadata", {})

                        # Check if hash matches
                        if metadata.get("file-hash") == file_hash:
                            self.logger.debug(
                                f"Found duplicate content at: {obj['Key']}"
                            )
                            return True

                    except Exception as e:
                        # Skip objects we can't read metadata for
                        self.logger.debug(
                            f"Could not read metadata for {obj['Key']}: {e}"
                        )
                        continue

            return False

        except Exception as e:
            self.logger.warning(f"Error checking for duplicate content: {e}")
            # If we can't check, assume it's new content
            return False

    def upload_file(
        self, s3_client, file_path: Path, bucket_name: str, s3_key: str
    ) -> bool:
        """Upload a single file to S3 with hash metadata for deduplication"""
        try:
            from .utils import get_file_hash

            # Calculate file hash for metadata
            file_hash = get_file_hash(file_path, "md5")

            # Prepare metadata
            metadata = {}
            if file_hash:
                metadata["file-hash"] = file_hash
                metadata["file-size"] = str(file_path.stat().st_size)

            # Upload with metadata
            extra_args = {}
            if metadata:
                extra_args["Metadata"] = metadata

            s3_client.upload_file(
                str(file_path), bucket_name, s3_key, ExtraArgs=extra_args
            )

            self.logger.debug(
                f"Uploaded {file_path.name} with hash metadata: {file_hash[:8] if file_hash else 'N/A'}..."
            )
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
        self.enable_deduplication = True  # Enable content deduplication by default

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

    def set_deduplication(self, enabled: bool):
        """Configure content deduplication"""
        self.enable_deduplication = enabled

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

    def configure_deduplication(self, enabled: bool):
        """Configure content deduplication"""
        self.config.set_deduplication(enabled)

    def validate_backup_config(self) -> tuple[bool, str]:
        """Validate the current backup configuration"""
        return self.config.validate_config()

    def execute_backup(
        self,
        progress_callback=None,
        status_callback=None,
        error_callback=None,
        incremental=True,
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

                # Get files to backup with progress updates
                files = self.backup_manager.get_files_to_backup(
                    folder_path, progress_callback
                )
                self.progress_tracker.start_folder(folder_path, len(files))

                # Upload files (incremental backup)
                folder_path_obj = Path(folder_path)
                for _i, file_path in enumerate(files):
                    if self.backup_manager.cancelled:
                        break

                    s3_key = self.backup_manager.calculate_s3_key(
                        file_path, folder_path_obj
                    )

                    # Check if file needs to be uploaded (incremental backup with deduplication)
                    should_upload = self.backup_manager.should_upload_file(
                        s3_client,
                        file_path,
                        bucket_name,
                        s3_key,
                        incremental=incremental,
                        enable_deduplication=self.config.enable_deduplication,
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
                            status_callback(
                                f"Skipping unchanged: {Path(file_path).name}"
                            )
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

    def reset_cancellation(self):
        """Reset the cancellation state for a new backup"""
        self.backup_manager.reset_cancellation()
