"""Run Microsoft GraphRAG GlobalSearch over a built index (MSRAG baseline).

Runs inside the pinned graphrag 0.3.6 environment (``.venv-msrag``), so it only
depends on graphrag/pandas. Reads a JSON list of ``{"id", "query"}`` items and
appends one JSON line per answered query to ``--out`` (resumable).

Each output line carries the response, the ids of the community reports the
response cites (``[Data: Reports (1, 5, +more)]``), and, for each cited report,
the titles of the source documents underlying that community. The latter is
how MSRAG citations are compared against document-level gold evidence.

Usage (from the repo root):
    .venv-msrag/bin/python eval/rag/msrag_query.py --root <index dir> \
        --queries q.json --out answers.jsonl --community-level 1 \
        --response-type "multiple paragraphs" --concurrency 4
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Set

import pandas as pd
from graphrag.config import load_config, resolve_paths
from graphrag.query import api

_REPORT_REF = re.compile(r"Reports\s*\(([^)]*)\)")


def _cited_report_ids(response: str) -> List[str]:
    ids: List[str] = []
    for group in _REPORT_REF.findall(response):
        for tok in group.split(","):
            tok = tok.strip()
            if tok.isdigit() and tok not in ids:
                ids.append(tok)
    return ids


def _community_titles(out_dir: Path, level: int) -> Dict[str, Set[str]]:
    """community id -> titles of documents whose text units mention its entities."""
    nodes = pd.read_parquet(out_dir / "create_final_nodes.parquet")
    ents = pd.read_parquet(out_dir / "create_final_entities.parquet")
    units = pd.read_parquet(out_dir / "create_final_text_units.parquet")
    docs = pd.read_parquet(out_dir / "create_final_documents.parquet")

    doc_title = dict(zip(docs["id"], docs["title"]))
    unit_docs = {
        u: [doc_title.get(d, d) for d in (dids if dids is not None else [])]
        for u, dids in zip(units["id"], units["document_ids"])
    }
    name_col = "name" if "name" in ents.columns else "title"
    ent_units = {
        n: list(t) if t is not None else []
        for n, t in zip(ents[name_col], ents["text_unit_ids"])
    }
    out: Dict[str, Set[str]] = {}
    lvl = nodes[nodes["level"] == level]
    for title, comm in zip(lvl["title"], lvl["community"]):
        if comm is None or str(comm) in ("", "nan", "-1"):
            continue
        bucket = out.setdefault(str(int(float(comm))), set())
        for u in ent_units.get(title, []):
            bucket.update(unit_docs.get(u, []))
    return out


async def _main(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    config = load_config(root, None)
    resolve_paths(config)
    out_dir = Path(config.storage.base_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir

    nodes = pd.read_parquet(out_dir / "create_final_nodes.parquet")
    entities = pd.read_parquet(out_dir / "create_final_entities.parquet")
    reports = pd.read_parquet(out_dir / "create_final_community_reports.parquet")
    comm_titles = _community_titles(out_dir, args.community_level)
    report_text = {
        str(c): str(t) for c, t in zip(reports["community"], reports["full_content"])
    }

    queries = json.loads(Path(args.queries).read_text(encoding="utf-8"))
    out_path = Path(args.out)
    done: Set[str] = set()
    if out_path.is_file():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["id"])
    todo = [q for q in queries if q["id"] not in done]
    print(f"msrag: {len(done)} done, {len(todo)} to run", flush=True)

    sem = asyncio.Semaphore(args.concurrency)
    lock = asyncio.Lock()

    async def one(item: Dict[str, str]) -> None:
        async with sem:
            try:
                response, _ctx = await api.global_search(
                    config=config,
                    nodes=nodes,
                    entities=entities,
                    community_reports=reports,
                    community_level=args.community_level,
                    response_type=args.response_type,
                    query=item["query"],
                )
                response = str(response)
                error = None
            except Exception as exc:  # recorded, scored as a failed answer
                response, error = "", repr(exc)
            cited = _cited_report_ids(response)
            rec = {
                "id": item["id"],
                "response": response,
                "error": error,
                "cited_reports": cited,
                "cited_titles": {r: sorted(comm_titles.get(r, set())) for r in cited},
                "cited_text": {r: report_text.get(r, "")[:4000] for r in cited},
            }
            async with lock:
                with out_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec) + "\n")

    await asyncio.gather(*(one(q) for q in todo))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--queries", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--community-level", type=int, default=1)
    ap.add_argument("--response-type", default="multiple paragraphs")
    ap.add_argument("--concurrency", type=int, default=4)
    asyncio.run(_main(ap.parse_args()))
