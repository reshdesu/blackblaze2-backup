@echo off
REM Build script for Windows using uv with PyInstaller warnings handling

echo Building BlackBlaze B2 Backup Tool for Windows...
echo.

REM Install uv if not already installed
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing uv package manager...
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
)

REM Create virtual environment and install dependencies
echo Creating virtual environment...
uv venv
call .venv\Scripts\activate.bat

echo Installing dependencies...
uv pip install -e ".[build]"

REM Clean previous builds
echo Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM Create executable using spec file with warning suppression
echo Building executable...
pyinstaller --clean --log-level=ERROR blackblaze_backup.spec 2>nul

REM Check if build was successful
if exist "dist\BlackBlaze-Backup-Tool.exe" (
    echo.
    echo ✅ Build successful!
    echo Executable created: dist\BlackBlaze-Backup-Tool.exe
    echo.
    echo To run the application:
    echo   dist\BlackBlaze-Backup-Tool.exe
    echo.
) else (
    echo.
    echo ❌ Build failed!
    echo Check the build logs for errors.
    echo.
)

pause
