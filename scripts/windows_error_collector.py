#!/usr/bin/env python3
"""
Windows Error Collector for BlackBlaze B2 Backup Tool
Automatically collects and reports Windows-specific errors
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


def setup_logging():
    """Setup logging for error collection"""
    log_dir = Path.home() / ".blackblaze_backup"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "error_collector.log"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(__name__)


def collect_system_info():
    """Collect Windows system information"""
    logger = logging.getLogger(__name__)

    try:
        # Get Windows version
        result = subprocess.run(["ver"], capture_output=True, text=True, shell=True)
        windows_version = result.stdout.strip() if result.returncode == 0 else "Unknown"

        # Get Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # Get architecture
        arch = os.environ.get("PROCESSOR_ARCHITECTURE", "Unknown")

        return {
            "windows_version": windows_version,
            "python_version": python_version,
            "architecture": arch,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error collecting system info: {e}")
        return {"error": str(e)}


def collect_application_logs():
    """Collect application logs"""
    logger = logging.getLogger(__name__)

    log_file = Path.home() / ".blackblaze_backup" / "blackblaze_backup.log"

    if log_file.exists():
        try:
            with open(log_file, encoding="utf-8") as f:
                # Get last 100 lines
                lines = f.readlines()
                return lines[-100:] if len(lines) > 100 else lines
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
            return [f"Error reading log file: {e}"]
    else:
        return ["Log file not found"]


def test_single_instance_protection():
    """Test single instance protection"""
    logger = logging.getLogger(__name__)

    try:
        # Check if lock file exists
        temp_dir = Path(tempfile.gettempdir())
        lock_file = temp_dir / "blackblaze_backup_tool_single_instance.lock"

        if lock_file.exists():
            with open(lock_file) as f:
                pid = f.read().strip()

            # Check if process is running
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True
            )

            return {
                "lock_file_exists": True,
                "pid": pid,
                "process_running": "PID" in result.stdout,
                "test_result": "SUCCESS" if "PID" in result.stdout else "FAILED",
            }
        else:
            return {"lock_file_exists": False, "test_result": "NO_LOCK_FILE"}
    except Exception as e:
        logger.error(f"Error testing single instance protection: {e}")
        return {"error": str(e)}


def test_system_tray():
    """Test system tray availability"""
    logger = logging.getLogger(__name__)

    try:
        # Check if system tray is available
        import ctypes

        user32 = ctypes.windll.user32

        # Check if we can access system tray
        hwnd = user32.FindWindowW("Shell_TrayWnd", None)

        return {
            "tray_available": hwnd != 0,
            "test_result": "SUCCESS" if hwnd != 0 else "FAILED",
        }
    except Exception as e:
        logger.error(f"Error testing system tray: {e}")
        return {"error": str(e)}


def collect_error_report():
    """Collect comprehensive error report"""
    logger = setup_logging()
    logger.info("Starting Windows error collection")

    report = {
        "collection_timestamp": datetime.now().isoformat(),
        "system_info": collect_system_info(),
        "application_logs": collect_application_logs(),
        "single_instance_test": test_single_instance_protection(),
        "system_tray_test": test_system_tray(),
    }

    # Save report
    report_file = Path.home() / ".blackblaze_backup" / "windows_error_report.json"
    try:
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"Error report saved to {report_file}")
    except Exception as e:
        logger.error(f"Error saving report: {e}")

    return report


if __name__ == "__main__":
    report = collect_error_report()
    print(json.dumps(report, indent=2))
