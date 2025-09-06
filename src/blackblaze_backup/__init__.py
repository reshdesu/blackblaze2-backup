"""
BlackBlaze B2 Backup Tool

A cross-platform GUI application for backing up local folders to BackBlaze B2 S3 buckets.
"""

__version__ = "1.0.0"
__author__ = "reshdesu & Claude (Anthropic)"
__email__ = "reshdesu@users.noreply.github.com"
__description__ = "A cross-platform GUI application for backing up local folders to BackBlaze B2 S3 buckets"

from .core import (
    BackupService,
    BackupManager,
    BackupConfig,
    BackupProgressTracker,
    CredentialManager
)
from .gui import BlackBlazeBackupApp

__all__ = [
    "BackupService",
    "BackupManager", 
    "BackupConfig",
    "BackupProgressTracker",
    "CredentialManager",
    "BlackBlazeBackupApp",
    "__version__",
    "__author__",
    "__email__",
    "__description__"
]
