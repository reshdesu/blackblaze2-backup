#!/usr/bin/env python3
"""
Simple test script for single instance protection logic.
This tests the core single instance protection without requiring the full GUI application.
"""

import sys
from pathlib import Path

# Add the source directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_single_instance_logic():
    """Test the single instance protection logic directly."""
    print("Testing single instance protection logic...")

    # Import the single instance function
    try:
        from blackblaze_backup.gui import _ensure_single_instance

        print("Successfully imported _ensure_single_instance")
    except ImportError as e:
        print(f"Failed to import _ensure_single_instance: {e}")
        return False

    # Create a mock app object
    class MockApp:
        def __init__(self):
            self._instance_lock_file = None

    app = MockApp()

    # Test 1: First instance should succeed
    print("\nTest 1: First instance should succeed")
    result1 = _ensure_single_instance(app)
    print(f"First instance result: {result1}")

    if not result1:
        print("ERROR: First instance should return True")
        return False

    # Test 2: Second instance should fail
    print("\nTest 2: Second instance should fail")
    result2 = _ensure_single_instance(app)
    print(f"Second instance result: {result2}")

    if result2:
        print("ERROR: Second instance should return False")
        return False

    # Test 3: Clean up and test again
    print("\nTest 3: After cleanup, first instance should succeed again")
    if app._instance_lock_file and app._instance_lock_file.exists():
        app._instance_lock_file.unlink()
        print("Cleaned up lock file")

    result3 = _ensure_single_instance(app)
    print(f"Third instance result: {result3}")

    if not result3:
        print("ERROR: After cleanup, first instance should return True")
        return False

    print("\nAll tests passed!")
    return True


if __name__ == "__main__":
    success = test_single_instance_logic()
    sys.exit(0 if success else 1)
