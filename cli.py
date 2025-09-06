#!/usr/bin/env python3
"""
BlackBlaze B2 Backup Tool - CLI Mode
Runs backups in the background without GUI
"""

import sys
import argparse
import logging
import time
from pathlib import Path
from typing import Dict, List

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent / "src"))

from blackblaze_backup.core import BackupService
from blackblaze_backup.config import config


def setup_cli_logging(log_file: str = None):
    """Setup logging for CLI mode"""
    if log_file is None:
        log_file = config.log_file
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def load_backup_config(config_file: str) -> Dict:
    """Load backup configuration from file"""
    import json
    
    config_path = Path(config_file)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    with open(config_path, 'r') as f:
        return json.load(f)


def run_backup_cli(backup_config: Dict, credentials: Dict, logger):
    """Run backup in CLI mode"""
    backup_service = BackupService()
    
    # Set credentials
    is_valid, message = backup_service.set_credentials(credentials)
    if not is_valid:
        logger.error(f"Invalid credentials: {message}")
        return False
    
    # Configure backup
    if backup_config.get('single_bucket_mode', False):
        backup_service.configure_bucket_mode(True, backup_config.get('single_bucket_name', ''))
    else:
        backup_service.configure_bucket_mode(False)
    
    # Add folders
    for folder_config in backup_config.get('folders', []):
        folder_path = folder_config['path']
        bucket_name = folder_config.get('bucket', '')
        backup_service.add_folder_to_backup(folder_path, bucket_name)
    
    # Validate configuration
    is_valid, message = backup_service.validate_backup_config()
    if not is_valid:
        logger.error(f"Invalid backup configuration: {message}")
        return False
    
    # Progress callbacks
    def progress_callback(value):
        logger.info(f"Progress: {value}%")
    
    def status_callback(message):
        logger.info(f"Status: {message}")
    
    def error_callback(message):
        logger.error(f"Error: {message}")
    
    # Execute backup
    logger.info("Starting backup process...")
    start_time = time.time()
    
    success = backup_service.execute_backup(
        progress_callback=progress_callback,
        status_callback=status_callback,
        error_callback=error_callback
    )
    
    end_time = time.time()
    duration = end_time - start_time
    
    if success:
        logger.info(f"Backup completed successfully in {duration:.2f} seconds")
    else:
        logger.error(f"Backup failed after {duration:.2f} seconds")
    
    return success


def create_sample_config():
    """Create a sample configuration file"""
    sample_config = {
        "single_bucket_mode": True,
        "single_bucket_name": "my-backup-bucket",
        "folders": [
            {
                "path": "/home/user/Documents",
                "bucket": ""
            },
            {
                "path": "/home/user/Pictures", 
                "bucket": ""
            }
        ],
        "credentials": {
            "endpoint": "s3.us-west-001.backblazeb2.com",
            "access_key": "your_access_key_here",
            "secret_key": "your_secret_key_here",
            "region": "us-west-001"
        }
    }
    
    config_file = Path("backup_config.json")
    import json
    
    with open(config_file, 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    print(f"Sample configuration created: {config_file}")
    print("Edit the file with your actual paths and credentials.")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="BlackBlaze B2 Backup Tool - CLI Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run backup with configuration file
  bb2backup-cli --config backup_config.json
  
  # Run backup with specific log file
  bb2backup-cli --config backup_config.json --log backup.log
  
  # Create sample configuration
  bb2backup-cli --create-config
  
  # Run in daemon mode (background)
  bb2backup-cli --config backup_config.json --daemon
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to backup configuration file'
    )
    
    parser.add_argument(
        '--log', '-l',
        type=str,
        help='Path to log file'
    )
    
    parser.add_argument(
        '--daemon', '-d',
        action='store_true',
        help='Run in daemon mode (background)'
    )
    
    parser.add_argument(
        '--create-config',
        action='store_true',
        help='Create a sample configuration file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Create sample config if requested
    if args.create_config:
        create_sample_config()
        return
    
    # Validate required arguments
    if not args.config:
        parser.error("--config is required (use --create-config to create a sample)")
    
    # Setup logging
    logger = setup_cli_logging(args.log)
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    try:
        # Load configuration
        backup_config = load_backup_config(args.config)
        credentials = backup_config.get('credentials', {})
        
        if not credentials:
            logger.error("No credentials found in configuration file")
            return 1
        
        # Run backup
        if args.daemon:
            logger.info("Starting backup in daemon mode...")
            # In daemon mode, we could fork the process here
            # For now, just run normally but log to file only
        
        success = run_backup_cli(backup_config, credentials, logger)
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
