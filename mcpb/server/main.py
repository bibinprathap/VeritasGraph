"""MCPB entry point: put the bundled dependencies on sys.path and start the server."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

from veritasgraph_mcp.server import main  # noqa: E402

if __name__ == "__main__":
    main()
