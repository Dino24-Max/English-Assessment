"""
Pytest configuration and shared fixtures
Sets up Python path for imports
"""

import sys
import os
from pathlib import Path

# Add src/main/python to Python path for imports
# conftest.py is in src/test/, so go up 2 levels to project root
_conftest_file = Path(__file__).resolve()
project_root = _conftest_file.parent.parent.parent
python_src = project_root / "src" / "main" / "python"
python_src_str = str(python_src.resolve())

# Add to sys.path (must be first to ensure imports work)
if python_src_str not in sys.path:
    sys.path.insert(0, python_src_str)

# Also set PYTHONPATH environment variable for subprocesses
os.environ["PYTHONPATH"] = python_src_str + os.pathsep + os.environ.get("PYTHONPATH", "")

# Configure pytest-asyncio for async fixtures
import pytest_asyncio

# Ensure async fixtures work correctly
pytest_plugins = ["pytest_asyncio"]

