"""
GUI tests for BlackBlaze B2 Backup Tool using pytest-qt
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QPushButton,
    QTabWidget,
)

from blackblaze_backup.core import BackupService
from blackblaze_backup.gui import BlackBlazeBackupApp


@pytest.fixture
def app(qtbot):
    """Create application instance for testing"""
    application = BlackBlazeBackupApp()
    qtbot.addWidget(application)
    return application


@pytest.fixture
def temp_folder():
    """Create temporary folder for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "file1.txt").write_text("test content 1")
        (temp_path / "subdir").mkdir()
        (temp_path / "subdir" / "file2.txt").write_text("test content 2")

        yield temp_path


class TestBlackBlazeBackupApp:
    """Test cases for main GUI application"""

    def test_app_initialization(self, app):
        """Test application initialization"""
        assert app.windowTitle() == "BlackBlaze B2 Backup Tool"
        assert app.backup_service is not None
        assert app.backup_worker is None

    def test_credentials_tab_elements(self, app):
        """Test credentials tab UI elements"""
        # Find credentials tab (assuming it's the first tab)
        tab_widget = app.findChild(QTabWidget)
        assert tab_widget is not None

        # Check if credential fields exist
        assert app.endpoint_edit is not None
        assert app.access_key_edit is not None
        assert app.secret_key_edit is not None
        assert app.region_edit is not None

    def test_folders_tab_elements(self, app):
        """Test folders tab UI elements"""
        assert app.folder_tree is not None
        assert app.single_bucket_check is not None
        assert app.single_bucket_edit is not None

    def test_backup_tab_elements(self, app):
        """Test backup tab UI elements"""
        assert app.start_backup_btn is not None
        assert app.cancel_backup_btn is not None
        assert app.progress_bar is not None
        assert app.status_text is not None
        assert app.log_text is not None


class TestCredentialsTab:
    """Test cases for credentials tab functionality"""

    def test_credential_fields_input(self, app, qtbot):
        """Test credential field input"""
        # Test endpoint input
        qtbot.keyClicks(app.endpoint_edit, "s3.us-west-001.backblazeb2.com")
        assert app.endpoint_edit.text() == "s3.us-west-001.backblazeb2.com"

        # Test access key input
        qtbot.keyClicks(app.access_key_edit, "test_access_key")
        assert app.access_key_edit.text() == "test_access_key"

        # Test secret key input
        qtbot.keyClicks(app.secret_key_edit, "test_secret_key")
        assert app.secret_key_edit.text() == "test_secret_key"

        # Test region input
        qtbot.keyClicks(app.region_edit, "us-west-001")
        assert app.region_edit.text() == "us-west-001"

    @patch("blackblaze_backup.gui.QMessageBox.information")
    @patch.object(BackupService, "set_credentials")
    def test_test_connection_success(
        self, mock_set_credentials, mock_message_box, app, qtbot
    ):
        """Test successful connection test"""
        mock_set_credentials.return_value = (True, "Connection successful")

        # Fill in credentials
        app.endpoint_edit.setText("s3.us-west-001.backblazeb2.com")
        app.access_key_edit.setText("test_access_key")
        app.secret_key_edit.setText("test_secret_key")
        app.region_edit.setText("us-west-001")

        # Find and click test connection button
        buttons = app.findChildren(QPushButton)
        test_button = next(
            (btn for btn in buttons if btn.text() == "Test Connection"), None
        )

        if test_button:
            qtbot.mouseClick(test_button, Qt.LeftButton)
            mock_set_credentials.assert_called_once()
            mock_message_box.assert_called_once()

    @patch("blackblaze_backup.gui.QMessageBox.critical")
    @patch.object(BackupService, "set_credentials")
    def test_test_connection_failure(
        self, mock_set_credentials, mock_message_box, app, qtbot
    ):
        """Test failed connection test"""
        mock_set_credentials.return_value = (False, "Connection failed")

        # Fill in credentials
        app.endpoint_edit.setText("invalid-endpoint")
        app.access_key_edit.setText("invalid_key")
        app.secret_key_edit.setText("invalid_secret")
        app.region_edit.setText("invalid_region")

        # Find and click test connection button
        buttons = app.findChildren(QPushButton)
        test_button = next(
            (btn for btn in buttons if btn.text() == "Test Connection"), None
        )

        if test_button:
            qtbot.mouseClick(test_button, Qt.LeftButton)
            mock_set_credentials.assert_called_once()
            mock_message_box.assert_called_once()


