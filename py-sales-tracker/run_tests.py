#!/usr/bin/env python3
"""
Test runner script for Sales Tracker application.
This script ensures proper import paths and runs all tests.
"""
import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set PYTHONPATH environment variable
os.environ['PYTHONPATH'] = str(current_dir)

if __name__ == "__main__":
    import pytest
    
    # Run pytest with proper configuration
    exit_code = pytest.main([
        "-v",
        "--tb=short",
        "tests/",
        "-x"  # Stop on first failure for faster feedback
    ])
    
    sys.exit(exit_code)
