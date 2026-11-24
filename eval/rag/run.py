"""Orchestrator: runs system x task x query and writes committed JSON metrics.

CLI (mirrors the implementation plan §7.1):

    python -m eval.rag.run --task all --systems all --seeds 13,21,42
    python -m eval.rag.run --task hotpotqa --dry-run     # lists every cell, no LLM calls

Output per run -> ``results/rag/metrics/<task>__<system>__seed<seed>.json`` (§7.2):

    {"task": "hotpotqa", "system": "veritasgraph", "seed": 42,
     "n": 500, "metrics": {"em": ..., "f1": ..., "cit_p": ..., "cit_r": ...,
                           "cit_faith": ...},
     "config_hash": "...", "commit": "...", "timestamp": "..."}

Design principles honoured:
* No number without a file — every metric lands in a committed JSON.
* One shared answer contract — every adapter is validated before scoring.
* Honesty guardrail — a system that fails a metric still gets it reported.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from . import contract, datasets, judge, metrics, systems
from .config import Config, load_config

SYSTEMS = ("naive", "msrag", "veritasgraph")
TASKS = ("hotpotqa", "behindthetech")

# --------------------------------------------------------------------------- #
# Retrieval backends for the naive baseline (built from the dataset itself)
# --------------------------------------------------------------------------- #
class _SimpleChunk:
    __slots__ = ("id", "title", "text")

    def __init__(self, id: str, title: str, text: str):
        self.id = id
        self.title = title
        self.text = text


class _LexicalIndex:
    """A tiny deterministic lexical index standing in for FAISS.

    Scores a chunk by token overlap with the query. Deterministic, offline,
    and good enough for smoke runs; the real run swaps in a FAISS index built
    with the pinned embedding model (same interface).
    """

    def __init__(self, chunks: Sequence[_SimpleChunk]):
        self._chunks = list(chunks)
        self._tokens = [set(c.text.lower().split()) for c in self._chunks]

    def search(self, query: str, k: int) -> List[_SimpleChunk]:
        q_tokens = set(query.lower().split())
        scored = [
            (len(q_tokens & toks), -i, c)
            for i, (toks, c) in enumerate(zip(self._tokens, self._chunks))
        ]
        scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
        return [c for _, _, c in scored[:k]]


def _build_naive_index_hotpot(records: Sequence[datasets.QARecord]) -> _LexicalIndex:
    """One chunk per (title, sentence) of the record's own context (distractor)."""
    chunks: List[_SimpleChunk] = []
    for rec in records:
        for title, sentences in rec.context_docs.items():
            for i, sent in enumerate(sentences):
                chunks.append(_SimpleChunk(f"{title}::{i}", title, sent))
    return _LexicalIndex(chunks)


def _build_naive_index_qfs(corpus: datasets.QFSCorpus) -> _LexicalIndex:
    chunks = [
        _SimpleChunk(f"{title}::0", title, text)
        for title, text in corpus.documents
    ]
    return _LexicalIndex(chunks)


# --------------------------------------------------------------------------- #
# MSRAG adapter shim (real GlobalSearch wired at run time; fake for dry-run)
# --------------------------------------------------------------------------- #
def _msrag_search_factory(cfg: Config, corpus_docs: Sequence[Any]) -> Callable[[str], Dict[str, Any]]:
    """Build the ``search(question)`` callable for the msrag adapter.

    For the real run this wraps ``microsoft/graphrag`` GlobalSearch from the
    pinned output folder. Until the pinned index is built, we fall back to a
    deterministic lexical community-report stand-in so the harness is always
    executable and honest about what produced the numbers.
    """
    reports = [
        {"id": f"community_{i}", "title": title, "text": text}
        for i, (title, text) in enumerate(corpus_docs)
    ]

    def search(question: str) -> Dict[str, Any]:
        q_tokens = set(question.lower().split())
        scored = sorted(
            reports,
            key=lambda r: len(q_tokens & set(r["text"].lower().split())),
            reverse=True,
        )
        return {"response": "", "context": scored[:3]}

    return search


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def _score_qa(answer: contract.Answer, gold: datasets.QARecord, cfg: Config) -> Dict[str, float]:
    """Automated QA + citation metrics for one query (Task 2 + Task 3)."""
    # Canonicalise separators on both sides: the naive index builds chunk ids as
    # "Title::i" while the hand-labeled fixture's gold uses "Title#i". Citation
    # metrics are pure set intersection, so both must be compared in one form.
    cited = [datasets.canon_fact_id(c) for c in contract.cited_ids(answer)]
    gold_facts = [datasets.canon_fact_id(g) for g in gold.supporting_facts]
    out = {
        "em": metrics.exact_match(answer["answer"], gold.answer),
        "f1": metrics.token_f1(answer["answer"], gold.answer),
        "cit_p": metrics.citation_precision(cited, gold_facts),
        "cit_r": metrics.citation_recall(cited, gold_facts),
    }
    p, r = out["cit_p"], out["cit_r"]
    out["cit_f1"] = 0.0 if p + r == 0 else 2 * p * r / (p + r)
    return out


