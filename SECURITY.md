# Security Policy for BlackBlaze B2 Backup Tool

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Security Guidelines

### Credential Management
- **NEVER** commit credentials, API keys, or secrets to the repository
- Use the built-in secure credential storage feature
- Credentials are encrypted and stored in the system keyring
- If you accidentally commit secrets, immediately rotate them

### File Exclusions
The following files are automatically excluded from version control:
- `*.log` - Log files may contain sensitive information
- `credentials.json` - Credential files
- `secrets.json` - Secret configuration files
- `config.json` - Configuration files that may contain secrets
- `.env*` - Environment files
- `*.key`, `*.pem`, `*.p12`, `*.pfx` - Certificate and key files

### Pre-commit Hooks
Consider setting up pre-commit hooks to scan for secrets:
```bash
pip install pre-commit
pre-commit install
```

### Reporting Security Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

1. **DO NOT** create a public issue
2. Email security concerns to: [your-email@example.com]
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Security Best Practices

1. **Regular Updates**: Keep dependencies updated
2. **Credential Rotation**: Regularly rotate BackBlaze B2 API keys
3. **Access Control**: Use least-privilege principle for API keys
4. **Monitoring**: Monitor backup logs for unusual activity
5. **Encryption**: All credentials are encrypted at rest

### Dependencies Security

We use `uv` for fast and secure dependency management:
- Automatic vulnerability scanning
- Lock file integrity verification
- Minimal attack surface

## Contact

For security-related questions or concerns, please contact the maintainers.
