"""Answerability: can the graph answer this question, before an LLM is called?

:func:`check_answerable` reports which entities and glossary terms a question
touches, which content words nothing in the graph covers, and a coverage ratio.

* ``exploratory`` — answerable when at least one entity matches.
* ``governed`` — additionally requires a **certified** glossary term in the
  question, so governed answers only ever rest on reviewed meaning.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from veritasgraph.ontology import key
from veritasgraph.text import norm, query_tokens

MODES = ("exploratory", "governed")


def _covered(token: str, phrases: List[str]) -> bool:
    rx = re.compile(rf"(?<!\w){re.escape(token)}")
    return any(rx.search(p) for p in phrases)


def check_answerable(engine: Any, question: str, mode: str = "exploratory") -> Dict[str, Any]:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    with engine._read():
        seeds: List[str] = engine._seed_entities(question)
        seed_names = [engine.entities[s]["name"] for s in seeds if s in engine.entities]
        empty = not engine.entities
    ontology = getattr(engine, "ontology", None)
    terms = ontology.match_terms(question) if ontology is not None else []
    certified = [t for t in terms if t["status"] == "certified"]

    tokens = query_tokens(question)
    phrases = [norm(n) for n in seed_names]
    for term in terms:
        phrases.append(term["norm_name"])
        phrases.extend(term["synonyms"])
    phrases = [key(p) for p in phrases]
    unmatched = [t for t in tokens if not _covered(t, phrases)]
    coverage = 1.0 if not tokens else round((len(tokens) - len(unmatched)) / len(tokens), 3)

    answerable = bool(seeds) and (mode != "governed" or bool(certified))
    reason = None
    if not answerable:
        if empty:
            reason = "the knowledge graph is empty."
        elif not seeds:
            reason = "none of the entities in the question appear in the knowledge graph."
        else:
            reason = (
                "no certified glossary term covers the question"
                + (f" (proposed only: {', '.join(t['name'] for t in terms)})" if terms else "")
                + "."
            )
    return {
        "answerable": answerable,
        "mode": mode,
        "coverage": coverage,
        "matched_entities": [{"id": s, "name": n} for s, n in zip(seeds, seed_names)],
        "matched_terms": [
            {"id": t["id"], "name": t["name"], "status": t["status"]} for t in terms
        ],
        "unmatched_tokens": unmatched,
        "reason": reason,
    }