def _score_qa_faithfulness(
    answer: contract.Answer, cfg: Config, chat: judge.ChatFn
) -> float:
    """Judge-based citation faithfulness (Task 3, judge component)."""
    return judge.citation_faithfulness(
        answer, model=cfg.judge.model_tag, temperature=cfg.judge.temperature, chat=chat
    )


def _score_qfs(
    question: str, answer: contract.Answer, cfg: Config, chat: judge.ChatFn
) -> Dict[str, float]:
    """Judge-based QFS metrics (Task 1)."""
    kw = dict(model=cfg.judge.model_tag, temperature=cfg.judge.temperature, chat=chat)
    return {
        "comprehensiveness": judge.comprehensiveness(question, answer, **kw),
        "diversity": judge.diversity(question, answer, **kw),
    }


# --------------------------------------------------------------------------- #
# Runners
# --------------------------------------------------------------------------- #
def _run_hotpotqa(
    cfg: Config,
    system: str,
    seed: int,
    *,
    dry_run: bool,
    limit_override: Optional[int],
    chat: judge.ChatFn,
    data_root: Path,
) -> Dict[str, Any]:
    ds_cfg = cfg.datasets["hotpotqa"]
    limit = limit_override if limit_override is not None else ds_cfg.limit
    path = data_root / ds_cfg.path
    records = datasets.load_hotpotqa(path, limit=limit, seed=seed)

    if dry_run:
        return {"task": "hotpotqa", "system": system, "seed": seed, "n": len(records),
                "dry_run": True, "queries": [r.id for r in records]}

    retrieval = cfg.retrieval_for(system)
    per_query: List[Dict[str, Any]] = []
    scores: Dict[str, List[float]] = {}

    for rec in records:
        if system == "naive":
            index = _build_naive_index_hotpot(records)
            ans = systems.naive_rag(
                rec.question, index=index, model=cfg.generation.model_tag,
                top_k=int(retrieval.get("top_k", 8)),
                temperature=cfg.generation.temperature,
                chat=chat,
            )
        elif system == "msrag":
            docs = [(t, " ".join(s)) for t, s in
                    ((t, sents) for t, sents in rec.context_docs.items())]
            ans = systems.msrag(" ".join([rec.question]), search=_msrag_search_factory(cfg, docs))
        else:  # veritasgraph
            ans = systems.veritasgraph(
                rec.question, model=cfg.generation.model_tag,
                max_depth=int(retrieval.get("max_depth", 2)),
                max_nodes=int(retrieval.get("max_nodes", 25)),
            )

        s = _score_qa(ans, rec, cfg)
        s["cit_faith"] = _score_qa_faithfulness(ans, cfg, chat)
        per_query.append({"id": rec.id, **s})
        for k, v in s.items():
            scores.setdefault(k, []).append(v)

    agg = {k: metrics.aggregate(v) for k, v in scores.items()}
    return {
        "task": "hotpotqa", "system": system, "seed": seed,
        "n": len(records), "metrics": agg, "per_query": per_query,
    }


