# BlackBlaze B2 Backup Tool

A cross-platform GUI application for backing up local folders to BackBlaze B2 S3 buckets.

## Features

- **Cross-platform**: Runs on Windows and Ubuntu 24.04
- **Simple GUI**: Minimalistic interface built with PySide6 (Qt for Python)
- **Flexible Backup Options**:
  - Upload all folders to a single bucket
  - Upload different folders to different buckets
- **Secure Credential Storage**: Encrypted credential storage using system keyring
- **Progress Tracking**: Real-time progress bars and status updates
- **Error Handling**: Comprehensive error reporting and logging
- **Modern Package Management**: Uses `uv` for fast dependency management

## Requirements

- Python 3.8 or higher
- BackBlaze B2 account with S3-compatible API access
- `uv` package manager (automatically installed by build scripts)

## Quick Start

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

### Using Run Scripts
```bash
# Ubuntu/Linux
./run.sh

# Windows
run.bat

# Cross-platform Python script
python run.py
```

### Traditional Installation

### Ubuntu 24.04

1. Install Python 3 and uv:
```bash
sudo apt update
sudo apt install python3 python3-pip
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

2. Clone or download this repository
3. Install dependencies:
```bash
uv venv
source .venv/bin/activate
uv pip install PySide6 boto3 botocore cryptography keyring
```

4. Run the application:
```bash
# Using uv (recommended)
uv run python main.py

# Or using the run script
./run.sh

# Or directly with Python
python3 main.py
```

### Windows

1. Install Python 3.8+ from [python.org](https://python.org)
2. Install uv:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

3. Clone or download this repository
4. Install dependencies:
```cmd
uv venv
.venv\Scripts\activate
uv pip install PySide6 boto3 botocore cryptography keyring
```

5. Run the application:
```cmd
REM Using uv (recommended)
uv run python main.py

REM Or using the run script
run.bat

REM Or directly with Python
python main.py
```

## Building Executables

### Ubuntu 24.04
```bash
chmod +x build_ubuntu.sh
./build_ubuntu.sh
```

### Windows
```cmd
build_windows.bat
```

## Development

### Using uv for Development

```bash
# Install development dependencies
uv pip install pyinstaller pytest black flake8

# Run the application
python3 main.py

# Run tests
pytest

# Format code
black .

# Lint code
flake8 .
```

## Usage

1. **Configure Credentials**: 
   - Go to the "Credentials" tab
   - Enter your BackBlaze B2 S3 endpoint, access key, secret key, and region
   - Test the connection to verify your credentials
   - Save credentials securely for future use

2. **Select Folders**:
   - Go to the "Folders" tab
   - Click "Add Folder" to select folders to backup
   - Choose between single bucket or multiple bucket mode
   - Configure bucket names for each folder

3. **Start Backup**:
   - Go to the "Backup" tab
   - Click "Start Backup" to begin the process
   - Monitor progress and status updates
   - Cancel if needed

## BackBlaze B2 Setup

1. Create a BackBlaze B2 account
2. Create an Application Key (not Master Key) with S3-compatible API access
3. Note your S3 endpoint URL from the Buckets page
4. Use the Application Key ID and Application Key as your credentials

## Security

- Credentials are encrypted using Fernet encryption
- Stored securely in the system keyring
- No credentials are stored in plain text
- `.gitignore` configured to prevent accidental secret commits

## Troubleshooting

- Check the log file `blackblaze_backup.log` for detailed error messages
- Ensure your BackBlaze B2 Application Key has the necessary permissions
- Verify your S3 endpoint URL is correct
- Make sure you have sufficient disk space for temporary files during upload

## Why uv?

We use `uv` instead of traditional pip because it's:
- **10-100x faster** than pip for package installation
- **More reliable** with better dependency resolution
- **Modern** with built-in virtual environment management
- **Cross-platform** with excellent Windows and Linux support

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

We welcome contributions! Please see our [CONTRIBUTORS](CONTRIBUTORS.md) and [SECURITY](SECURITY.md) files for guidelines.

## Acknowledgments

- Built with [PySide6](https://pypi.org/project/PySide6/) for cross-platform GUI
- Uses [uv](https://github.com/astral-sh/uv) for fast package management  
- Integrates with [BackBlaze B2](https://www.backblaze.com/b2-cloud-storage.html) S3-compatible API
- Secure credential storage powered by [keyring](https://pypi.org/project/keyring/) and [cryptography](https://pypi.org/project/cryptography/)