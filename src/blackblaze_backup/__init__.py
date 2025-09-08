"""
BlackBlaze B2 Backup Tool

A cross-platform GUI application for backing up local folders to BackBlaze B2 S3 buckets.
"""

__version__ = "1.0.77"
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

    # Run post-install setup on first import
    try:
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