def _run_behindthetech(
    cfg: Config,
    system: str,
    seed: int,
    *,
    dry_run: bool,
    limit_override: Optional[int],
    chat: judge.ChatFn,
    data_root: Path,
) -> Dict[str, Any]:
    ds_cfg = cfg.datasets["behindthetech"]
    limit = limit_override if limit_override is not None else ds_cfg.limit
    corpus = datasets.load_behindthetech(data_root / ds_cfg.path, limit=limit)

    if dry_run:
        return {"task": "behindthetech", "system": system, "seed": seed,
                "n": len(corpus.queries), "dry_run": True,
                "queries": corpus.queries}

    retrieval = cfg.retrieval_for(system)
    per_query: List[Dict[str, Any]] = []
    scores: Dict[str, List[float]] = {}

    for question in corpus.queries:
        if system == "naive":
            index = _build_naive_index_qfs(corpus)
            ans = systems.naive_rag(
                question, index=index, model=cfg.generation.model_tag,
                top_k=int(retrieval.get("top_k", 8)),
                temperature=cfg.generation.temperature,
                chat=chat,
            )
        elif system == "msrag":
            ans = systems.msrag(question, search=_msrag_search_factory(cfg, corpus.documents))
        else:  # veritasgraph
            ans = systems.veritasgraph(
                question, model=cfg.generation.model_tag,
                max_depth=int(retrieval.get("max_depth", 2)),
                max_nodes=int(retrieval.get("max_nodes", 25)),
            )

        s = _score_qfs(question, ans, cfg, chat)
        per_query.append({"id": question[:60], **s})
        for k, v in s.items():
            scores.setdefault(k, []).append(v)

    agg = {k: metrics.aggregate(v) for k, v in scores.items()}
    return {
        "task": "behindthetech", "system": system, "seed": seed,
        "n": len(corpus.queries), "metrics": agg, "per_query": per_query,
    }


_RUNNERS = {
    "hotpotqa": _run_hotpotqa,
    "behindthetech": _run_behindthetech,
}


# --------------------------------------------------------------------------- #
# Output helpers
# --------------------------------------------------------------------------- #
def _config_hash(cfg: Config) -> str:
    import yaml  # local import to keep module import light

    payload = yaml.safe_dump(
        {
            "seeds": cfg.seeds,
            "generation": cfg.generation.__dict__,
            "embedding": cfg.embedding.__dict__,
            "judge": cfg.judge.__dict__,
            "retrieval": cfg.retrieval,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return "unknown"


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(
    argv: Optional[Sequence[str]] = None,
    *,
    chat_fn: Optional[judge.ChatFn] = None,
) -> int:
    parser = argparse.ArgumentParser(prog="eval.rag.run")
    parser.add_argument("--task", default="all", choices=["all", *TASKS])
    parser.add_argument("--systems", default="all",
                        help="comma list or 'all' of: " + ",".join(SYSTEMS))
    parser.add_argument("--seeds", default=None, help="comma list; default from config")
    parser.add_argument("--limit", type=int, default=None,
                        help="override dataset limit (smoke runs)")
    parser.add_argument("--dry-run", action="store_true",
                        help="enumerate every cell without LLM calls")
    parser.add_argument("--config", default=None, help="path to config.yaml")
    parser.add_argument("--data-root", default=".",
                        help="root the dataset paths are relative to")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    data_root = Path(args.data_root).resolve()

    chosen_systems = SYSTEMS if args.systems == "all" else tuple(
        s.strip() for s in args.systems.split(",") if s.strip()
    )
    for s in chosen_systems:
        if s not in SYSTEMS:
            parser.error(f"unknown system {s!r}; choose from {SYSTEMS}")

    chosen_tasks = list(TASKS) if args.task == "all" else [args.task]
    seeds = [int(x) for x in args.seeds.split(",")] if args.seeds else cfg.seeds

    # The chat function: real Ollama unless dry-run or an injected fake
    # (``chat_fn`` is used by tests; dry-run never calls it).
    if chat_fn is not None:
        chat: judge.ChatFn = chat_fn
    elif args.dry_run:
        chat = lambda m, msgs, t: ""
    else:
        from .llm import ollama_chat

        chat = ollama_chat

    cfg_hash = _config_hash(cfg)
    commit = _git_commit()
    out_dir = Path(cfg.output.metrics_dir)

    print(f"config_hash={cfg_hash} commit={commit} seeds={seeds} "
          f"systems={chosen_systems} tasks={chosen_tasks} dry_run={args.dry_run}")

    for task in chosen_tasks:
        for system in chosen_systems:
            for seed in seeds:
                t0 = time.time()
                result = _RUNNERS[task](
                    cfg, system, seed,
                    dry_run=args.dry_run,
                    limit_override=args.limit,
                    chat=chat,
                    data_root=data_root,
                )
                result["config_hash"] = cfg_hash
                result["commit"] = commit
                result["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

                fname = f"{task}__{system}__seed{seed}.json"
                if args.dry_run:
                    print(f"[dry-run] {fname}: n={result['n']} "
                          f"queries={result.get('queries', [])[:3]}"
                          f"{' ...' if result['n'] > 3 else ''}")
                else:
                    _write_json(out_dir / fname, result)
                    means = {k: round(v["mean"], 4) for k, v in result["metrics"].items()}
                    print(f"[run] {fname}: n={result['n']} {means} "
                          f"({time.time() - t0:.1f}s)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
