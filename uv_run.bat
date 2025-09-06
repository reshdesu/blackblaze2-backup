@echo off
REM UV Run Script for BlackBlaze B2 Backup Tool (Windows)

echo BlackBlaze B2 Backup Tool - UV Runner
echo ======================================

REM Check if uv is installed
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing uv package manager...
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
)

REM Try different approaches to run with uv
echo Starting BlackBlaze B2 Backup Tool...

REM Method 1: Try uv run with specific Python version
uv run --python 3.12 python main.py
if %errorlevel% equ 0 (
    echo Application started successfully!
    pause
    exit /b 0
)

REM Method 2: Create venv and install dependencies
echo Creating virtual environment and installing dependencies...
uv venv --python 3.12
call .venv\Scripts\activate.bat
uv pip install -e .

REM Run the application
echo Starting application...
python main.py
pause
