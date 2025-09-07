# BlackBlaze B2 Backup Tool

A cross-platform GUI application for backing up local folders to BackBlaze B2 S3 buckets with automatic scheduling and background operation.

## ✨ Features

- **🖥️ Cross-platform**: Runs on Windows 11 and Ubuntu 24.04
- **🎨 Modern GUI**: Clean, minimalistic interface built with PySide6 (Qt for Python)
- **🔄 Background Operation**: Runs backups in the background with system tray support
- **⏰ Automatic Scheduling**: Set up automatic backups (hourly, daily, weekly, monthly)
- **📁 Flexible Backup Options**:
  - Upload all folders to a single bucket
  - Upload different folders to different buckets
- **🔐 Secure Credential Storage**: Encrypted credential storage using system keyring
- **📊 Real-time Progress**: Live progress bars and status updates
- **🛡️ Error Handling**: Comprehensive error reporting and logging
- **⚡ Fast Package Management**: Uses `uv` for lightning-fast dependency management
- **💾 Persistent Configuration**: Automatically remembers folders, schedules, and settings
- **📂 Organized Storage**: Files are organized in S3 with proper folder structure

## 🚀 Quick Start

### One-Line Command (Easiest)
```bash
git clone https://github.com/reshdesu/blackblaze2-backup.git && cd blackblaze2-backup && uv run bb2backup
```

### Using uv (Recommended)
```bash
# Clone the repository
git clone https://github.com/reshdesu/blackblaze2-backup.git
cd blackblaze2-backup

# Run directly with uv (installs dependencies automatically)
uv run bb2backup
```

## 🔧 Configuration

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

## 📖 Usage

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
   - Choose frequency (hourly, daily, weekly, monthly)
   - Set backup time (for non-hourly schedules)
   - Your schedule is automatically saved

### 5. **Background Operation**
   - When you close the app, it minimizes to system tray
   - Scheduled backups run automatically in the background
   - Right-click the tray icon for quick actions (Show Window, Start Backup, Schedule, Exit)
   - The app automatically kills older instances when starting

## 🧪 Testing

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

## 🏗️ Building Executables

### Ubuntu 24.04
```bash
chmod +x build_ubuntu.sh
./build_ubuntu.sh
```

### Windows
```cmd
build_windows.bat
```

## 🛠️ Development

### Using uv for Development

```bash
# Install development dependencies
uv add --dev pytest black flake8 mypy pre-commit

# Run the application
uv run bb2backup

# Run tests
uv run pytest

# Format code
uv run black .

# Lint code
uv run flake8 .

# Type checking
uv run mypy src/
```

## 🔒 Security

- **Encrypted Storage**: Credentials are encrypted using Fernet encryption
- **System Keyring**: Stored securely in the system keyring
- **No Plain Text**: No credentials are stored in plain text
- **Git Protection**: `.gitignore` configured to prevent accidental secret commits
- **Input Validation**: All credential inputs are validated before saving

## 🐛 Troubleshooting

- **Check Logs**: Look at `blackblaze_backup.log` for detailed error messages
- **Permissions**: Ensure your BackBlaze B2 Application Key has necessary permissions
- **Endpoint**: Verify your S3 endpoint URL is correct
- **Disk Space**: Make sure you have sufficient disk space for temporary files
- **Network**: Check your internet connection for upload issues

## ⚡ Why uv?

We use `uv` instead of traditional pip because it's:
- **10-100x faster** than pip for package installation
- **More reliable** with better dependency resolution
- **Modern** with built-in virtual environment management
- **Cross-platform** with excellent Windows and Linux support

## 📋 Requirements

- Python 3.8 or higher
- BackBlaze B2 account with S3-compatible API access
- `uv` package manager (automatically installed by build scripts)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

We welcome contributions! Please see our [CONTRIBUTORS](CONTRIBUTORS.md) and [SECURITY](SECURITY.md) files for guidelines.

## 🙏 Acknowledgments

- Built with [PySide6](https://pypi.org/project/PySide6/) for cross-platform GUI
- Uses [uv](https://github.com/astral-sh/uv) for fast package management
- Integrates with [BackBlaze B2](https://www.backblaze.com/b2-cloud-storage.html) S3-compatible API
- Secure credential storage powered by [keyring](https://pypi.org/project/keyring/) and [cryptography](https://pypi.org/project/cryptography/)

## 📊 Project Status

✅ **Core Features Complete**
- Cross-platform GUI application
- Secure credential management
- Background operation with system tray
- Automatic scheduling (hourly, daily, weekly, monthly)
- Real-time progress tracking
- Organized S3 storage structure
- Persistent configuration
- Comprehensive error handling

✅ **Testing Complete**
- Unit tests for core functionality
- GUI tests for user interface
- Integration tests with real S3 connectivity
- Automated test data creation
- CI/CD pipeline with GitHub Actions

✅ **Documentation Complete**
- Comprehensive README
- Security guidelines
- Contributing guidelines
- Build instructions for both platforms
