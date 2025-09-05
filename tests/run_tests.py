#!/usr/bin/env python3
"""
Run all tests for the FA Header Generator

This script provides a simple way to run all tests with proper Python path setup.
"""

import os
import sys
import subprocess
from pathlib import Path


def setup_test_environment():
    """Set up the test environment"""
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    tools_dir = project_root / "tools"
    tests_dir = project_root / "tests"

    # Add tools directory to Python path
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))

    # Change to tests directory
    os.chdir(tests_dir)

    return tests_dir


def run_tests():
    """Run the test suite"""
    tests_dir = setup_test_environment()

    # Check if pytest is available
    try:
        import pytest

        print("Running tests with pytest...")

        # Run pytest with coverage
        exit_code = pytest.main(
            ["-v", "--tb=short", "--cov=../tools", "--cov-report=term-missing", "."]
        )

        return exit_code

    except ImportError:
        print("pytest not available, running with unittest...")

        # Run with unittest as fallback
        exit_code = subprocess.call(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-v",
                "-s",
                ".",
                "-p",
                "test_*.py",
            ]
        )

        return exit_code


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
