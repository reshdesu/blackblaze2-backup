#!/usr/bin/env python3
"""
Format checking script to ensure all Python files are properly formatted.
This script can be run manually or integrated into CI/CD pipelines.
"""

import subprocess
import sys


def check_formatting():
    """Check if all Python files are properly formatted."""
    print("Checking Python code formatting...")

    # Directories to check
    directories = ["src/", "tests/", "main.py"]

    # Run ruff format --check
    try:
        result = subprocess.run(
            ["ruff", "format", "--check"] + directories,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            print("All Python files are properly formatted!")
            return True
        else:
            print("Formatting issues found:")
            print(result.stdout)
            if result.stderr:
                print("Errors:")
                print(result.stderr)
            return False

    except FileNotFoundError:
        print("Error: ruff not found. Please install ruff first.")
        return False
    except Exception as e:
        print(f"Error running ruff: {e}")
        return False


def fix_formatting():
    """Fix formatting issues automatically."""
    print("Fixing Python code formatting...")

    directories = ["src/", "tests/", "main.py"]

    try:
        result = subprocess.run(
            ["ruff", "format"] + directories,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            print("Formatting fixed successfully!")
            if result.stdout:
                print("Files reformatted:")
                print(result.stdout)
            return True
        else:
            print("Error fixing formatting:")
            print(result.stderr)
            return False

    except FileNotFoundError:
        print("Error: ruff not found. Please install ruff first.")
        return False
    except Exception as e:
        print(f"Error running ruff: {e}")
        return False


def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--fix":
        success = fix_formatting()
    else:
        success = check_formatting()
        if not success:
            print("\nTip: Run with --fix to automatically fix formatting issues:")
            print("   python scripts/check-formatting.py --fix")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
