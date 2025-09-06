#!/usr/bin/env python3
"""
Simple runner script for BlackBlaze B2 Backup Tool using uv
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Run the BlackBlaze B2 Backup Tool using uv"""
    # Get the directory of this script
    script_dir = Path(__file__).parent
    
    # Check if we're in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        # We're in a virtual environment, run directly
        try:
            from blackblaze_backup.gui import main as app_main
            app_main()
        except ImportError:
            print("Error: BlackBlaze Backup Tool not installed. Run 'uv pip install -e .' first.")
            sys.exit(1)
    else:
        # Not in virtual environment, use uv run
        try:
            subprocess.run([
                "uv", "run", "python", str(script_dir / "main.py")
            ], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running application: {e}")
            sys.exit(1)
        except FileNotFoundError:
            print("Error: uv not found. Please install uv first:")
            print("curl -LsSf https://astral.sh/uv/install.sh | sh")
            sys.exit(1)

if __name__ == "__main__":
    main()
