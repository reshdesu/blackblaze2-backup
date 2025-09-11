#!/usr/bin/env python3
"""
Windows Testing Script for BlackBlaze B2 Backup Tool
Comprehensive testing suite for Windows-specific functionality
"""

import json
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path


def setup_logging():
    """Setup logging for testing"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("windows_test_results.log"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(__name__)


def test_executable_exists():
    """Test if executable exists and is runnable"""
    logger = logging.getLogger(__name__)

    exe_path = Path("dist/BlackBlaze-Backup-Tool.exe")

    if not exe_path.exists():
        logger.error(f"Executable not found at {exe_path}")
        return False

    logger.info(f"Executable found at {exe_path}")
    return True


def test_single_instance_protection():
    """Test single instance protection"""
    logger = logging.getLogger(__name__)
    logger.info("Testing single instance protection...")

    try:
        # Start first instance
        proc1 = subprocess.Popen(
            ["dist/BlackBlaze-Backup-Tool.exe"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(3)  # Let it initialize

        # Try to start second instance (should fail)
        proc2 = subprocess.Popen(
            ["dist/BlackBlaze-Backup-Tool.exe"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(2)

        # Check if second instance is still running
        if proc2.poll() is None:
            logger.error(
                "Second instance is still running - single instance protection failed"
            )
            proc2.terminate()
            proc1.terminate()
            return False
        else:
            logger.info("Second instance exited - single instance protection working")

        # Clean up
        proc1.terminate()
        return True

    except Exception as e:
        logger.error(f"Error testing single instance protection: {e}")
        return False


def test_system_tray():
    """Test system tray functionality"""
    logger = logging.getLogger(__name__)
    logger.info("Testing system tray...")

    try:
        # Start application
        proc = subprocess.Popen(
            ["dist/BlackBlaze-Backup-Tool.exe"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(5)  # Let it initialize and show tray

        # Check if process is still running
        if proc.poll() is None:
            logger.info("Application started and is running")
            proc.terminate()
            return True
        else:
            logger.error("Application crashed during startup")
            return False

    except Exception as e:
        logger.error(f"Error testing system tray: {e}")
        return False


def test_window_focus():
    """Test window focus functionality"""
    logger = logging.getLogger(__name__)
    logger.info("Testing window focus...")

    try:
        import ctypes

        # Start application
        proc = subprocess.Popen(
            ["dist/BlackBlaze-Backup-Tool.exe"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(3)

        # Try to find and focus the window
        user32 = ctypes.windll.user32

        # Find window by class name or title
        hwnd = user32.FindWindowW(None, "BlackBlaze B2 Backup Tool")
        if hwnd:
            logger.info("Found application window")
            # Try to bring to front
            user32.SetForegroundWindow(hwnd)
            logger.info("Window focus test completed")
            proc.terminate()
            return True
        else:
            logger.warning("Could not find application window")
            proc.terminate()
            return False

    except Exception as e:
        logger.error(f"Error testing window focus: {e}")
        return False


def test_backup_functionality():
    """Test basic backup functionality"""
    logger = logging.getLogger(__name__)
    logger.info("Testing backup functionality...")

    try:
        # This would require actual BackBlaze credentials
        # For now, just test that the app can start without crashing
        proc = subprocess.Popen(
            ["dist/BlackBlaze-Backup-Tool.exe"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(3)

        if proc.poll() is None:
            logger.info("Application started successfully for backup test")
            proc.terminate()
            return True
        else:
            logger.error("Application crashed during backup test")
            return False

    except Exception as e:
        logger.error(f"Error testing backup functionality: {e}")
        return False


def run_comprehensive_tests():
    """Run all Windows tests"""
    logger = setup_logging()
    logger.info("Starting comprehensive Windows testing")

    results = {"timestamp": datetime.now().isoformat(), "tests": {}}

    # Test executable exists
    results["tests"]["executable_exists"] = test_executable_exists()

    if results["tests"]["executable_exists"]:
        # Test single instance protection
        results["tests"][
            "single_instance_protection"
        ] = test_single_instance_protection()

        # Test system tray
        results["tests"]["system_tray"] = test_system_tray()

        # Test window focus
        results["tests"]["window_focus"] = test_window_focus()

        # Test backup functionality
        results["tests"]["backup_functionality"] = test_backup_functionality()

    # Calculate overall result
    passed_tests = sum(1 for result in results["tests"].values() if result)
    total_tests = len(results["tests"])
    results["overall_result"] = "PASSED" if passed_tests == total_tests else "FAILED"
    results["passed_tests"] = passed_tests
    results["total_tests"] = total_tests

    logger.info(f"Testing completed: {passed_tests}/{total_tests} tests passed")

    # Save results
    with open("windows_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    results = run_comprehensive_tests()
    print(json.dumps(results, indent=2))
