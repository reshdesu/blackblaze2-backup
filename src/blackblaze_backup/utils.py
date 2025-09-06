"""
Utilities and helper functions for BlackBlaze B2 Backup Tool
"""

import os
import hashlib
from pathlib import Path
from typing import List, Optional, Tuple
import mimetypes


def get_file_hash(file_path: Path, algorithm: str = 'md5') -> str:
    """Calculate hash of a file"""
    hash_obj = hashlib.new(algorithm)
    
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except IOError:
        return ""


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def get_file_info(file_path: Path) -> dict:
    """Get comprehensive file information"""
    try:
        stat = file_path.stat()
        return {
            'name': file_path.name,
            'size': stat.st_size,
            'size_formatted': format_file_size(stat.st_size),
            'modified': stat.st_mtime,
            'created': stat.st_ctime,
            'mime_type': mimetypes.guess_type(str(file_path))[0] or 'unknown',
            'hash': get_file_hash(file_path)
        }
    except (OSError, IOError):
        return {}


def sanitize_bucket_name(name: str) -> str:
    """Sanitize bucket name according to S3 naming rules"""
    # Remove invalid characters and convert to lowercase
    sanitized = ''.join(c.lower() if c.isalnum() or c in '-.' else '-' for c in name)
    
    # Remove consecutive dashes and trim
    while '--' in sanitized:
        sanitized = sanitized.replace('--', '-')
    
    sanitized = sanitized.strip('-')
    
    # Ensure it starts and ends with alphanumeric
    if sanitized and not sanitized[0].isalnum():
        sanitized = 'bucket-' + sanitized
    if sanitized and not sanitized[-1].isalnum():
        sanitized = sanitized + '-bucket'
    
    # Limit length
    if len(sanitized) > 63:
        sanitized = sanitized[:63].rstrip('-')
    
    return sanitized or 'backup-bucket'


def validate_folder_path(path: str) -> Tuple[bool, str]:
    """Validate if a path is a valid folder"""
    try:
        folder_path = Path(path)
        if not folder_path.exists():
            return False, "Folder does not exist"
        if not folder_path.is_dir():
            return False, "Path is not a directory"
        if not os.access(folder_path, os.R_OK):
            return False, "No read permission for folder"
        return True, "Valid folder"
    except Exception as e:
        return False, f"Invalid path: {str(e)}"


def get_folder_size(folder_path: Path) -> int:
    """Calculate total size of a folder"""
    total_size = 0
    try:
        for file_path in folder_path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
    except (OSError, IOError):
        pass
    return total_size


def estimate_backup_time(folder_path: Path, upload_speed_mbps: float = 10.0) -> str:
    """Estimate backup time based on folder size and upload speed"""
    total_size = get_folder_size(folder_path)
    total_size_mb = total_size / (1024 * 1024)
    
    if total_size_mb == 0:
        return "Unknown"
    
    # Convert Mbps to MB/s (divide by 8)
    upload_speed_mb_per_sec = upload_speed_mbps / 8
    estimated_seconds = total_size_mb / upload_speed_mb_per_sec
    
    if estimated_seconds < 60:
        return f"{estimated_seconds:.0f} seconds"
    elif estimated_seconds < 3600:
        return f"{estimated_seconds / 60:.1f} minutes"
    else:
        return f"{estimated_seconds / 3600:.1f} hours"


class ProgressTracker:
    """Simple progress tracking utility"""
    
    def __init__(self, total: int = 100):
        self.total = total
        self.current = 0
        self.callbacks = []
    
    def add_callback(self, callback):
        """Add a progress callback function"""
        self.callbacks.append(callback)
    
    def update(self, increment: int = 1):
        """Update progress"""
        self.current = min(self.current + increment, self.total)
        percentage = int((self.current / self.total) * 100) if self.total > 0 else 0
        
        for callback in self.callbacks:
            callback(percentage, self.current, self.total)
    
    def set_progress(self, current: int):
        """Set absolute progress"""
        self.current = min(current, self.total)
        percentage = int((self.current / self.total) * 100) if self.total > 0 else 0
        
        for callback in self.callbacks:
            callback(percentage, self.current, self.total)
    
    def reset(self, total: int = None):
        """Reset progress tracker"""
        if total is not None:
            self.total = total
        self.current = 0
