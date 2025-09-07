# BlackBlaze B2 Backup Tool

A cross-platform GUI application for backing up local folders to BackBlaze B2 S3 buckets with automatic scheduling and background operation.

## Features

- **Cross-platform**: Runs on Windows 11 and Ubuntu 24.04
- **Modern GUI**: Clean, minimalistic interface built with PySide6 (Qt for Python)
- **Background Operation**: Runs backups in the background with system tray support
- **Automatic Scheduling**: Set up automatic backups (1min, 5min, 15min, hourly, daily, weekly, monthly)
- **Flexible Backup Options**:
  - Upload all folders to a single bucket
  - Upload different folders to different buckets
- **Secure Credential Storage**: Encrypted credential storage using system keyring
- **Real-time Progress**: Live progress bars and status updates
- **Error Handling**: Comprehensive error reporting and logging
- **Fast Package Management**: Uses `uv` for lightning-fast dependency management
- ** Persistent Configuration**: Automatically remembers folders, schedules, and settings
- ** Organized Storage**: Files are organized in S3 with proper folder structure
- **Incremental Backups**: Only upload changed files for faster, efficient backups
- ** Concurrent Protection**: Prevents multiple backup operations from interfering
- **Easy Installation**: MSI installer for Windows, DEB package for Ubuntu
- **Auto-Updates**: Automatic uninstallation of older versions during MSI installation

## Quick Start

### Install from Releases (Recommended)

