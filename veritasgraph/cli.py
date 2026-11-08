"""``veritasgraph`` command line: serve the Studio, run MCP, migrate, compile, export, import.

The graph lives in ``$VERITASGRAPH_DB`` (or ``$STUDIO_DATA_DIR/veritasgraph.db``);
every command that touches it opens the same store the Studio and MCP use.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Optional


def _engine() -> Any:
    from studio_api.graphrag_engine import engine

    return engine


def _cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print("serve needs the studio extra: pip install 'veritasgraph-mcp[studio]'", file=sys.stderr)
        return 2
    uvicorn.run("studio_api.main:app", host=args.host, port=args.port, log_level=args.log_level)
    return 0


def _cmd_mcp(_args: argparse.Namespace) -> int:
    from veritasgraph_mcp.server import main

    main()
    return 0


def _cmd_migrate(args: argparse.Namespace) -> int:
    from veritasgraph.store.migrate_json import main

    argv = [str(args.json_path), str(args.db_path)] + (["--keep"] if args.keep else [])
    return main(argv)


def _cmd_compile(args: argparse.Namespace) -> int:
    from veritasgraph import compile as compiler

    engine = _engine()
    if engine.store is None:
        print("no graph store configured", file=sys.stderr)
        return 2
    run = compiler.run_compile(engine, trigger="cli", actor=args.actor)
    print(json.dumps(run, indent=2, default=str))
    return 1 if run.get("status") == "busy" else 0


def _cmd_export(args: argparse.Namespace) -> int:
    data = json.dumps(_engine().export_graph(), indent=2, default=str)
    if args.output == "-":
        print(data)
    else:
        Path(args.output).write_text(data, encoding="utf-8")
    return 0


def _dry_run(graph: dict, fmt: str) -> dict:
    """Report what an import would do without writing anything."""
    from studio_api import graphrag_engine as ge

    fmt = (fmt or "auto").strip().lower()
    if fmt == "auto":
        fmt = ge._detect_format(graph)
    adapter = ge._FORMAT_ADAPTERS.get(fmt)
    if adapter is None:
        raise ValueError(f"Unsupported format '{fmt}'.")
    norm = adapter(graph)
    nodes = norm.get("nodes", [])
    engine = _engine()
    with engine._read():
        existing = [n["name"] for n in nodes if n.get("name") and ge._norm(n["name"]) in engine._name_index]
    return {
        "dry_run": True,
        "format": norm.get("format", fmt),
        "nodes_in_file": len(nodes),
        "edges_in_file": len(norm.get("edges", [])),
        "would_add_entities": sum(1 for n in nodes if n.get("name")) - len(existing),
        "existing_entities": existing[:50],
    }


def _cmd_import(args: argparse.Namespace) -> int:
    graph = json.loads(Path(args.path).read_text(encoding="utf-8"))
    try:
        if args.dry_run:
            result = _dry_run(graph, args.format)
        else:
            result = _engine().import_graph(
                graph,
                fmt=args.format,
                source_type=args.source_type,
                merge_strategy=args.merge_strategy,
                title=args.title,
                actor=args.actor,
            )
    except ValueError as exc:
        print(f"import failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 0


def _cmd_structured(args: argparse.Namespace) -> int:
    from veritasgraph.structured import service, worker
    from veritasgraph.structured.store import db

    if args.action == "migrate":
        db.upgrade()
        print("vg_structured is up to date")
        return 0
    if not service.enabled():
        print("Set VG_STRUCTURED_DSN first.", file=sys.stderr)
        return 2
    if args.action == "status":
        print(json.dumps(service.status(), indent=2, default=str))
        return 0
    if args.action == "ask":
        print(
            json.dumps(
                service.ask(
                    args.target,
                    actor="cli",
                    role="admin",
                    mode=args.mode,
                    connection_id=args.connection,
                ),
                indent=2,
                default=str,
            )
        )
        return 0
    names = {c["name"]: c["id"] for c in service.list_connections()}
    conn_id = names.get(args.target) if args.action != "reindex" else None
    if args.action != "reindex" and conn_id is None:
        print(f"Unknown connection {args.target!r}. Known: {', '.join(names) or 'none'}", file=sys.stderr)
        return 2
    job_id = worker.enqueue(args.action, "cli", conn_id)
    job = worker._claim()
    if job is None:
        print("No queued job found.", file=sys.stderr)
        return 2
    stats = worker._run(job)
    worker._finish(job_id, {"status": "done", "stats": stats})
    print(json.dumps(stats, indent=2, default=str))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="veritasgraph", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("serve", help="run the Studio API (needs the studio extra)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8200)
    p.add_argument("--log-level", default="info")
    p.set_defaults(func=_cmd_serve)

    p = sub.add_parser("mcp", help="run the MCP server over stdio")
    p.set_defaults(func=_cmd_mcp)

    p = sub.add_parser("migrate", help="move a legacy graphrag.json into a SQLite store")
    p.add_argument("json_path", type=Path)
    p.add_argument("db_path", type=Path)
    p.add_argument("--keep", action="store_true", help="do not rename the JSON file")
    p.set_defaults(func=_cmd_migrate)

    p = sub.add_parser("compile", help="run the ontology compile pipeline once")
    p.add_argument("--actor", default="cli")
    p.set_defaults(func=_cmd_compile)

    p = sub.add_parser("export", help="export the graph as JSON")
    p.add_argument("-o", "--output", default="-", help="file path, or - for stdout")
    p.set_defaults(func=_cmd_export)

    p = sub.add_parser("import", help="import a graph JSON file")
    p.add_argument("path", type=Path)
    p.add_argument("--format", default="auto")
    p.add_argument("--source-type", default="curated", choices=["curated", "extracted", "inferred"])
    p.add_argument(
        "--merge-strategy", default="preserve_curated", choices=["preserve_curated", "skip_existing", "overwrite"]
    )
    p.add_argument("--title", default=None)
    p.add_argument("--actor", default="cli")
    p.add_argument("--dry-run", action="store_true", help="report what would change; write nothing")
    p.set_defaults(func=_cmd_import)

    p = sub.add_parser("structured", help="structured-data layer (needs the structured extra)")
    p.add_argument("action", choices=["migrate", "status", "sync", "compile", "reindex", "ask"])
    p.add_argument("target", nargs="?", default="", help="connection name (sync/compile) or question (ask)")
    p.add_argument("--mode", default="exploratory", choices=["exploratory", "governed"])
    p.add_argument("--connection", default=None, help="connection id for ask")
    p.set_defaults(func=_cmd_structured)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
