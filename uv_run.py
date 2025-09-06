#!/usr/bin/env python3
"""
UV Run Script for BlackBlaze B2 Backup Tool
Handles dependency resolution and runs the application
"""

import subprocess
import sys
import os
from pathlib import Path

def check_uv_installed():
    """Check if uv is installed"""
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_uv():
    """Install uv package manager"""
    print("Installing uv package manager...")
    try:
        if os.name == 'nt':  # Windows
            subprocess.run([
                "powershell", "-c", 
                "irm https://astral.sh/uv/install.ps1 | iex"
            ], check=True)
        else:  # Unix-like systems
            subprocess.run([
                "curl", "-LsSf", "https://astral.sh/uv/install.sh"
            ], stdout=subprocess.PIPE, check=True)
            subprocess.run(["sh"], input=subprocess.PIPE, check=True)
        print("uv installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install uv: {e}")
        return False

def run_with_uv():
    """Run the application using uv"""
    script_dir = Path(__file__).parent
    
    try:
        # Try to run with uv run
        print("Starting BlackBlaze B2 Backup Tool with uv...")
        subprocess.run([
            "uv", "run", "--python", "3.12", "python", str(script_dir / "main.py")
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running with uv: {e}")
        print("Trying alternative approach...")
        
        # Fallback: create venv and install dependencies
        try:
            subprocess.run(["uv", "venv"], check=True)
            
            if os.name == 'nt':  # Windows
                activate_cmd = str(script_dir / ".venv" / "Scripts" / "activate.bat")
                subprocess.run([activate_cmd, "&&", "uv", "pip", "install", "-e", "."], 
                             shell=True, check=True)
                subprocess.run([activate_cmd, "&&", "python", str(script_dir / "main.py")], 
                             shell=True, check=True)
            else:  # Unix-like systems
                activate_cmd = f"source {script_dir}/.venv/bin/activate"
                subprocess.run(f"{activate_cmd} && uv pip install -e .", 
                             shell=True, check=True)
                subprocess.run(f"{activate_cmd} && python {script_dir}/main.py", 
                             shell=True, check=True)
        except subprocess.CalledProcessError as e2:
            print(f"Fallback also failed: {e2}")
            print("Please install dependencies manually:")
            print("  uv venv")
            print("  source .venv/bin/activate  # or .venv\\Scripts\\activate.bat on Windows")
            print("  uv pip install -e .")
            print("  python main.py")
            sys.exit(1)

def main():
    """Main entry point"""
    print("BlackBlaze B2 Backup Tool - UV Runner")
    print("=" * 40)
    
    # Check if uv is installed
    if not check_uv_installed():
        print("uv not found. Installing...")
        if not install_uv():
            print("Failed to install uv. Please install manually:")
            print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
            sys.exit(1)
    
    # Run the application
    run_with_uv()

if __name__ == "__main__":
    main()
