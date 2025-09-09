#!/usr/bin/env python3
"""
Pre-commit hook to check for secrets and credentials in files.
"""
import os
import re
import sys


def check_for_secrets():
    """Check files for potential secrets and credentials."""
    # Skip documentation files that might contain examples
    skip_files = ["AI_CONTEXT.json", "README.md", "DEVELOPMENT.md", "docs/"]

    secret_patterns = [
        # Common credential patterns (more specific to avoid false positives)
        r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{3,}["\'](?!\s*[,}])',  # At least 3 chars, not in JSON
        r'(?i)(api_key|apikey|access_key)\s*=\s*["\'][^"\']{5,}["\'](?!\s*[,}])',  # At least 5 chars, not in JSON
        r'(?i)(secret|token|auth_token)\s*=\s*["\'][^"\']{5,}["\'](?!\s*[,}])',  # At least 5 chars, not in JSON
        r'(?i)(database_url|db_url|connection_string)\s*=\s*["\'][^"\']{10,}["\'](?!\s*[,}])',  # At least 10 chars, not in JSON
        # Specific token patterns
        r"(?i)sk-[a-zA-Z0-9]{20,}",  # OpenAI API keys
        r"(?i)AKIA[0-9A-Z]{16}",  # AWS Access Key ID
        r'(?i)aws_secret_access_key\s*=\s*["\'][0-9a-zA-Z/+]{40}["\']',  # AWS Secret Access Key
        r"(?i)ghp_[a-zA-Z0-9]{36}",  # GitHub Personal Access Token
        r"(?i)gho_[a-zA-Z0-9]{36}",  # GitHub OAuth Token
        r"(?i)ghu_[a-zA-Z0-9]{36}",  # GitHub User Token
        r"(?i)ghs_[a-zA-Z0-9]{36}",  # GitHub Server Token
        r"(?i)ghr_[a-zA-Z0-9]{36}",  # GitHub Refresh Token
        # Additional patterns
        r"(?i)bearer\s+[a-zA-Z0-9\-._~+/]{10,}=*",  # Bearer tokens (at least 10 chars)
        r"(?i)authorization\s*:\s*[a-zA-Z0-9\-._~+/]{10,}=*",  # Authorization headers
    ]

    files_with_secrets = []

    for file_path in sys.argv[1:]:
        if not os.path.exists(file_path):
            continue

        # Skip documentation files
        if any(skip_file in file_path for skip_file in skip_files):
            continue

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

                for pattern in secret_patterns:
                    match = re.search(pattern, content)
                    if match:
                        files_with_secrets.append(
                            f"{file_path}: Potential secret found (pattern: {pattern[:50]}...)"
                        )
                        break

        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            continue

    if files_with_secrets:
        print("SECURITY WARNING: Potential secrets detected!")
        for warning in files_with_secrets:
            print(f"  {warning}")
        print("Please remove secrets before committing.")
        print("Common secrets to avoid:")
        print("  - Passwords, API keys, tokens")
        print("  - Database connection strings with credentials")
        print("  - AWS keys, GitHub tokens")
        print("  - Any hardcoded credentials")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(check_for_secrets())
