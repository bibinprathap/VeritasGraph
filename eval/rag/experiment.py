"""Full benchmark driver: builds real indexes, runs real systems, writes metrics.

This is the driver behind Tables III-V. Unlike ``eval.rag.run`` (dry-run and
offline smoke tooling), every number written here comes from real model calls:

* **naive**              dense top-k retrieval (``nomic-embed-text``) + generation
* **msrag**              ``microsoft/graphrag`` 0.3.6 indexing + GlobalSearch
                         (pinned venv ``.venv-msrag``, see ``msrag_query.py``)
* **veritasgraph**       ``studio_api.graphrag_engine`` ingest + query (as built:
                         lexical entry points, BFS expansion)
* **veritasgraph_dense** ablation: same graph, entry points from dense chunk
                         retrieval mapped to entities via provenance links

Stages are resumable (every LLM output is cached on disk), so the command can
be re-run after an interruption:

    python -m eval.rag.experiment prepare
    python -m eval.rag.experiment index  --task hotpotqa|behindthetech --system ...
    python -m eval.rag.experiment answer --task ... --system ...
    python -m eval.rag.experiment score  --task ... --system ...
    python -m eval.rag.experiment tables

Settings come from ``eval/rag/config.yaml`` (``experiment:`` section).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import httpx
import numpy as np
import yaml

from . import judge, metrics, systems
from .config import load_config
from .run import _config_hash, _git_commit, _write_json

ROOT = Path(__file__).resolve().parents[2]
CFG_PATH = Path(__file__).resolve().parent / "config.yaml"
SYSTEMS = ("naive", "msrag", "veritasgraph", "veritasgraph_dense")
TASKS = ("hotpotqa", "behindthetech")


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #
def _settings() -> Dict[str, Any]:
    raw = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))
    return raw["experiment"]


CFG = load_config(CFG_PATH)
EXP = _settings()
# Pilot runs: RAG_EXP_OVERRIDE='{"work_dir": ..., ...}' shrinks the experiment
# (used only to smoke-test the pipeline; pilot outputs are never reported).
if os.environ.get("RAG_EXP_OVERRIDE"):
    EXP.update(json.loads(os.environ["RAG_EXP_OVERRIDE"]))
OLLAMA = os.environ.get("RAG_OLLAMA_URL", EXP["ollama_url"]).rstrip("/")
GEN_MODEL = CFG.generation.model_tag
JUDGE_MODEL = CFG.judge.model_tag
EMB_MODEL = CFG.embedding.model_tag
WORK = ROOT / EXP["work_dir"]          # indexes + caches (large, not committed)
_OUT = ROOT / EXP["output_dir"] if EXP.get("output_dir") else None
RAW = (_OUT / "raw") if _OUT else ROOT / CFG.output.raw_dir   # answers + judge outputs
METRICS = (_OUT / "metrics") if _OUT else ROOT / CFG.output.metrics_dir
TABLES = (_OUT / "tables") if _OUT else ROOT / CFG.output.tables_dir


def _manifest_path() -> Path:
    return WORK / "run_manifest.json"


def _load_run_state() -> Dict[str, Any]:
    path = _manifest_path()
    if not path.is_file():
        return {"prepare": {"done": False}, "index": {}, "answer": {}, "score": {}, "tables": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"prepare": {"done": False}, "index": {}, "answer": {}, "score": {}, "tables": {}}
    state = {"prepare": {"done": False}, "index": {}, "answer": {}, "score": {}, "tables": {}}
    for key, value in data.items():
        if isinstance(value, dict):
            state[key] = value
    return state


def _save_run_state(state: Dict[str, Any]) -> None:
    path = _manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def _stage_done(stage: str, task: Optional[str] = None, system: Optional[str] = None) -> bool:
    state = _load_run_state()
    bucket = state.get(stage, {})
    if task is None:
        return bool(bucket.get("done")) if isinstance(bucket, dict) else False
    if system is None:
        return bool(bucket.get(task, {}).get("done")) if isinstance(bucket.get(task), dict) else False
    return bool(bucket.get(task, {}).get(system, False)) if isinstance(bucket.get(task), dict) else False


def _mark_stage_done(stage: str, task: Optional[str] = None, system: Optional[str] = None) -> None:
    state = _load_run_state()
    if task is None:
        state[stage] = {"done": True}
    elif system is None:
        state.setdefault(stage, {})[task] = {"done": True}
    else:
        state.setdefault(stage, {}).setdefault(task, {})[system] = True
    _save_run_state(state)


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --------------------------------------------------------------------------- #
# Ollama access
# --------------------------------------------------------------------------- #
_client = httpx.Client(timeout=900.0)


def chat(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.0,
    num_predict: Optional[int] = None,
) -> str:
    options: Dict[str, Any] = {"temperature": temperature}
    if num_predict is not None:
        options["num_predict"] = num_predict
    body = {"model": model, "messages": messages, "stream": False, "options": options}
    for attempt in range(4):
        try:
            r = _client.post(f"{OLLAMA}/api/chat", json=body)
            r.raise_for_status()
            return (r.json().get("message") or {}).get("content", "")
        except Exception:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    return ""


def judge_chat(model: str, messages: List[Dict[str, str]], temperature: float) -> str:
    return chat(model, messages, temperature, num_predict=64)


def embed(texts: Sequence[str], batch: int = 32) -> np.ndarray:
    vecs: List[List[float]] = []
    for i in range(0, len(texts), batch):
        chunk = [t[:6000] for t in texts[i:i + batch]]
        r = _client.post(f"{OLLAMA}/api/embed", json={"model": EMB_MODEL, "input": chunk})
        r.raise_for_status()
        vecs.extend(r.json()["embeddings"])
    arr = np.asarray(vecs, dtype=np.float32)
    arr /= np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12
    return arr


def pmap(fn: Callable[[Any], Any], items: Sequence[Any], workers: Optional[int] = None,
         label: str = "") -> List[Any]:
    """Parallel map with progress logging (order preserved)."""
    workers = workers or int(EXP["concurrency"])
    out: List[Any] = [None] * len(items)
    done = [0]
    lock = threading.Lock()
    t0 = time.time()

    def run(i: int) -> None:
        out[i] = fn(items[i])
        with lock:
            done[0] += 1
            if done[0] % max(1, len(items) // 20) == 0 or done[0] == len(items):
                rate = done[0] / max(1e-9, time.time() - t0)
                eta = (len(items) - done[0]) / max(rate, 1e-9)
                _log(f"{label} {done[0]}/{len(items)}  ({rate:.2f}/s, eta {eta/60:.1f} min)")

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(run, range(len(items))))
    return out


class JsonlCache:
    """Append-only key -> value cache on disk (resumable stages)."""

    def __init__(self, path: Path):
        self.path = path
        self.data: Dict[str, Any] = {}
        self._lock = threading.Lock()
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self.data[rec["k"]] = rec["v"]
        path.parent.mkdir(parents=True, exist_ok=True)

    def __contains__(self, k: str) -> bool:
        return k in self.data

    def get(self, k: str) -> Any:
        return self.data[k]

    def put(self, k: str, v: Any) -> None:
        with self._lock:
            self.data[k] = v
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"k": k, "v": v}) + "\n")


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
def _h(s: str, n: int = 10) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:n]


def prepare() -> None:
    """Sample HotpotQA questions per seed, build both corpora, write queries."""
    if _stage_done("prepare"):
        _log("prepare: already complete; resuming from existing corpus files")
        return
    import pandas as pd

    WORK.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(ROOT / EXP["hotpotqa_parquet"])
    pool = []
    for row in df.itertuples(index=False):
        ctx = [(str(t), [str(s) for s in sents])
               for t, sents in zip(row.context["title"], row.context["sentences"])]
        pool.append({
            "id": str(row.id), "question": str(row.question), "answer": str(row.answer),
            "type": str(row.type), "level": str(row.level),
            "gold_titles": sorted(set(str(t) for t in row.supporting_facts["title"])),
            "context": ctx,
        })

    n = int(EXP["hotpotqa_n_per_seed"])
    questions: Dict[str, List[Dict[str, Any]]] = {}
    paragraphs: Dict[str, str] = {}
    for seed in CFG.seeds:
        idx = sorted(random.Random(seed).sample(range(len(pool)), n))
        questions[str(seed)] = [pool[i] for i in idx]
        for i in idx:
            for title, sents in pool[i]["context"]:
                paragraphs.setdefault(title, " ".join(s.strip() for s in sents).strip())
    docs = [{"id": f"p{_h(t)}", "title": t, "text": txt}
            for t, txt in sorted(paragraphs.items()) if txt]
    (WORK / "hotpotqa_questions.json").write_text(json.dumps(questions), encoding="utf-8")
    (WORK / "hotpotqa_corpus.json").write_text(json.dumps(docs), encoding="utf-8")
    uniq = {q["id"] for qs in questions.values() for q in qs}
    _log(f"hotpotqa: {n}/seed x {len(CFG.seeds)} seeds ({len(uniq)} unique questions), "
         f"{len(docs)} corpus paragraphs")

    bdir = ROOT / CFG.datasets["behindthetech"].path
    bdocs = [{"id": p.stem, "title": p.stem, "text": p.read_text(encoding="utf-8")}
             for p in sorted(bdir.glob("*.txt"))]
    if EXP.get("pilot_btt_chars"):
        bdocs = [dict(d, text=d["text"][: int(EXP["pilot_btt_chars"])])
                 for d in bdocs[: int(EXP.get("pilot_btt_docs", 2))]]
    (WORK / "behindthetech_corpus.json").write_text(json.dumps(bdocs), encoding="utf-8")
    words = sum(len(d["text"].split()) for d in bdocs)
    _log(f"behindthetech: {len(bdocs)} transcripts, {words} words")
    _mark_stage_done("prepare")


def corpus(task: str) -> List[Dict[str, str]]:
    return json.loads((WORK / f"{task}_corpus.json").read_text(encoding="utf-8"))


def hotpot_questions() -> Dict[str, List[Dict[str, Any]]]:
    return json.loads((WORK / "hotpotqa_questions.json").read_text(encoding="utf-8"))


def qfs_queries() -> List[Dict[str, str]]:
    return [{"id": f"q{i:02d}", "query": q} for i, q in enumerate(EXP["qfs_queries"])]


def query_items(task: str) -> List[Dict[str, Any]]:
    """All distinct queries for a task (answered once, scored per seed)."""
    if task == "behindthetech":
        return qfs_queries()
    seen: Dict[str, Dict[str, Any]] = {}
    for qs in hotpot_questions().values():
        for q in qs:
            seen.setdefault(q["id"], {"id": q["id"], "query": q["question"]})
    return list(seen.values())


def units(task: str) -> List[Dict[str, str]]:
    """Retrieval units shared by naive RAG and VeritasGraph ingestion.

    HotpotQA: one unit per Wikipedia paragraph. Behind the Tech: transcripts
    split with the engine's own chunker (<= 1,200 characters).
    """
    from studio_api.graphrag_engine import _chunk_text

    out: List[Dict[str, str]] = []
    for d in corpus(task):
        pieces = [d["text"]] if task == "hotpotqa" else _chunk_text(d["text"])
        for i, piece in enumerate(pieces):
            out.append({"id": f"doc_{_h(d['title'])}#{i}", "doc": d["title"],
                        "title": d["title"], "text": piece})
    return out


def _unit_vectors(task: str, us: List[Dict[str, str]]) -> np.ndarray:
    path = WORK / f"{task}_unit_vectors.npy"
    if path.is_file():
        arr = np.load(path)
        if arr.shape[0] == len(us):
            return arr
    _log(f"embedding {len(us)} units for {task}")
    texts = [f"{u['title']}: {u['text']}" for u in us]
    parts = pmap(lambda i: embed(texts[i:i + 64]), list(range(0, len(texts), 64)),
                 label="embed")
    arr = np.concatenate(parts, axis=0)
    np.save(path, arr)
    return arr


class DenseIndex:
    def __init__(self, task: str):
        self.units = units(task)
        self.vecs = _unit_vectors(task, self.units)

    def search_ids(self, query: str, k: int) -> List[int]:
        q = embed([query])[0]
        sims = self.vecs @ q
        return list(np.argsort(-sims)[:k])

    def search(self, query: str, k: int) -> List[systems.Chunk]:  # type: ignore[name-defined]
        return [_Unit(**self.units[i]) for i in self.search_ids(query, k)]


class _Unit:
    def __init__(self, id: str, title: str, text: str, doc: str):
        self.id, self.title, self.text, self.doc = id, title, text, doc


# --------------------------------------------------------------------------- #
# VeritasGraph: isolated engine instance per corpus
# --------------------------------------------------------------------------- #
def _vg_engine(task: str):
    from studio_api.graphrag_engine import GraphRAGEngine

    snapshot = WORK / "veritasgraph" / task / "graph.json"

    class EvalEngine(GraphRAGEngine):
        dense: Optional[DenseIndex] = None
        source_entities: Dict[str, List[str]] = {}
        _tl = threading.local()

        def retrieve(self, query: str, max_depth: int = 2, max_nodes: int = 25):
            rq = getattr(self._tl, "retrieval_query", None)
            return super().retrieve(rq or query, max_depth, max_nodes)

        def query_with_context(self, llm_question: str, retrieval_query: str,
                               model: str, max_depth: int, max_nodes: int):
            """Generate for ``llm_question`` but retrieve with ``retrieval_query``."""
            self._tl.retrieval_query = retrieval_query
            try:
                return self.query(llm_question, model, max_depth, max_nodes)
            finally:
                self._tl.retrieval_query = None

        def _load(self) -> None:  # isolated from the Studio's own graph
            if snapshot.is_file():
                data = json.loads(snapshot.read_text(encoding="utf-8"))
                self.sources = data["sources"]
                self.entities = data["entities"]
                self.relationships = data["relationships"]
                self._name_index = {
                    re.sub(r"\s+", " ", e["name"]).strip().lower(): eid
                    for eid, e in self.entities.items()
                }

        def _save(self) -> None:
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_text(json.dumps({
                "sources": self.sources, "entities": self.entities,
                "relationships": self.relationships}), encoding="utf-8")

        def _seed_entities(self, query: str) -> List[str]:
            if self.dense is None:
                return super()._seed_entities(query)
            # Ablation: entry points = entities extracted from the top-k chunks
            # retrieved by dense similarity (provenance links chunk -> entity).
            k = int(EXP["dense_seed_top_k"])
            seeds: List[str] = []
            for i in self.dense.search_ids(query, k):
                for eid in self.source_entities.get(self.dense.units[i]["id"], []):
                    if eid not in seeds:
                        seeds.append(eid)
            return seeds or super()._seed_entities(query)

    eng = EvalEngine()
    eng.chat_timeout = 900.0
    return eng


def index_veritasgraph(task: str) -> None:
    if _stage_done("index", task, "veritasgraph"):
        _log(f"veritasgraph/{task}: index already complete; skipping")
        return
    eng = _vg_engine(task)
    us = units(task)
    cache = JsonlCache(WORK / "veritasgraph" / task / "extractions.jsonl")
    eng.chat_options = {"temperature": CFG.generation.temperature}
    todo = [u for u in us if u["id"] not in cache]
    _log(f"veritasgraph/{task}: {len(us)} units, {len(todo)} to extract")

    def extract(u: Dict[str, str]) -> None:
        try:
            parsed = eng.extract_chunk(u["text"], GEN_MODEL)
        except Exception as exc:
            parsed = {"entities": [], "relationships": [], "error": repr(exc)}
        cache.put(u["id"], parsed)

    pmap(extract, todo, label=f"vg-extract/{task}")

    # Deterministic merge in corpus order.
    eng.sources, eng.entities, eng.relationships = {}, {}, {}
    eng._name_index, eng._rel_index = {}, {}
    counts: Dict[str, int] = {}
    for u in us:
        parsed = cache.get(u["id"])
        n = sum(1 for x in us if x["doc"] == u["doc"]) if task != "hotpotqa" else 1
        idx = int(u["id"].rsplit("#", 1)[1])
        eng.merge_chunk(u["id"], u["id"].split("#")[0], f"{u['title']} [{idx + 1}/{n}]"
                        if task != "hotpotqa" else u["title"], u["text"], parsed)
        counts["failed"] = counts.get("failed", 0) + (1 if "error" in parsed else 0)
        counts["empty"] = counts.get("empty", 0) + (0 if parsed.get("entities") else 1)
    eng._save()
    stats = {"units": len(us), "entities": len(eng.entities),
             "relationships": len(eng.relationships),
             "extraction_failures": counts.get("failed", 0),
             "units_with_no_entities": counts.get("empty", 0)}
    (WORK / "veritasgraph" / task / "stats.json").write_text(json.dumps(stats, indent=2))
    _mark_stage_done("index", task, "veritasgraph")
    _log(f"veritasgraph/{task}: {stats}")


# --------------------------------------------------------------------------- #
# MSRAG: graphrag 0.3.6 project per corpus
# --------------------------------------------------------------------------- #
MSRAG_PY = ROOT / ".venv-msrag" / "bin" / "python"


def _msrag_root(task: str) -> Path:
    return WORK / "msrag" / task


def _msrag_settings(task: str) -> Dict[str, Any]:
    m = EXP["msrag"]
    llm = {
        "api_key": "ollama", "type": "openai_chat", "model": GEN_MODEL,
        "model_supports_json": True, "api_base": f"{OLLAMA}/v1",
        "temperature": CFG.generation.temperature, "max_tokens": 4000,
        "request_timeout": 900.0, "concurrent_requests": int(EXP["concurrency"]),
        "max_retries": 5, "tokens_per_minute": 0, "requests_per_minute": 0,
    }
    return {
        "encoding_model": "cl100k_base",
        "skip_workflows": [],
        "llm": llm,
        "parallelization": {"stagger": 0.0, "num_threads": int(EXP["concurrency"])},
        "async_mode": "threaded",
        "embeddings": {
            "async_mode": "threaded",
            "llm": {"api_key": "ollama", "type": "openai_embedding", "model": EMB_MODEL,
                    "api_base": f"{OLLAMA}/v1"},
            # GlobalSearch does not use vector stores; skip all embedding targets.
            "skip": ["entity.name", "entity.description", "relationship.description",
                     "document.raw_content", "community.title", "community.summary",
                     "community.full_content", "text_unit.text"],
        },
        "chunks": {"size": int(m["chunk_size"]), "overlap": int(m["chunk_overlap"]),
                   "group_by_columns": ["id"]},
        "input": {"type": "file", "file_type": "text", "base_dir": "input",
                  "file_encoding": "utf-8", "file_pattern": ".*\\.txt$"},
        "cache": {"type": "file", "base_dir": "cache"},
        "storage": {"type": "file", "base_dir": "output"},
        "reporting": {"type": "file", "base_dir": "logs"},
        "entity_extraction": {"prompt": "prompts/entity_extraction.txt",
                              "entity_types": ["organization", "person", "geo", "event"],
                              "max_gleanings": int(m["max_gleanings"])},
        "summarize_descriptions": {"prompt": "prompts/summarize_descriptions.txt",
                                   "max_length": 500},
        "claim_extraction": {"enabled": False, "prompt": "prompts/claim_extraction.txt",
                             "description": "Any claims or facts that could be relevant to information discovery.",
                             "max_gleanings": 0},
        "community_reports": {"prompt": "prompts/community_report.txt",
                              "max_length": 2000, "max_input_length": 8000},
        "cluster_graph": {"max_cluster_size": 10},
        "embed_graph": {"enabled": False},
        "umap": {"enabled": False},
        "snapshots": {"graphml": False, "raw_entities": False, "top_level_nodes": False},
        "global_search": {"temperature": CFG.generation.temperature,
                          "max_tokens": 12000, "data_max_tokens": 8000,
                          "map_max_tokens": 1000, "reduce_max_tokens": 1500,
                          "concurrency": int(EXP["concurrency"])},
    }


def _msrag_index_complete(root: Path) -> bool:
    out = root / "output"
    required = {
        "create_final_documents.parquet",
        "create_final_community_reports.parquet",
        "create_final_relationships.parquet",
        "create_final_text_units.parquet",
        "stats.json",
    }
    return out.is_dir() and required.issubset({p.name for p in out.iterdir() if p.is_file()})


def index_msrag(task: str) -> None:
    root = _msrag_root(task)
    # Some interrupted runs leave a valid GraphRAG index on disk even though the
    # manifest was never updated. Treat the completed output as authoritative.
    if _stage_done("index", task, "msrag") or _msrag_index_complete(root):
        _mark_stage_done("index", task, "msrag")
        _log(f"msrag/{task}: index already complete; skipping")
        return
    if not (root / "prompts").is_dir():
        root.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(MSRAG_PY), "-m", "graphrag.index", "--init", "--root", str(root)],
                       check=True, cwd=str(ROOT), capture_output=True)
    (root / "settings.yaml").write_text(yaml.safe_dump(_msrag_settings(task), sort_keys=False))
    (root / ".env").write_text("GRAPHRAG_API_KEY=ollama\n")
    inp = root / "input"
    inp.mkdir(exist_ok=True)
    mapping = {}
    for d in corpus(task):
        fname = f"{d['id']}.txt"
        mapping[fname] = d["title"]
        p = inp / fname
        if not p.is_file():
            p.write_text(d["text"], encoding="utf-8")
    (root / "title_map.json").write_text(json.dumps(mapping))
    _log(f"msrag/{task}: indexing {len(mapping)} documents with graphrag 0.3.6")
    log = open(root / "index_run.log", "a")
    rc = subprocess.run([str(MSRAG_PY), "-m", "graphrag.index", "--root", str(root),
                         "--reporter", "print"], cwd=str(ROOT), stdout=log, stderr=log).returncode
    if rc != 0 and not _msrag_index_complete(root):
        raise SystemExit(f"graphrag indexing failed (rc={rc}); see {root/'index_run.log'}")
    _mark_stage_done("index", task, "msrag")
    _log(f"msrag/{task}: index done")


# --------------------------------------------------------------------------- #
# Answering
# --------------------------------------------------------------------------- #
def _answers_path(task: str, system: str) -> Path:
    return RAW / "answers" / f"{task}__{system}.jsonl"


_SRC_ID = re.compile(r"\b(doc_[0-9a-f]+#\d+)")


def _cited(text: str, context_ids: Sequence[str]) -> List[str]:
    """Source ids the answer cites, restricted to ids actually in its context."""
    found = set(_SRC_ID.findall(text or ""))
    return [c for c in context_ids if c in found]


def _qa_query(question: str) -> str:
    return question + "\n\n" + EXP["hotpotqa_answer_instruction"]


def _num_predict(task: str) -> int:
    return CFG.generation.num_predict if task == "hotpotqa" else int(EXP["qfs_num_predict"])


def answer(task: str, system: str) -> None:
    if _stage_done("answer", task, system):
        _log(f"answer {task}/{system}: already complete; skipping")
        return
    items = query_items(task)
    cache = JsonlCache(_answers_path(task, system))
    todo = [it for it in items if it["id"] not in cache]
    _log(f"answer {task}/{system}: {len(items)} queries, {len(todo)} to run")
    if not todo:
        _mark_stage_done("answer", task, system)
        return

    if system == "msrag":
        root = _msrag_root(task)
        qfile = root / "queries.json"
        qfile.write_text(json.dumps([
            {"id": it["id"], "query": _qa_query(it["query"]) if task == "hotpotqa" else it["query"]}
            for it in todo]))
        out = root / "answers_raw.jsonl"
        m = EXP["msrag"]
        rtype = m["response_type_qa"] if task == "hotpotqa" else m["response_type_qfs"]
        rc = subprocess.run([str(MSRAG_PY), str(ROOT / "eval/rag/msrag_query.py"),
                             "--root", str(root), "--queries", str(qfile), "--out", str(out),
                             "--community-level", str(m["community_level"]),
                             "--response-type", rtype,
                             "--concurrency", str(EXP["concurrency"])],
                            cwd=str(ROOT)).returncode
        if rc != 0:
            raise SystemExit(f"msrag query failed rc={rc}")
        tmap = json.loads((root / "title_map.json").read_text())
        stem_map = {Path(k).stem: v for k, v in tmap.items()}
        stem_map.update({k: v for k, v in tmap.items()})
        for line in out.read_text().splitlines():
            rec = json.loads(line)
            if rec["id"] in cache:
                continue
            cited_titles = sorted({stem_map.get(t, t) for ts in rec["cited_titles"].values()
                                   for t in ts})
            cache.put(rec["id"], {
                "answer": rec["response"], "error": rec["error"],
                "cited": [f"report_{r}" for r in rec["cited_reports"]],
                "cited_titles": cited_titles,
                "cited_sources": [{"id": f"report_{r}", "title": f"community report {r}",
                                   "text": rec["cited_text"].get(r, "")}
                                  for r in rec["cited_reports"]],
                "context_titles": [],
            })
        return

    us = units(task)
    unit_by_id = {u["id"]: u for u in us}
    npred = _num_predict(task)

    if system == "naive":
        index = DenseIndex(task)
        k = int(CFG.retrieval_for("naive").get("top_k", 8))

        def run(it: Dict[str, Any]) -> None:
            q = _qa_query(it["query"]) if task == "hotpotqa" else it["query"]
            chunks = index.search(it["query"], k)
            text = chat(GEN_MODEL, systems._naive_prompt(q, chunks),
                        CFG.generation.temperature, npred)
            ctx = [c.id for c in chunks]
            cited = _cited(text, ctx)
            cache.put(it["id"], {
                "answer": text, "context": ctx, "cited": cited,
                "cited_titles": sorted({unit_by_id[c]["doc"] for c in cited}),
                "cited_sources": [{"id": c, "title": unit_by_id[c]["title"],
                                   "text": unit_by_id[c]["text"]} for c in cited],
                "context_titles": sorted({unit_by_id[c]["doc"] for c in ctx}),
            })
    else:
        eng = _vg_engine(task)
        if not eng.entities:
            raise SystemExit(f"veritasgraph index for {task} missing; run `index` first")
        eng.chat_options = {"temperature": CFG.generation.temperature, "num_predict": npred}
        if system == "veritasgraph_dense":
            eng.dense = DenseIndex(task)
            src_ents: Dict[str, List[str]] = {}
            for eid, e in eng.entities.items():
                for sid in e.get("sources", []):
                    src_ents.setdefault(sid, []).append(eid)
            eng.source_entities = src_ents
        r = CFG.retrieval_for("veritasgraph")
        depth, nodes = int(r.get("max_depth", 2)), int(r.get("max_nodes", 25))

        def run(it: Dict[str, Any]) -> None:
            q = _qa_query(it["query"]) if task == "hotpotqa" else it["query"]
            # Retrieval uses the bare question; the answer-format instruction
            # is only part of the generation prompt.
            ctx_ids = [s["id"] for s in eng.retrieve(it["query"], depth, nodes)["sources"]]
            res = eng.query_with_context(q, it["query"], GEN_MODEL, depth, nodes)
            text = res["answer"]
            cited = _cited(text, ctx_ids)
            cache.put(it["id"], {
                "answer": text, "context": ctx_ids, "cited": cited,
                "cited_titles": sorted({unit_by_id[c]["doc"] for c in cited if c in unit_by_id}),
                "cited_sources": [{"id": c, "title": unit_by_id[c]["title"],
                                   "text": unit_by_id[c]["text"]} for c in cited if c in unit_by_id],
                "context_titles": sorted({unit_by_id[c]["doc"] for c in ctx_ids if c in unit_by_id}),
                "reasoning_path": res.get("reasoning_path", [])[:50],
            })

    pmap(run, todo, label=f"answer/{task}/{system}")
    _mark_stage_done("answer", task, system)


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
_BRACKETS = re.compile(r"\[[^\]]*\]")


def clean_answer(text: str) -> str:
    """Strip citations / data references so EM/F1 see only the answer text."""
    t = _BRACKETS.sub(" ", text or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _prf(pred: Iterable[str], gold: Iterable[str]) -> Tuple[float, float, float]:
    p = metrics.citation_precision(list(pred), list(gold))
    r = metrics.citation_recall(list(pred), list(gold))
    return p, r, (0.0 if p + r == 0 else 2 * p * r / (p + r))


def score(task: str, system: str) -> None:
    if _stage_done("score", task, system):
        _log(f"score {task}/{system}: already complete; skipping")
        return
    answers = JsonlCache(_answers_path(task, system))
    jcache = JsonlCache(RAW / "judge" / f"{task}__{system}.jsonl")
    cfg_hash, commit = _config_hash(CFG), _git_commit()

    if task == "hotpotqa":
        allq = {q["id"]: q for qs in hotpot_questions().values() for q in qs}

        def judge_one(qid: str) -> None:
            if qid in jcache:
                return
            a = answers.get(qid)
            ans = {"answer": a["answer"], "citations": a["cited_sources"],
                   "reasoning_path": [], "subgraph": {"nodes": [], "edges": []}}
            try:
                s = judge.citation_faithfulness(ans, model=JUDGE_MODEL,
                                                temperature=CFG.judge.temperature,
                                                chat=judge_chat)
            except ValueError:
                s = None
            jcache.put(qid, {"cit_faith": s})

        pmap(judge_one, [q for q in allq if q in answers], label=f"judge/{task}/{system}")

        for seed, qs in hotpot_questions().items():
            per_query, scores = [], {}
            for q in qs:
                a = answers.get(q["id"])
                pred = clean_answer(a["answer"])
                p, r, f = _prf(a["cited_titles"], q["gold_titles"])
                ctx_r = metrics.citation_recall(a.get("context_titles", []), q["gold_titles"]) \
                    if a.get("context_titles") else None
                faith = jcache.get(q["id"])["cit_faith"]
                s = {"em": metrics.exact_match(pred, q["answer"]),
                     "f1": metrics.token_f1(pred, q["answer"]),
                     "cit_p": p, "cit_r": r, "cit_f1": f,
                     "cit_faith": 0.0 if faith is None else faith,
                     "cited_any": 1.0 if a["cited_titles"] else 0.0}
                if ctx_r is not None:
                    s["ctx_recall"] = ctx_r
                per_query.append({"id": q["id"], "type": q["type"], **s,
                                  "judge_parse_failed": faith is None,
                                  "error": a.get("error")})
                for k, v in s.items():
                    scores.setdefault(k, []).append(v)
            _write_json(METRICS / f"hotpotqa__{system}__seed{seed}.json", {
                "task": "hotpotqa", "system": system, "seed": int(seed), "n": len(qs),
                "metrics": {k: metrics.aggregate(v) for k, v in scores.items()},
                "per_query": per_query, "config_hash": cfg_hash, "commit": commit,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "citation_unit": "document (Wikipedia paragraph title)",
            })
            _log(f"hotpotqa/{system}/seed{seed}: "
                 + ", ".join(f"{k}={metrics.aggregate(v)['mean']:.3f}" for k, v in scores.items()))
        _mark_stage_done("score", task, system)
        return

    items = qfs_queries()

    def judge_qfs(it: Dict[str, str]) -> None:
        if it["id"] in jcache:
            return
        a = answers.get(it["id"])
        ans = {"answer": a["answer"], "citations": [], "reasoning_path": [],
               "subgraph": {"nodes": [], "edges": []}}
        out = {}
        for name, fn in (("comprehensiveness", judge.comprehensiveness),
                         ("diversity", judge.diversity)):
            try:
                out[name] = fn(it["query"], ans, model=JUDGE_MODEL,
                               temperature=CFG.judge.temperature, chat=judge_chat)
            except ValueError:
                out[name] = None
        jcache.put(it["id"], out)

    pmap(judge_qfs, items, label=f"judge/{task}/{system}")
    per_query, scores = [], {}
    for it in items:
        j = jcache.get(it["id"])
        s = {k: (0.0 if v is None else v) for k, v in j.items()}
        per_query.append({"id": it["id"], "query": it["query"], **s,
                          "judge_parse_failed": any(v is None for v in j.values()),
                          "answer_words": len(answers.get(it["id"])["answer"].split())})
        for k, v in s.items():
            scores.setdefault(k, []).append(v)
    _write_json(METRICS / f"behindthetech__{system}__seed{CFG.seeds[0]}.json", {
        "task": "behindthetech", "system": system, "seed": CFG.seeds[0], "n": len(items),
        "metrics": {k: metrics.aggregate(v) for k, v in scores.items()},
        "per_query": per_query, "config_hash": cfg_hash, "commit": commit,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "note": "deterministic single run; std is across queries",
    })
    _mark_stage_done("score", task, system)
    _log(f"behindthetech/{system}: "
         + ", ".join(f"{k}={metrics.aggregate(v)['mean']:.3f}" for k, v in scores.items()))


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #
LABELS = {"naive": "Naive RAG", "msrag": "MSRAG (Global Search)",
          "veritasgraph": "VeritasGraph (Ours)",
          "veritasgraph_dense": "VeritasGraph + dense entry points (ablation)"}


def _load(task: str, system: str) -> List[Dict[str, Any]]:
    return [json.loads(p.read_text()) for p in sorted(METRICS.glob(f"{task}__{system}__seed*.json"))]


def tables() -> None:
    if _stage_done("tables"):
        _log("tables: already complete; skipping")
        return
    TABLES.mkdir(parents=True, exist_ok=True)

    def cell_seeds(runs: List[Dict[str, Any]], key: str, scale: float = 1.0) -> str:
        vals = [r["metrics"][key]["mean"] * scale for r in runs if key in r["metrics"]]
        if not vals:
            return "n/a"
        m = float(np.mean(vals))
        sd = float(np.std(vals))
        return f"{m:.1f} ± {sd:.1f}" if scale != 1.0 else f"{m:.3f} ± {sd:.3f}"

    out = []
    # Table III — QFS (single deterministic run; std across queries)
    rows = ["| System | Comprehensiveness | Diversity | n |", "| --- | --- | --- | --- |"]
    for s in SYSTEMS:
        runs = _load("behindthetech", s)
        if not runs:
            continue
        m = runs[0]["metrics"]
        rows.append(f"| {LABELS[s]} | {m['comprehensiveness']['mean']:.3f} ± "
                    f"{m['comprehensiveness']['std']:.3f} | {m['diversity']['mean']:.3f} ± "
                    f"{m['diversity']['std']:.3f} | {runs[0]['n']} |")
    out.append(("table_iii.md", rows))

    rows = ["| System | EM (%) | F1 (%) | Gold-evidence recall of retrieved context (%) |",
            "| --- | --- | --- | --- |"]
    for s in SYSTEMS:
        runs = _load("hotpotqa", s)
        if runs:
            rows.append(f"| {LABELS[s]} | {cell_seeds(runs, 'em', 100)} | "
                        f"{cell_seeds(runs, 'f1', 100)} | {cell_seeds(runs, 'ctx_recall', 100)} |")
    out.append(("table_iv.md", rows))

    rows = ["| System | Cit. Precision | Cit. Recall | Cit. F1 | Cit. Faithfulness | Answers with ≥1 citation (%) |",
            "| --- | --- | --- | --- | --- | --- |"]
    for s in SYSTEMS:
        runs = _load("hotpotqa", s)
        if runs:
            rows.append(f"| {LABELS[s]} | {cell_seeds(runs, 'cit_p')} | {cell_seeds(runs, 'cit_r')} | "
                        f"{cell_seeds(runs, 'cit_f1')} | {cell_seeds(runs, 'cit_faith')} | "
                        f"{cell_seeds(runs, 'cited_any', 100)} |")
    out.append(("table_v.md", rows))

    for name, rows in out:
        (TABLES / name).write_text("\n".join(rows) + "\n", encoding="utf-8")
        print(f"== {name}\n" + "\n".join(rows))
    _mark_stage_done("tables")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="eval.rag.experiment")
    ap.add_argument("stage", choices=["prepare", "index", "answer", "score", "tables", "all"])
    ap.add_argument("--task", default="all", choices=["all", *TASKS])
    ap.add_argument("--system", default="all", choices=["all", *SYSTEMS])
    a = ap.parse_args(argv)
    tasks = TASKS if a.task == "all" else (a.task,)
    syss = SYSTEMS if a.system == "all" else (a.system,)
    _log(f"stage={a.stage} tasks={tasks} systems={syss} ollama={OLLAMA} model={GEN_MODEL}")

    if a.stage in ("prepare", "all"):
        prepare()
    for t in tasks:
        if a.stage in ("index", "all"):
            if "veritasgraph" in syss or "veritasgraph_dense" in syss:
                index_veritasgraph(t)
            if "msrag" in syss:
                index_msrag(t)
        for s in syss:
            if a.stage in ("answer", "all"):
                answer(t, s)
            if a.stage in ("score", "all"):
                score(t, s)
    if a.stage in ("tables", "all"):
        tables()
    return 0


if __name__ == "__main__":
    sys.exit(main())
