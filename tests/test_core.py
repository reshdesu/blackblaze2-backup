"""
Unit tests for BlackBlaze B2 Backup Tool core functionality
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import keyring

from blackblaze_backup.core import (
    CredentialManager,
    BackupManager,
    BackupConfig,
    BackupProgressTracker,
    BackupService
)
from blackblaze_backup.utils import (
    get_file_hash,
    format_file_size,
    sanitize_bucket_name,
    validate_folder_path,
    get_folder_size
)


class TestCredentialManager:
    """Test cases for CredentialManager"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.credential_manager = CredentialManager()
        self.test_credentials = {
            'endpoint': 's3.us-west-001.backblazeb2.com',
            'access_key': 'test_access_key',
            'secret_key': 'test_secret_key',
            'region': 'us-west-001'
        }
    
    @patch('keyring.set_password')
    def test_save_credentials_success(self, mock_set_password):
        """Test successful credential saving"""
        result = self.credential_manager.save_credentials(self.test_credentials)
        assert result is True
        assert mock_set_password.call_count == 2
    
    @patch('keyring.set_password')
    def test_save_credentials_failure(self, mock_set_password):
        """Test credential saving failure"""
        mock_set_password.side_effect = Exception("Keyring error")
        result = self.credential_manager.save_credentials(self.test_credentials)
        assert result is False
    
    @patch('keyring.get_password')
    def test_load_credentials_success(self, mock_get_password):
        """Test successful credential loading"""
        # Mock encrypted data
        mock_get_password.side_effect = [
            "encrypted_credentials_data",
            "encryption_key"
        ]
        
        with patch('cryptography.fernet.Fernet') as mock_fernet:
            mock_cipher = Mock()
            mock_cipher.decrypt.return_value = json.dumps(self.test_credentials).encode()
            mock_fernet.return_value = mock_cipher
            
            result = self.credential_manager.load_credentials()
            assert result == self.test_credentials
    
    @patch('keyring.get_password')
    def test_load_credentials_no_data(self, mock_get_password):
        """Test loading credentials when no data exists"""
        mock_get_password.return_value = None
        result = self.credential_manager.load_credentials()
        assert result is None
    
    @patch('boto3.client')
    def test_validate_credentials_success(self, mock_boto_client):
        """Test successful credential validation"""
        mock_s3_client = Mock()
        mock_s3_client.list_buckets.return_value = {'Buckets': []}
        mock_boto_client.return_value = mock_s3_client
        
        is_valid, message = self.credential_manager.validate_credentials(self.test_credentials)
        assert is_valid is True
        assert "successful" in message
    
    @patch('boto3.client')
    def test_validate_credentials_failure(self, mock_boto_client):
        """Test credential validation failure"""
        mock_boto_client.side_effect = Exception("Connection failed")
        
        is_valid, message = self.credential_manager.validate_credentials(self.test_credentials)
        assert is_valid is False
        assert "failed" in message


class TestBackupManager:
    """Test cases for BackupManager"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.backup_manager = BackupManager()
    
    def test_cancel_backup(self):
        """Test backup cancellation"""
        assert self.backup_manager.cancelled is False
        self.backup_manager.cancel_backup()
        assert self.backup_manager.cancelled is True
    
    def test_get_files_to_backup(self):
        """Test getting files to backup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "file1.txt").write_text("test content 1")
            (temp_path / "subdir").mkdir()
            (temp_path / "subdir" / "file2.txt").write_text("test content 2")
            
            files = self.backup_manager.get_files_to_backup(str(temp_path))
            assert len(files) == 2
            assert all(f.is_file() for f in files)
    
    def test_get_files_to_backup_nonexistent(self):
        """Test getting files from nonexistent folder"""
        with pytest.raises(FileNotFoundError):
            self.backup_manager.get_files_to_backup("/nonexistent/path")
    
    def test_calculate_s3_key(self):
        """Test S3 key calculation"""
        base_folder = Path("/home/user/documents")
        file_path = Path("/home/user/documents/subdir/file.txt")
        
        s3_key = self.backup_manager.calculate_s3_key(file_path, base_folder)
        assert s3_key == "subdir/file.txt"
    
    @patch('boto3.client')
    def test_create_s3_client(self, mock_boto_client):
        """Test S3 client creation"""
        credentials = {
            'endpoint': 's3.us-west-001.backblazeb2.com',
            'access_key': 'test_key',
            'secret_key': 'test_secret',
            'region': 'us-west-001'
        }
        
        self.backup_manager.create_s3_client(credentials)
        mock_boto_client.assert_called_once()


