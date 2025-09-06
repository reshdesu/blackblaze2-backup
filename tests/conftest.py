"""
Test configuration and fixtures for BlackBlaze B2 Backup Tool
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from blackblaze_backup.config import Config


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_config(temp_config_dir):
    """Create test config instance"""
    config = Config()
    config.config_dir = temp_config_dir
    config.config_file = temp_config_dir / "config.json"
    config.log_file = temp_config_dir / "blackblaze_backup.log"
    return config


@pytest.fixture
def mock_credentials():
    """Mock credentials for testing"""
    return {
        "endpoint": "s3.us-west-001.backblazeb2.com",
        "access_key": "test_access_key",
        "secret_key": "test_secret_key",
        "region": "us-west-001",
    }


@pytest.fixture
def mock_s3_client():
    """Mock S3 client for testing"""
    mock_client = Mock()
    mock_client.list_buckets.return_value = {"Buckets": []}
    mock_client.upload_file.return_value = None
    return mock_client


@pytest.fixture
def temp_folder_with_files():
    """Create temporary folder with test files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "file1.txt").write_text("test content 1")
        (temp_path / "file2.txt").write_text("test content 2")
        (temp_path / "subdir").mkdir()
        (temp_path / "subdir" / "file3.txt").write_text("test content 3")

        yield temp_path


@pytest.fixture
def mock_keyring():
    """Mock keyring for testing"""
    with (
        patch("keyring.set_password") as mock_set,
        patch("keyring.get_password") as mock_get,
    ):
        yield mock_set, mock_get


@pytest.fixture
def mock_boto3():
    """Mock boto3 for testing"""
    with patch("boto3.client") as mock_client:
        yield mock_client


class TestConfig:
    """Test cases for configuration management"""

    def test_get_default_config(self, test_config):
        """Test default configuration generation"""
        config = test_config.get_default_config()

        assert "app" in config
        assert "backup" in config
        assert "ui" in config
        assert config["app"]["name"] == test_config.app_name
        assert config["app"]["version"] == test_config.version

    def test_load_config_file_not_exists(self, test_config):
        """Test loading config when file doesn't exist"""
        config = test_config.load_config()
        assert config == test_config.get_default_config()

    def test_save_and_load_config(self, test_config):
        """Test saving and loading configuration"""
        test_data = {
            "app": {"name": "Test App", "version": "1.0.0"},
            "backup": {"default_region": "us-east-1"},
        }

        # Save config
        result = test_config.save_config(test_data)
        assert result is True

        # Load config
        loaded_config = test_config.load_config()
        assert loaded_config == test_data

    def test_get_config_value(self, test_config):
        """Test getting configuration values"""
        test_data = {
            "app": {"name": "Test App"},
            "backup": {"region": "us-west-001"},
        }

        with patch.object(test_config, "load_config", return_value=test_data):
            assert test_config.get("app.name") == "Test App"
            assert test_config.get("backup.region") == "us-west-001"
            assert test_config.get("nonexistent.key", "default") == "default"

    def test_set_config_value(self, test_config):
        """Test setting configuration values"""
        with patch.object(test_config, "save_config", return_value=True) as mock_save:
            result = test_config.set("app.name", "New App Name")
            assert result is True
            mock_save.assert_called_once()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers"""
    for item in items:
        # Add unit marker to core tests
        if "test_core" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Add integration marker to GUI tests
        if "test_gui" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add slow marker to tests that might take time
        if "backup" in item.name.lower() or "upload" in item.name.lower():
            item.add_marker(pytest.mark.slow)


# Test discovery configuration
# pytest_plugins = ["pytest_qt"]  # Only needed for GUI tests
