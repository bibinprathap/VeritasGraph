"""Dataset loaders for the RAG evaluation harness.

Two corpora, matching the paper's Experimental Design:

* **HotpotQA** (distractor dev) — multi-hop QA (Task 2) and the gold supporting
  facts used to score attribution (Task 3).
* **"Behind the Tech"** transcripts — global query-focused summarisation (Task 1),
  the same corpus the MSRAG paper used.

Records are normalised to small dataclasses so the rest of the harness never
touches raw dataset formats. All loaders are deterministic given a seed and do
no network I/O — tests point them at ``tests/rag/fixtures``.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# --------------------------------------------------------------------------- #
# Record types
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class QARecord:
    """A multi-hop QA item with gold answer and gold supporting-fact ids."""

    id: str
    question: str
    answer: str
    supporting_facts: List[str]          # canonical chunk ids, e.g. "Title::0"
    context_docs: Dict[str, List[str]]   # title -> list of sentences


@dataclass(frozen=True)
class QFSCorpus:
    """A corpus plus a fixed list of global sensemaking queries."""

    corpus_id: str
    documents: List[Tuple[str, str]]     # (title, text)
    queries: List[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Canonical chunk id for a (title, sentence-index) supporting fact
# --------------------------------------------------------------------------- #
def fact_id(title: str, sent_idx: int) -> str:
    """Canonical, stable id for a HotpotQA supporting fact / context sentence."""
    return f"{title}::{int(sent_idx)}"


def canon_fact_id(fid: str) -> str:
    """Normalise a supporting-fact / chunk id to one canonical form.

    The harness has two historical separators: the official HotpotQA schema and
    ``fact_id`` use ``Title::i``, while the hand-labeled fixture uses ``Title#i``.
    Citation metrics are pure set intersection, so predicted and gold ids must be
    compared in a single canonical form. We canonicalise on ``Title::i``; ids that
    carry no recognisable separator are returned unchanged.
    """
    s = str(fid)
    if "::" in s:
        return s
    if "#" in s:
        title, _, idx = s.rpartition("#")
        if title and idx.isdigit():
            return f"{title}::{idx}"
    return s


# --------------------------------------------------------------------------- #
# HotpotQA
# --------------------------------------------------------------------------- #
def _normalise_hotpot_record(raw: dict) -> QARecord:
    """Normalise one raw HotpotQA distractor record.

    Raw schema (official): ``_id``, ``question``, ``answer``,
    ``supporting_facts`` = list of ``[title, sent_id]``,
    ``context`` = list of ``[title, [sentences]]``.

    The fixture schema (``hotpot_mini.json``) is already normalised with
    ``id``/``supporting_facts`` as canonical ids; we accept both.
    """
    rid = str(raw.get("_id") or raw.get("id"))
    question = str(raw["question"])
    answer = str(raw["answer"])

    context = raw.get("context") or raw.get("context_docs") or []
    context_docs: Dict[str, List[str]] = {}
    if isinstance(context, dict):
        # Already {title: [sentences]} (or fixture's {title: [ids]} — kept as-is).
        context_docs = {str(k): list(v) for k, v in context.items()}
    else:
        for entry in context:
            if isinstance(entry, (list, tuple)) and len(entry) == 2:
                title, sentences = entry
                context_docs[str(title)] = [str(s) for s in sentences]

    sup = raw.get("supporting_facts") or []
    supporting: List[str] = []
    for sf in sup:
        if isinstance(sf, str):
            supporting.append(sf)                    # already canonical (fixture)
        elif isinstance(sf, (list, tuple)) and len(sf) == 2:
            title, sent_idx = sf
            supporting.append(fact_id(str(title), int(sent_idx)))

    return QARecord(
        id=rid,
        question=question,
        answer=answer,
        supporting_facts=supporting,
        context_docs=context_docs,
    )


def load_hotpotqa(
    path: Path | str,
    *,
    limit: Optional[int] = None,
    seed: int = 42,
) -> List[QARecord]:
    """Load HotpotQA records, deterministically subsampled to ``limit``.

    Accepts both the official distractor JSON (a list of records) and the
    fixture's ``{"records": [...]}`` wrapper.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    records = data["records"] if isinstance(data, dict) else data
    if not isinstance(records, list):
        raise ValueError("HotpotQA file must contain a list of records")

    normalised = [_normalise_hotpot_record(r) for r in records]

    if limit is not None and limit < len(normalised):
        rng = random.Random(seed)
        idx = sorted(rng.sample(range(len(normalised)), limit))
        normalised = [normalised[i] for i in idx]

    return normalised


# --------------------------------------------------------------------------- #
# "Behind the Tech" global QFS corpus
# --------------------------------------------------------------------------- #
_DEFAULT_QFS_QUERIES = [
    "What are the main themes discussed across the dataset?",
    "Describe the relationship between AI and society discussed by the guests.",
    "What recurring concerns about technology do the guests raise?",
    "Summarise the different perspectives on innovation presented.",
]


def load_behindthetech(
    path: Path | str,
    *,
    limit: Optional[int] = None,
    queries: Optional[List[str]] = None,
) -> QFSCorpus:
    """Load the transcript corpus as a global QFS corpus.

    ``path`` may be a directory of ``*.txt`` transcripts or a single JSON file
    ``{"documents": [{"title":..., "text":...}], "queries": [...]}`` (used by
    tests). ``limit`` caps the number of documents loaded.
    """
    p = Path(path)
    documents: List[Tuple[str, str]] = []
    file_queries: Optional[List[str]] = None

    if p.is_file() and p.suffix == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        for doc in data.get("documents", []):
            documents.append((str(doc.get("title", "untitled")), str(doc.get("text", ""))))
        file_queries = data.get("queries")
    elif p.is_dir():
        for txt in sorted(p.glob("*.txt")):
            documents.append((txt.stem, txt.read_text(encoding="utf-8")))
    else:
        raise FileNotFoundError(f"behindthetech path not found: {p}")

    if limit is not None:
        documents = documents[:limit]

    chosen_queries = queries or file_queries or _DEFAULT_QFS_QUERIES
    return QFSCorpus(
        corpus_id=p.stem or "behindthetech",
        documents=documents,
        queries=list(chosen_queries),
    )