class TestBackupConfig:
    """Test cases for BackupConfig"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config = BackupConfig()
    
    def test_add_folder(self):
        """Test adding folder to configuration"""
        self.config.add_folder("/test/folder", "test-bucket")
        assert "/test/folder" in self.config.folders_to_backup
        assert self.config.folders_to_backup["/test/folder"] == "test-bucket"
    
    def test_remove_folder(self):
        """Test removing folder from configuration"""
        self.config.add_folder("/test/folder", "test-bucket")
        self.config.remove_folder("/test/folder")
        assert "/test/folder" not in self.config.folders_to_backup
    
    def test_set_single_bucket_mode(self):
        """Test single bucket mode configuration"""
        self.config.set_single_bucket_mode(True, "single-bucket")
        assert self.config.single_bucket_mode is True
        assert self.config.single_bucket_name == "single-bucket"
    
    def test_get_backup_plan_single_bucket(self):
        """Test backup plan generation for single bucket mode"""
        self.config.add_folder("/folder1", "bucket1")
        self.config.add_folder("/folder2", "bucket2")
        self.config.set_single_bucket_mode(True, "single-bucket")
        
        plan = self.config.get_backup_plan()
        assert all(bucket == "single-bucket" for bucket in plan.values())
    
    def test_get_backup_plan_multiple_buckets(self):
        """Test backup plan generation for multiple bucket mode"""
        self.config.add_folder("/folder1", "bucket1")
        self.config.add_folder("/folder2", "bucket2")
        
        plan = self.config.get_backup_plan()
        assert plan["/folder1"] == "bucket1"
        assert plan["/folder2"] == "bucket2"
    
    def test_validate_config_no_folders(self):
        """Test configuration validation with no folders"""
        is_valid, message = self.config.validate_config()
        assert is_valid is False
        assert "No folders" in message
    
    def test_validate_config_single_bucket_no_name(self):
        """Test configuration validation for single bucket mode without bucket name"""
        self.config.add_folder("/test/folder")
        self.config.set_single_bucket_mode(True, "")
        
        is_valid, message = self.config.validate_config()
        assert is_valid is False
        assert "bucket name is required" in message
    
    def test_validate_config_valid(self):
        """Test valid configuration"""
        self.config.add_folder("/test/folder", "test-bucket")
        
        is_valid, message = self.config.validate_config()
        assert is_valid is True
        assert "valid" in message


class TestBackupProgressTracker:
    """Test cases for BackupProgressTracker"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.tracker = BackupProgressTracker()
    
    def test_start_backup(self):
        """Test backup initialization"""
        folders = {"folder1": "bucket1", "folder2": "bucket2"}
        self.tracker.start_backup(folders)
        
        assert self.tracker.total_folders == 2
        assert self.tracker.completed_folders == 0
    
    def test_start_folder(self):
        """Test folder processing start"""
        self.tracker.start_folder("/test/folder", 10)
        
        assert self.tracker.current_folder == "/test/folder"
        assert self.tracker.total_files == 10
        assert self.tracker.completed_files == 0
    
    def test_complete_file(self):
        """Test file completion tracking"""
        self.tracker.total_files = 10
        self.tracker.complete_file()
        
        assert self.tracker.completed_files == 1
    
    def test_complete_folder(self):
        """Test folder completion tracking"""
        self.tracker.total_folders = 5
        self.tracker.complete_folder()
        
        assert self.tracker.completed_folders == 1
    
    def test_get_overall_progress(self):
        """Test overall progress calculation"""
        self.tracker.total_folders = 4
        self.tracker.completed_folders = 2
        
        progress = self.tracker.get_overall_progress()
        assert progress == 50
    
    def test_get_folder_progress(self):
        """Test folder progress calculation"""
        self.tracker.total_files = 8
        self.tracker.completed_files = 6
        
        progress = self.tracker.get_folder_progress()
        assert progress == 75
    
    def test_get_status_message(self):
        """Test status message generation"""
        self.tracker.current_folder = "/test/folder"
        
        message = self.tracker.get_status_message()
        assert "Backing up: /test/folder" in message


class TestUtils:
    """Test cases for utility functions"""
    
    def test_format_file_size(self):
        """Test file size formatting"""
        assert format_file_size(0) == "0 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"
    
    def test_sanitize_bucket_name(self):
        """Test bucket name sanitization"""
        assert sanitize_bucket_name("My Bucket!") == "my-bucket"
        assert sanitize_bucket_name("test@#$%bucket") == "test-bucket"
        assert sanitize_bucket_name("") == "backup-bucket"
        assert sanitize_bucket_name("a" * 100) == "a" * 63
    
    def test_validate_folder_path(self):
        """Test folder path validation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            is_valid, message = validate_folder_path(temp_dir)
            assert is_valid is True
        
        is_valid, message = validate_folder_path("/nonexistent/path")
        assert is_valid is False
        assert "does not exist" in message


if __name__ == "__main__":
    pytest.main([__file__])
