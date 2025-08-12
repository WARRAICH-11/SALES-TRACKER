"""
Pytest configuration file to fix import paths for the Sales Tracker application.
"""
import sys
from pathlib import Path

# Add the project root to Python path so tests can import app modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Also add to PYTHONPATH for subprocess calls
import os
current_path = os.environ.get('PYTHONPATH', '')
if current_path:
    os.environ['PYTHONPATH'] = f"{project_root}{os.pathsep}{current_path}"
else:
    os.environ['PYTHONPATH'] = str(project_root)
