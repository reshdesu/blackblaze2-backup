@echo off
REM Build script for Windows using uv

echo Building BlackBlaze B2 Backup Tool for Windows...

REM Install uv if not already installed
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing uv package manager...
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
)

REM Create virtual environment and install dependencies
uv venv
call .venv\Scripts\activate.bat
uv pip install -e ".[build]"

REM Create executable using spec file
pyinstaller --clean blackblaze_backup.spec

echo Build complete! Executable created in dist\ directory
echo To run: dist\BlackBlaze-Backup-Tool.exe
pause
