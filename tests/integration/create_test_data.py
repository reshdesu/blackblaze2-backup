#!/usr/bin/env python3
"""
BlackBlaze B2 Backup Tool - Test Suite
Creates test data and runs comprehensive tests before release
"""

import json
from datetime import datetime
from pathlib import Path


class TestDataCreator:
    """Creates comprehensive test data for backup testing"""

    def __init__(self, base_path: str = None):
        self.base_path = (
            Path(base_path)
            if base_path
            else Path.home() / "Documents" / "blackblaze-test-backup"
        )
        self.test_files = []

    def create_test_structure(self) -> Path:
        """Create comprehensive test folder structure"""
        print(f"Creating test data structure at: {self.base_path}")

        # Create main directory
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Create nested directories
        subdirs = ["documents", "images", "archives", "logs", "config"]
        for subdir in subdirs:
            (self.base_path / subdir).mkdir(exist_ok=True)

        # Create test files
        self._create_root_files()
        self._create_nested_files()
        self._create_large_files()
        self._create_special_files()

        print(f" Test structure created with {len(self.test_files)} files")
        return self.base_path

    def _create_root_files(self):
        """Create files in root directory"""
        files = {
            "README.md": self._get_readme_content(),
            "config.json": self._get_config_content(),
            "sample_data.csv": self._get_csv_content(),
            "app.log": self._get_log_content(),
            "sample.txt": self._get_sample_text_content(),
        }

        for filename, content in files.items():
            file_path = self.base_path / filename
            file_path.write_text(content)
            self.test_files.append(file_path)

    def _create_nested_files(self):
        """Create files in subdirectories"""
        nested_files = {
            "documents/project_docs.md": self._get_project_docs_content(),
            "documents/api_spec.yaml": self._get_yaml_content(),
            "images/test_image_metadata.txt": self._get_image_metadata_content(),
            "images/thumbnail_info.json": self._get_thumbnail_content(),
            "archives/test_archive_info.txt": self._get_archive_content(),
            "archives/backup_manifest.json": self._get_manifest_content(),
            "logs/error.log": self._get_error_log_content(),
            "logs/debug.log": self._get_debug_log_content(),
            "config/settings.ini": self._get_ini_content(),
            "config/database.conf": self._get_db_config_content(),
        }

        for filepath, content in nested_files.items():
            file_path = self.base_path / filepath
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            self.test_files.append(file_path)

    def _create_large_files(self):
        """Create larger files for performance testing"""
        # Create a larger text file
        large_content = (
            "This is a large test file for backup performance testing.\n" * 1000
        )
        large_file = self.base_path / "large_test_file.txt"
        large_file.write_text(large_content)
        self.test_files.append(large_file)

        # Create a large JSON file
        large_json = {
            "test_data": [
                {
                    "id": i,
                    "value": f"test_value_{i}",
                    "timestamp": datetime.now().isoformat(),
                }
                for i in range(1000)
            ]
        }
        large_json_file = self.base_path / "documents" / "large_dataset.json"
        large_json_file.write_text(json.dumps(large_json, indent=2))
        self.test_files.append(large_json_file)

    def _create_special_files(self):
        """Create files with special characters and edge cases"""
        # File with special characters in name
        special_file = self.base_path / "file-with-special-chars_123.txt"
        special_file.write_text("File with special characters in filename")
        self.test_files.append(special_file)

        # Empty file
        empty_file = self.base_path / "empty_file.txt"
        empty_file.write_text("")
        self.test_files.append(empty_file)

        # File with unicode content
        unicode_file = self.base_path / "unicode_test.txt"
        unicode_content = "Unicode test: café, naïve, résumé, 中文, العربية, русский"
        unicode_file.write_text(unicode_content)
        self.test_files.append(unicode_file)

    def get_file_summary(self) -> dict:
        """Get summary of created test files"""
        total_size = sum(f.stat().st_size for f in self.test_files)
        return {
            "total_files": len(self.test_files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_types": self._get_file_types(),
            "directory_structure": self._get_directory_structure(),
        }

    def _get_file_types(self) -> dict[str, int]:
        """Count files by extension"""
        extensions = {}
        for file_path in self.test_files:
            ext = file_path.suffix.lower() or "no_extension"
            extensions[ext] = extensions.get(ext, 0) + 1
        return extensions

    def _get_directory_structure(self) -> list[str]:
        """Get directory structure as list"""
        structure = []
        for file_path in sorted(self.test_files):
            rel_path = file_path.relative_to(self.base_path)
            structure.append(str(rel_path))
        return structure

    # Content generation methods
    def _get_readme_content(self) -> str:
        return """# BlackBlaze B2 Backup Test Files

This is a comprehensive test suite for the BlackBlaze B2 backup tool.

## Test Scenarios

1. **File Types**: Various file extensions and formats
2. **Directory Structure**: Nested folders and subdirectories
3. **File Sizes**: Small, medium, and large files
4. **Special Characters**: Unicode, special chars in filenames
5. **Edge Cases**: Empty files, binary simulation

## File Structure

- Root files: 5 files
- Nested files: 10 files
- Large files: 2 files
- Special files: 3 files

Total: 20 test files across 6 directories

Created: {datetime.now().isoformat()}
"""

    def _get_config_content(self) -> str:
        config = {
            "app": {
                "name": "BlackBlaze B2 Backup Tool",
                "version": "1.0.0",
                "test_mode": True,
            },
            "backup": {
                "test_files": 20,
                "test_folders": 6,
                "created_at": datetime.now().isoformat(),
            },
        }
        return json.dumps(config, indent=2)

    def _get_csv_content(self) -> str:
        return """Name,Age,City,Country,Occupation,Salary
John Doe,30,New York,USA,Software Engineer,75000
Jane Smith,25,London,UK,Designer,55000
Bob Johnson,35,Toronto,Canada,Manager,85000
Alice Brown,28,Sydney,Australia,Developer,70000
Charlie Wilson,32,Berlin,Germany,Analyst,65000
Diana Lee,27,Tokyo,Japan,Consultant,80000
Eve Davis,29,Paris,France,Architect,90000
Frank Miller,31,Mumbai,India,Engineer,60000
Grace Taylor,26,Sao Paulo,Brazil,Designer,50000
Henry Chen,33,Shanghai,China,Developer,75000"""

    def _get_log_content(self) -> str:
        return f"""2025-09-06 16:20:01 - INFO - BlackBlaze B2 Backup Tool started
2025-09-06 16:20:02 - INFO - Loading configuration from config.json
2025-09-06 16:20:03 - INFO - Connecting to BackBlaze B2 endpoint
2025-09-06 16:20:04 - INFO - Authentication successful
2025-09-06 16:20:05 - INFO - Scanning folder: {self.base_path}
2025-09-06 16:20:06 - INFO - Found 20 files to backup
2025-09-06 16:20:07 - INFO - Starting backup process
2025-09-06 16:20:08 - INFO - Uploading README.md (2.1 KB)
2025-09-06 16:20:09 - INFO - Uploading config.json (1.8 KB)
2025-09-06 16:20:10 - INFO - Uploading sample_data.csv (3.2 KB)
2025-09-06 16:20:11 - INFO - Uploading app.log (2.0 KB)
2025-09-06 16:20:12 - INFO - Uploading sample.txt (1.5 KB)
2025-09-06 16:20:13 - INFO - Backup completed successfully
2025-09-06 16:20:14 - INFO - Total files uploaded: 20
2025-09-06 16:20:15 - INFO - Total size: 45.2 KB
2025-09-06 16:20:16 - INFO - Backup duration: 25 seconds"""

    def _get_sample_text_content(self) -> str:
        return """This is a sample text file for testing the BlackBlaze B2 backup functionality.

The backup tool should be able to handle:
- Plain text files
- Various file extensions
- Different file sizes
- Special characters: !@#$%^&*()
- Unicode characters: café, naïve, résumé
- Numbers: 1234567890
- Mixed content: Text with numbers 123 and symbols @#$%

This file is designed to test the robustness of the backup system
when dealing with different types of content.

End of sample file."""

    def _get_project_docs_content(self) -> str:
        return """# Project Documentation

## Overview
This is a test document for the BlackBlaze B2 backup tool.

## Features
- Cross-platform support
- Background operation
- Scheduled backups
- Secure credential storage

## Testing
This document is used to test:
1. Nested folder structure backup
2. Markdown file handling
3. Special characters in filenames
4. File path preservation

## Notes
Created for backup functionality testing."""

    def _get_yaml_content(self) -> str:
        return """api:
  version: "1.0.0"
  name: "BlackBlaze B2 Backup API"

endpoints:
  backup:
    method: POST
    path: "/api/backup"
    description: "Start backup process"

  status:
    method: GET
    path: "/api/status"
    description: "Get backup status"

authentication:
  type: "API Key"
  header: "X-API-Key"
"""

    def _get_image_metadata_content(self) -> str:
        return """# Test Image Metadata

This file represents image metadata for backup testing.

## Image Information
- Format: PNG
- Dimensions: 1920x1080
- Size: 2.5 MB
- Created: 2025-09-06
- Color Space: RGB

## Backup Test
This metadata file tests:
- Binary file handling simulation
- Large file size testing
- Image format preservation
- Metadata backup functionality

Note: This is a text file simulating image metadata for testing purposes."""

    def _get_thumbnail_content(self) -> str:
        return json.dumps(
            {
                "thumbnail": {
                    "width": 150,
                    "height": 150,
                    "format": "JPEG",
                    "size": "45KB",
                    "created": datetime.now().isoformat(),
                }
            },
            indent=2,
        )

    def _get_archive_content(self) -> str:
        return """# Archive Test File

This file simulates an archive for backup testing.

## Archive Contents
- Compressed data simulation
- Multiple file types
- Nested directory structure
- Binary and text data

## Test Scenarios
1. Archive file handling
2. Compressed data backup
3. Large file processing
4. Binary content preservation

## Archive Information
- Format: ZIP simulation
- Size: 5.2 MB (simulated)
- Files: 15 files, 3 folders
- Compression: 65% ratio

This is a text file simulating archive metadata for testing purposes."""

    def _get_manifest_content(self) -> str:
        return json.dumps(
            {
                "backup_manifest": {
                    "version": "1.0.0",
                    "created_at": datetime.now().isoformat(),
                    "files": [
                        {
                            "path": "README.md",
                            "size": 2048,
                            "checksum": "abc123",
                        },
                        {
                            "path": "config.json",
                            "size": 1024,
                            "checksum": "def456",
                        },
                        {
                            "path": "sample_data.csv",
                            "size": 3072,
                            "checksum": "ghi789",
                        },
                    ],
                    "total_files": 20,
                    "total_size": 45200,
                }
            },
            indent=2,
        )

    def _get_error_log_content(self) -> str:
        return f"""2025-09-06 16:20:01 - ERROR - Failed to connect to endpoint
2025-09-06 16:20:02 - WARNING - Retrying connection attempt 1
2025-09-06 16:20:03 - ERROR - Authentication failed
2025-09-06 16:20:04 - INFO - Using fallback authentication method
2025-09-06 16:20:05 - ERROR - File upload failed: {self.base_path}/large_file.txt
2025-09-06 16:20:06 - WARNING - Retrying upload attempt 2
2025-09-06 16:20:07 - INFO - Upload successful after retry"""

    def _get_debug_log_content(self) -> str:
        return f"""2025-09-06 16:20:01 - DEBUG - Initializing backup service
2025-09-06 16:20:02 - DEBUG - Loading credentials from keyring
2025-09-06 16:20:03 - DEBUG - Creating S3 client with endpoint: s3.us-east-005.backblazeb2.com
2025-09-06 16:20:04 - DEBUG - Testing connection to BackBlaze B2
2025-09-06 16:20:05 - DEBUG - Connection successful, proceeding with backup
2025-09-06 16:20:06 - DEBUG - Scanning directory: {self.base_path}
2025-09-06 16:20:07 - DEBUG - Found 20 files to process
2025-09-06 16:20:08 - DEBUG - Starting file upload process"""

    def _get_ini_content(self) -> str:
        return """[app]
name = BlackBlaze B2 Backup Tool
version = 1.0.0
debug = true

[backup]
max_files = 1000
chunk_size = 8192
retry_attempts = 3

[logging]
level = INFO
file = backup.log
max_size = 10MB
"""

    def _get_db_config_content(self) -> str:
        return """# Database Configuration

[mysql]
host = localhost
port = 3306
database = backup_db
username = backup_user
password = secure_password

[postgresql]
host = localhost
port = 5432
database = backup_db
username = backup_user
password = secure_password

[redis]
host = localhost
port = 6379
database = 0
password = redis_password
"""


def main():
    """Main function to create test data"""
    print(" BlackBlaze B2 Backup Tool - Test Data Creator")
    print("=" * 60)

    # Create test data
    creator = TestDataCreator()
    test_path = creator.create_test_structure()

    # Display summary
    summary = creator.get_file_summary()
    print("\nTest Data Summary:")
    print(f"    Total Files: {summary['total_files']}")
    print(f"    Total Size: {summary['total_size_mb']} MB")
    print(f"    File Types: {summary['file_types']}")

    print("\n Directory Structure:")
    for file_path in summary["directory_structure"][:10]:  # Show first 10
        print(f"   - {file_path}")
    if len(summary["directory_structure"]) > 10:
        print(f"   ... and {len(summary['directory_structure']) - 10} more files")

    print(f"\n Test data created successfully at: {test_path}")
    print("Ready for backup testing!")


if __name__ == "__main__":
    main()
