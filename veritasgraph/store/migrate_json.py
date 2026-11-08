"""One-time migration of the legacy ``knowledge_graph.json`` snapshot into SQLite.

Run explicitly with ``python -m veritasgraph.store.migrate_json [json] [db]``; the
engine also runs it automatically the first time it opens an empty database next
to an existing snapshot. The JSON file is renamed (never deleted) afterwards.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

from veritasgraph.store.sqlite import SqliteGraphStore, _norm, open_store


def migrate_json(json_path: Path, store: SqliteGraphStore, *, rename: bool = True) -> Dict[str, Any]:
    """Load the snapshot into ``store``. Duplicate entity names are merged."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    sources: Dict[str, Dict[str, Any]] = data.get("sources", {}) or {}
    entities: Dict[str, Dict[str, Any]] = data.get("entities", {}) or {}
    relationships: Dict[str, Dict[str, Any]] = data.get("relationships", {}) or {}

    # The store enforces one entity per normalised name; legacy snapshots could
    # contain duplicates. Fold them into the first occurrence.
    by_name: Dict[str, str] = {}
    remap: Dict[str, str] = {}
    kept: Dict[str, Dict[str, Any]] = {}
    for eid, ent in entities.items():
        key = _norm(ent.get("name", ""))
        if not key:
            continue
        keeper = by_name.get(key)
        if keeper is None:
            by_name[key] = eid
            kept[eid] = ent
            continue
        remap[eid] = keeper
        target = kept[keeper]
        for sid in ent.get("sources", []):
            if sid not in target.setdefault("sources", []):
                target["sources"].append(sid)

    rels: Dict[str, Dict[str, Any]] = {}
    for rid, rel in relationships.items():
        s = remap.get(rel.get("source"), rel.get("source"))
        t = remap.get(rel.get("target"), rel.get("target"))
        if s not in kept or t not in kept or s == t:
            continue
        rels[rid] = {**rel, "source": s, "target": t}

    store.write_rows(sources=sources.values(), entities=kept.values(), relationships=rels.values())
    report = {
        "sources": len(sources),
        "entities": len(kept),
        "relationships": len(rels),
        "merged_duplicate_entities": len(remap),
        "dropped_relationships": len(relationships) - len(rels),
    }
    if rename:
        target = json_path.with_name(f"{json_path.name}.migrated-{int(time.time())}")
        json_path.rename(target)
        report["renamed_to"] = str(target)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", type=Path)
    parser.add_argument("db_path", type=Path)
    parser.add_argument("--keep", action="store_true", help="do not rename the JSON file")
    args = parser.parse_args(argv)
    store = open_store(args.db_path)
    if not store.is_empty():
        print(f"refusing: {args.db_path} already contains a graph", file=sys.stderr)
        return 2
    print(json.dumps(migrate_json(args.json_path, store, rename=not args.keep), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
