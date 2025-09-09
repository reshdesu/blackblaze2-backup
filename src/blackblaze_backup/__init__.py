"""
BlackBlaze B2 Backup Tool

A cross-platform GUI application for backing up local folders to BackBlaze B2 S3 buckets.
"""

__version__ = "1.0.86"
__author__ = "reshdesu & Claude (Anthropic)"
__email__ = "reshdesu@users.noreply.github.com"
__description__ = "A cross-platform GUI application for backing up local folders to BackBlaze B2 S3 buckets"

from .core import (
    BackupConfig,
    BackupManager,
    BackupProgressTracker,
    BackupService,
    CredentialManager,
)

# Import GUI components only when available (avoid CI issues)
try:
    from .gui import BlackBlazeBackupApp, main

    # Run post-install setup on first import (only in development)
    try:
        import sys
        from pathlib import Path

        # Check if we're running from a packaged application
        # PyInstaller sets sys.frozen and sys._MEIPASS when bundled
        is_packaged = getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")

        # Also check if we're running from a system-installed package
        # System packages have files in /usr/share/ or C:\Program Files\
        # Development runs from source directory
        package_dir = Path(__file__).parent
        is_system_package = (
            str(package_dir).startswith("/usr/")  # Linux system package
            or str(package_dir).startswith(
                "C:\\Program Files\\"
            )  # Windows system package
            or str(package_dir).startswith(
                "C:\\Program Files (x86)\\"
            )  # Windows 32-bit system package
        )

        # Only run post-install in development mode (not packaged, not system package)
        if not is_packaged and not is_system_package:
            from .post_install import install_desktop_entry

            install_desktop_entry()
    except Exception:  # nosec B110
        pass  # Silently continue if post-install fails

    _GUI_AVAILABLE = True
except ImportError:
    # GUI not available (e.g., in CI environment without Qt)
    BlackBlazeBackupApp = None
    main = None
    _GUI_AVAILABLE = False

__all__ = [
    "BackupService",
    "BackupManager",
    "BackupConfig",
    "BackupProgressTracker",
    "CredentialManager",
    "__version__",
    "__author__",
    "__email__",
    "__description__",
]

# Add GUI components to __all__ only if available
if _GUI_AVAILABLE:
    __all__.extend(["BlackBlazeBackupApp", "main"])