**Windows:**
1. Download `BlackBlaze-Backup-Tool-v1.0.43.msi` from [Releases](https://github.com/reshdesu/blackblaze2-backup/releases)
2. Run the MSI installer (no admin rights required)
3. Launch from Start Menu or Desktop shortcut

**Ubuntu:**
1. Download `blackblaze-backup-tool_amd64_v1.0.43.deb` from [Releases](https://github.com/reshdesu/blackblaze2-backup/releases)
2. Install with: `sudo dpkg -i blackblaze-backup-tool_amd64_v1.0.43.deb`
3. Launch from Applications menu

### Development Setup

**One-Line Command (Easiest)**
```bash
git clone https://github.com/reshdesu/blackblaze2-backup.git && cd blackblaze2-backup && uv run bb2backup
```

**Using uv (Recommended)**
```bash
# Clone the repository
git clone https://github.com/reshdesu/blackblaze2-backup.git
cd blackblaze2-backup

# Run directly with uv (installs dependencies automatically)
uv run bb2backup
```

## Configuration

### 1. Configure Credentials

Copy the sample environment file and add your BackBlaze B2 credentials:

```bash
cp sample.env .env
# Edit .env with your actual credentials
```

**Required credentials:**
- `B2_ENDPOINT`: Your BackBlaze B2 S3 endpoint (e.g., `s3.us-east-005.backblazeb2.com`)
- `B2_ACCESS_KEY_ID`: Your BackBlaze B2 application key ID
- `B2_SECRET_ACCESS_KEY`: Your BackBlaze B2 application key
- `B2_REGION`: Your BackBlaze B2 region (e.g., `us-east-005`)

### 2. Get BackBlaze B2 Credentials

1. Create a BackBlaze B2 account at [backblaze.com](https://www.backblaze.com/b2-cloud-storage.html)
2. Go to "App Keys" in your B2 account
3. Create a new Application Key (not Master Key) with S3-compatible API access
4. Note your S3 endpoint URL from the Buckets page
5. Use the Application Key ID and Application Key as your credentials

##  Usage

### 1. **Configure Credentials**
   - Go to the "Credentials" tab
   - Enter your BackBlaze B2 S3 endpoint, access key, secret key, and region
   - Test the connection to verify your credentials
   - Click "Save Credentials" - they'll be stored securely

### 2. **Select Folders**
   - Go to the "Folders" tab
   - Click "Add Folder" to select folders to backup
   - Choose between single bucket or multiple bucket mode
   - Configure bucket names for each folder
   - Your selections are automatically saved

### 3. **Start Backup**
   - Go to the "Backup" tab
   - Click "Start Backup" to begin the process
   - Monitor progress and status updates
   - Cancel if needed
   - Files are organized in S3 with proper folder structure

### 4. **Schedule Automatic Backups**
   - Click "Schedule Automatic Backups" button
   - Choose frequency (1min, 5min, 15min, hourly, daily, weekly, monthly)
   - Set backup time (for non-hourly schedules)
   - Your schedule is automatically saved
   - **Concurrent Protection**: Scheduled backups won't interfere with manual uploads

### 5. **Background Operation**
   - When you close the app, it minimizes to system tray
   - Scheduled backups run automatically in the background
   - Right-click the tray icon for quick actions (Show Window, Start Backup, Schedule, Exit)
   - The app automatically kills older instances when starting
   - **Incremental Backups**: Only changed files are uploaded for efficiency

##  Testing

### Run Comprehensive Test Suite

```bash
# Run all tests including test data creation and backup testing
uv run python tests/integration/run_tests.py
```

### Create Test Data

```bash
# Create test folder structure with various file types
uv run python tests/integration/create_test_data.py
```

### Individual Tests

```bash
# Unit tests
uv run pytest tests/test_core.py -v

# GUI tests
uv run pytest tests/test_gui.py -v

# All tests
uv run pytest tests/ -v
```

## Building from Source

For development purposes, you can build the application locally:

### Prerequisites
- Python 3.9+ with `uv` package manager
- Platform-specific dependencies (see [Development Setup](#-development) above)

### Build Commands
```bash
# Install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[build]"

# Build executable
pyinstaller --clean --log-level=ERROR blackblaze_backup.spec
```

**Note**: For production use, we recommend downloading pre-built packages from [GitHub Releases](https://github.com/reshdesu/blackblaze2-backup/releases) instead of building locally.

## Development

### Using uv for Development

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run the application
uv run bb2backup

# Run tests
uv run pytest

# Format code (automatic with pre-commit hooks)
uv run ruff format .

# Lint code (automatic with pre-commit hooks)
uv run ruff check .

# Type checking
uv run mypy src/
```

## Security

- **Encrypted Storage**: Credentials are encrypted using Fernet encryption
- **System Keyring**: Stored securely in the system keyring
- **No Plain Text**: No credentials are stored in plain text
- **Git Protection**: `.gitignore` configured to prevent accidental secret commits
- **Input Validation**: All credential inputs are validated before saving

##  Troubleshooting

- **Check Logs**:
  - **Windows**: `%USERPROFILE%\.blackblaze_backup\blackblaze_backup.log`
  - **Ubuntu**: `~/.blackblaze_backup/blackblaze_backup.log`
- **Permissions**: Ensure your BackBlaze B2 Application Key has necessary permissions
- **Endpoint**: Verify your S3 endpoint URL is correct
- **Disk Space**: Make sure you have sufficient disk space for temporary files
- **Network**: Check your internet connection for upload issues
- **Concurrent Backups**: If you see duplicate uploads, check that only one backup is running
- **Installation Issues**:
  - **Windows**: Try running MSI as administrator if shortcuts don't work
  - **Ubuntu**: See detailed troubleshooting guide below

## Ubuntu Installation Troubleshooting

If you encounter installation issues on Ubuntu, try these solutions:

### Quick Fix
```bash
# Remove any broken installation
sudo dpkg --remove --force-remove-reinstreq blackblaze-backup-tool

# Install fresh package
sudo apt install ./blackblaze-backup-tool_amd64_v*.deb
```

### Common Issues

#### Package Stuck in "iHR" State
```bash
# Check status
dpkg -l | grep blackblaze

# Force remove and reinstall
sudo dpkg --remove --force-remove-reinstreq blackblaze-backup-tool
sudo apt install ./blackblaze-backup-tool_amd64_v*.deb
```

#### Installation Interrupted
```bash
# Complete interrupted installations
sudo dpkg --configure -a
sudo apt-get install -f
```

#### Dependency Issues
```bash
# Update system and fix dependencies
sudo apt update
sudo apt-get install -f
sudo apt install ./blackblaze-backup-tool_amd64_v*.deb
```

### Alternative Installation Methods
- **GDebi**: `sudo apt install gdebi && sudo gdebi *.deb`
- **Software Center**: Double-click the DEB file
- **Manual**: Extract and copy files manually

### Getting Help
If issues persist, please include:
- Ubuntu version: `lsb_release -a`
- Architecture: `uname -m`
- Package status: `dpkg -l | grep blackblaze`
- Installation log: `sudo apt install ./blackblaze-backup-tool_amd64_v*.deb 2>&1 | tee install.log`

## Why uv?

We use `uv` instead of traditional pip because it's:
- **10-100x faster** than pip for package installation
- **More reliable** with better dependency resolution
- **Modern** with built-in virtual environment management
- **Cross-platform** with excellent Windows and Linux support

## Requirements

- Python 3.8 or higher
- BackBlaze B2 account with S3-compatible API access
- `uv` package manager (automatically installed by build scripts)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

We welcome contributions! Please see our [CONTRIBUTORS](CONTRIBUTORS.md) and [SECURITY](SECURITY.md) files for guidelines.

### Development Setup

For developers, we provide an automated setup script:

```bash
# Run the development setup script
./setup-dev.sh
```

This script will:
- Install pre-commit hooks
- Set up automatic code formatting
- Fix any existing formatting issues
- Ensure consistent code style

**Pre-commit hooks automatically:**
- Format code with `ruff`
- Remove trailing whitespace
- Fix end-of-file issues
- Check YAML syntax
- Prevent large files and merge conflicts

**Manual setup:**
```bash
# Install dependencies
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run formatting on all files
pre-commit run --all-files
```

##  Acknowledgments

- Built with [PySide6](https://pypi.org/project/PySide6/) for cross-platform GUI
- Uses [uv](https://github.com/astral-sh/uv) for fast package management
- Integrates with [BackBlaze B2](https://www.backblaze.com/b2-cloud-storage.html) S3-compatible API
- Secure credential storage powered by [keyring](https://pypi.org/project/keyring/) and [cryptography](https://pypi.org/project/cryptography/)

## Project Status

**Core Features Complete**
- Cross-platform GUI application (Windows 11 & Ubuntu 24.04)
- Secure credential management with system keyring
- Background operation with system tray support
- Automatic scheduling (1min, 5min, 15min, hourly, daily, weekly, monthly)
- Real-time progress tracking and status updates
- Organized S3 storage structure with proper folder hierarchy
- Persistent configuration with auto-save
- Comprehensive error handling and logging
- Incremental backup support for efficiency
- Concurrent backup protection to prevent conflicts

**Packaging & Distribution Complete**
- MSI installer for Windows with automatic upgrades
- DEB package for Ubuntu with proper dependencies
- GitHub Actions CI/CD pipeline with automated releases
- Versioned packages with dynamic versioning
- Cross-platform build system using uv

**Testing Complete**
- Unit tests for core functionality
- GUI tests for user interface
- Integration tests with real S3 connectivity
- Automated test data creation
- CI/CD pipeline with GitHub Actions
- Pre-commit hooks for code quality

**Documentation Complete**
- Comprehensive README with installation instructions
- Security guidelines and best practices
- Contributing guidelines with development setup
- Build instructions for both platforms
- Troubleshooting guide with log locations
