"""
VeritasReason Knowledge Explorer : CLI Entry Point

Provides the ``veritasreason-explorer`` command that loads a graph from a
JSON file, starts a FastAPI server, and optionally opens the browser.

Usage::

    veritasreason-explorer --graph my_graph.json --port 8000
    python -m veritasreason.explorer --graph my_graph.json
"""

import argparse
import sys
import webbrowser


def main(argv=None):
    """CLI entry point for the Knowledge Explorer server."""
    parser = argparse.ArgumentParser(
        prog="veritasreason-explorer",
        description="VeritasReason Knowledge Explorer — interactive dashboard for KG exploration",
    )
    parser.add_argument(
        "--graph", "-g",
        required=True,
        help="Path to a ContextGraph JSON file to load.",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000).",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the browser automatically.",
    )
    args = parser.parse_args(argv)

  
    import os
    if not os.path.isfile(args.graph):
        print(f"Error: graph file not found: {args.graph}", file=sys.stderr)
        sys.exit(1)

    try:
        import uvicorn 
    except ImportError:
        print(
            "Error: uvicorn is required.  Install with:\n"
            "  pip install veritas-reason[explorer]",
            file=sys.stderr,
        )
        sys.exit(1)

    from .session import GraphSession
    from .app import create_app

    print(f"Loading graph from {args.graph} ...")
    session = GraphSession.from_file(args.graph)
    stats = session.get_stats()
    print(
        f"Graph loaded — {stats.get('node_count', 0)} nodes, "
        f"{stats.get('edge_count', 0)} edges"
    )


    app = create_app(session=session)


    url = f"http://{args.host}:{args.port}"
    if not args.no_browser:
        import threading
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    print(f"Starting explorer at {url}")
    print(f"  API docs:  {url}/docs")
    print(f"  Health:    {url}/api/health")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
