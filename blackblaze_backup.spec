# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Get the current directory
current_dir = Path.cwd()

# Define the main script
main_script = current_dir / 'main.py'

# Define the icon file (convert SVG to ICO if needed)
icon_file = current_dir / 'src' / 'blackblaze_backup' / 'icon.ico'

# Check if icon exists, if not use a default
if not icon_file.exists():
    icon_file = None

# Hidden imports for PySide6 and other dependencies
hidden_imports = [
    'PySide6.QtCore',
    'PySide6.QtGui', 
    'PySide6.QtWidgets',
    'PySide6.QtNetwork',
    'PySide6.QtOpenGL',
    'PySide6.QtPrintSupport',
    'PySide6.QtSql',
    'PySide6.QtSvg',
    'PySide6.QtTest',
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebSockets',
    'PySide6.QtXml',
    'boto3',
    'botocore',
    'botocore.exceptions',
    'botocore.vendored.requests',
    'cryptography',
    'cryptography.fernet',
    'keyring',
    'keyring.backends',
    'keyring.backends.Windows',
    'keyring.backends.macOS',
    'keyring.backends.SecretService',
    'PIL',
    'PIL.Image',
    'dotenv',
    'json',
    'logging',
    'pathlib',
    'threading',
    'queue',
]

# Data files to include
datas = []

# Add icon if it exists
if icon_file and icon_file.exists():
    datas.append((str(icon_file), '.'))

# Analysis configuration
a = Analysis(
    [str(main_script)],
    pathex=[str(current_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'jupyter',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Filter out problematic Windows API libraries
filtered_binaries = []
for binary in a.binaries:
    # Skip Windows API libraries that cause warnings
    if any(api_lib in binary[0] for api_lib in [
        'api-ms-win-core-path-l1-1-0.dll',
        'api-ms-win-shcore-scaling-l1-1-1.dll',
        'api-ms-win-core-winrt-string-l1-1-0.dll',
        'api-ms-win-core-winrt-l1-1-0.dll',
        'api-ms-win-core-synch-l1-2-0.dll',
        'api-ms-win-core-sysinfo-l1-2-1.dll',
        'api-ms-win-core-processthreads-l1-1-2.dll',
    ]):
        continue
    filtered_binaries.append(binary)

a.binaries = filtered_binaries

# PYZ configuration
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# EXE configuration
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BlackBlaze-Backup-Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file) if icon_file and icon_file.exists() else None,
    version_file=None,
)