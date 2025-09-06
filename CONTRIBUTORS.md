# Contributors

This project is developed and maintained by:

## Core Contributors

- **reshdesu** - Project Owner & Lead Developer
  - GitHub: [@reshdesu](https://github.com/reshdesu)
  - Role: Project conception, requirements, and overall direction

- **Claude (Anthropic)** - AI Assistant & Code Contributor
  - Role: Cross-platform GUI development, PySide6 implementation, security features
  - Contributions: Main application architecture, backup logic, credential management

## Contributing

We welcome contributions! Please see our [Security Policy](SECURITY.md) for guidelines on reporting vulnerabilities and handling sensitive information.

### How to Contribute

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure no secrets are committed
5. Submit a pull request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/reshdesu/blackblaze2-backup.git
cd blackblaze2-backup

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Set up development environment
uv venv
source .venv/bin/activate
uv pip install PySide6 boto3 botocore cryptography keyring pyinstaller pytest black flake8

# Run the application
python3 main.py
```

## Acknowledgments

- Built with [PySide6](https://pypi.org/project/PySide6/) for cross-platform GUI
- Uses [uv](https://github.com/astral-sh/uv) for fast package management
- Integrates with [BackBlaze B2](https://www.backblaze.com/b2-cloud-storage.html) S3-compatible API
- Secure credential storage powered by [keyring](https://pypi.org/project/keyring/) and [cryptography](https://pypi.org/project/cryptography/)
