"""Test configuration for the NCAA prediction model."""

import os
import sys
from pathlib import Path

# Add the project root directory to Python path
# This allows imports from src to work in the test files
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
