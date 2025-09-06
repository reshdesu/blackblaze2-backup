"""
Configuration management for BlackBlaze B2 Backup Tool
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import json


class Config:
    """Application configuration manager"""
    
    def __init__(self):
        self.app_name = "BlackBlaze B2 Backup Tool"
        self.version = "1.0.0"
        self.config_dir = Path.home() / ".blackblaze_backup"
        self.config_file = self.config_dir / "config.json"
        self.log_file = self.config_dir / "blackblaze_backup.log"
        
        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "app": {
                "name": self.app_name,
                "version": self.version,
                "log_level": "INFO"
            },
            "backup": {
                "default_region": "us-west-001",
                "default_endpoint": "s3.us-west-001.backblazeb2.com",
                "max_concurrent_uploads": 5,
                "chunk_size": 8 * 1024 * 1024  # 8MB
            },
            "ui": {
                "window_width": 1000,
                "window_height": 700,
                "theme": "default"
            }
        }
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                return config
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}")
                return self.get_default_config()
        else:
            return self.get_default_config()
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving config: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'app.name')"""
        config = self.load_config()
        keys = key.split('.')
        value = config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> bool:
        """Set configuration value using dot notation"""
        config = self.load_config()
        keys = key.split('.')
        
        # Navigate to the parent of the target key
        current = config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Set the value
        current[keys[-1]] = value
        
        return self.save_config(config)


# Global config instance
config = Config()
