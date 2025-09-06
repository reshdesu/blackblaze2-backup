@echo off
REM Simple script to run BlackBlaze B2 Backup Tool with uv on Windows

echo Starting BlackBlaze B2 Backup Tool...

REM Check if uv is installed
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing uv package manager...
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
)

REM Run the application
uv run python main.py
pause
