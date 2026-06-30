"""Console-script shim that launches the MCP stdio server."""
import importlib.util
import sys
from pathlib import Path


def main():
    server_path = Path(__file__).resolve().parent.parent / "server.py"
    if not server_path.is_file():
        sys.exit(
            f"magent-server: cannot find {server_path}. Install the package from the "
            "cloned repo in editable mode: pip install -e ."
        )
    spec = importlib.util.spec_from_file_location("_magent_server", str(server_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_magent_server"] = mod
    spec.loader.exec_module(mod)
    mod.main()
