"""Launcher script for mageNT MCP Server.

This script ensures the proper Python path is set before starting the server.
"""

import sys
from pathlib import Path

# Add parent directory to Python path to allow imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Now import and run the server
if __name__ == "__main__":
    from mageNT import server
    server.main()