class TestFoldersTab:
    """Test cases for folders tab functionality"""

    def test_add_folder_dialog(self, app, qtbot, temp_folder):
        """Test add folder functionality"""
        with patch(
            "blackblaze_backup.gui.QFileDialog.getExistingDirectory"
        ) as mock_dialog:
            mock_dialog.return_value = str(temp_folder)

            # Find and click add folder button
            buttons = app.findChildren(QPushButton)
            add_button = next(
                (btn for btn in buttons if btn.text() == "Add Folder"), None
            )

            if add_button:
                qtbot.mouseClick(add_button, Qt.LeftButton)

                # Check if folder was added to tree
                assert app.folder_tree.topLevelItemCount() > 0
                mock_dialog.assert_called_once()

    def test_single_bucket_mode_toggle(self, app, qtbot):
        """Test single bucket mode toggle"""
        # Initially should be unchecked
        assert not app.single_bucket_check.isChecked()

        # Toggle checkbox
        qtbot.mouseClick(app.single_bucket_check, Qt.LeftButton)
        assert app.single_bucket_check.isChecked()

        # Toggle back
        qtbot.mouseClick(app.single_bucket_check, Qt.LeftButton)
        assert not app.single_bucket_check.isChecked()

    def test_single_bucket_input(self, app, qtbot):
        """Test single bucket name input"""
        qtbot.keyClicks(app.single_bucket_edit, "my-backup-bucket")
        assert app.single_bucket_edit.text() == "my-backup-bucket"


class TestBackupTab:
    """Test cases for backup tab functionality"""

    def test_backup_button_states(self, app):
        """Test backup button initial states"""
        assert app.start_backup_btn.isEnabled()
        assert not app.cancel_backup_btn.isEnabled()

    @patch("blackblaze_backup.gui.QMessageBox.warning")
    def test_start_backup_no_credentials(self, mock_message_box, app, qtbot):
        """Test starting backup without credentials"""
        # Don't fill in credentials
        buttons = app.findChildren(QPushButton)
        start_button = next(
            (btn for btn in buttons if btn.text() == "Start Backup"), None
        )

        if start_button:
            qtbot.mouseClick(start_button, Qt.LeftButton)
            mock_message_box.assert_called_once()

    @patch("blackblaze_backup.gui.QMessageBox.warning")
    def test_start_backup_no_folders(self, mock_message_box, app, qtbot):
        """Test starting backup without folders"""
        # Fill in credentials but no folders
        app.endpoint_edit.setText("s3.us-west-001.backblazeb2.com")
        app.access_key_edit.setText("test_access_key")
        app.secret_key_edit.setText("test_secret_key")
        app.region_edit.setText("us-west-001")

        buttons = app.findChildren(QPushButton)
        start_button = next(
            (btn for btn in buttons if btn.text() == "Start Backup"), None
        )

        if start_button:
            qtbot.mouseClick(start_button, Qt.LeftButton)
            mock_message_box.assert_called_once()

    def test_progress_bar_initialization(self, app):
        """Test progress bar initialization"""
        assert app.progress_bar.value() == 0
        assert app.progress_bar.minimum() == 0
        assert app.progress_bar.maximum() == 100

    def test_status_text_initialization(self, app):
        """Test status text initialization"""
        assert app.status_text.isReadOnly()
        assert app.status_text.toPlainText() == ""

    def test_log_text_initialization(self, app):
        """Test log text initialization"""
        assert app.log_text.isReadOnly()
        assert app.log_text.toPlainText() == ""


class TestIntegration:
    """Integration tests for the complete workflow"""

    @patch("blackblaze_backup.gui.QMessageBox.information")
    @patch.object(BackupService, "set_credentials")
    @patch.object(BackupService, "add_folder_to_backup")
    @patch.object(BackupService, "validate_backup_config")
    def test_complete_workflow(
        self,
        mock_validate,
        mock_add_folder,
        mock_set_credentials,
        mock_message_box,
        app,
        qtbot,
        temp_folder,
    ):
        """Test complete backup workflow"""
        # Mock successful operations
        mock_set_credentials.return_value = (True, "Connection successful")
        mock_validate.return_value = (True, "Configuration is valid")

        # Fill in credentials
        app.endpoint_edit.setText("s3.us-west-001.backblazeb2.com")
        app.access_key_edit.setText("test_access_key")
        app.secret_key_edit.setText("test_secret_key")
        app.region_edit.setText("us-west-001")

        # Test connection
        buttons = app.findChildren(QPushButton)
        test_button = next(
            (btn for btn in buttons if btn.text() == "Test Connection"), None
        )

        if test_button:
            qtbot.mouseClick(test_button, Qt.LeftButton)
            mock_set_credentials.assert_called_once()

        # Add folder
        with patch(
            "blackblaze_backup.gui.QFileDialog.getExistingDirectory"
        ) as mock_dialog:
            mock_dialog.return_value = str(temp_folder)

            add_button = next(
                (btn for btn in buttons if btn.text() == "Add Folder"), None
            )
            if add_button:
                qtbot.mouseClick(add_button, Qt.LeftButton)
                mock_add_folder.assert_called_once()

        # Configure single bucket mode
        qtbot.mouseClick(app.single_bucket_check, Qt.LeftButton)
        qtbot.keyClicks(app.single_bucket_edit, "test-bucket")

        # Start backup (this would normally start the worker thread)
        start_button = next(
            (btn for btn in buttons if btn.text() == "Start Backup"), None
        )
        if start_button:
            qtbot.mouseClick(start_button, Qt.LeftButton)
            mock_validate.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
