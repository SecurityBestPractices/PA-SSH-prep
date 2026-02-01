"""Launcher script for PA-SSH-prep - handles imports for PyInstaller."""

import sys
import os

# Add the project directory to the path
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    app_dir = os.path.dirname(sys.executable)
else:
    # Running as script
    app_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, app_dir)

# Now import and run the main module
from src.main import main

if __name__ == "__main__":
    main()
