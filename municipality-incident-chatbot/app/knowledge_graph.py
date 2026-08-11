"""VeritasGraph-backed municipal knowledge graph.

This module is the **Knowledge & Reasoning Layer** from ``01_architecture.md``.
It uses the real VeritasGraph GraphRAG engine
(:class:`studio_api.graphrag_engine.GraphRAGEngine`) to:

* store the municipal knowledge graph (incident types, departments, SLAs,
  policies) via ``import_graph`` — no LLM required;
* **classify** a free-text complaint into an incident category (intent layer);
* **route** a category to its responsible department + SLA using genuine
  multi-hop graph *retrieval* (``engine.retrieve``);
* produce a **grounded reply** built only from retrieved graph facts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config

# Isolate the municipality graph snapshot from the Studio graph BEFORE the
# VeritasGraph engine module computes its data-dir constant.
config.DATA_DIR.mkdir(parents=True, exist_ok=True)
os.environ["STUDIO_DATA_DIR"] = str(config.DATA_DIR)

from studio_api.graphrag_engine import GraphRAGEngine  # noqa: E402

from .seed_data import municipal_graph  # noqa: E402


def _meta(node: Dict[str, Any]) -> Dict[str, Any]:
    """Return the metadata dict attached to an imported node."""
    return (node.get("origin") or {}).get("meta") or {}


class MunicipalKnowledgeGraph:
    """Grounding + routing over the VeritasGraph engine."""

    def __init__(self, engine: Optional[GraphRAGEngine] = None) -> None:
        self.engine = engine or GraphRAGEngine()
        self.seed()

    # ------------------------------------------------------------------ #
    # Seeding
    # ------------------------------------------------------------------ #
    def seed(self) -> Dict[str, Any]:
        """Idempotently load the municipal graph into VeritasGraph."""
        return self.engine.import_graph(
            municipal_graph(),
            fmt="generic",
            source_type="curated",
            merge_strategy="overwrite",
            title="Department of Municipality KG",
        )

    # ------------------------------------------------------------------ #
    # Incident-type lookups
    # ------------------------------------------------------------------ #
    def _incident_nodes(self) -> List[Dict[str, Any]]:
        return [
            e for e in self.engine.entities.values()
            if e.get("type") == "incident_type"
        ]

    def incident(self, code: str) -> Optional[Dict[str, Any]]:
        """Return the incident-type node whose origin id == ``code``."""
        for node in self._incident_nodes():
            if (node.get("origin") or {}).get("origin_id") == code:
                m = _meta(node)
                return {
                    "code": code,
                    "label": node["name"],
                    "description": node.get("description", ""),
                    "cv_labels": m.get("cv_labels", []),
                    "min_confidence": float(m.get("min_confidence", 0.5)),
                    "aliases": m.get("aliases", []),
                }
        return None

    # ------------------------------------------------------------------ #
    # Classification (intent layer)
    # ------------------------------------------------------------------ #
    def classify(self, text: str) -> Optional[str]:
        """Map free text to an incident code via alias/keyword matching.

        Returns the incident code, or ``None`` when nothing matches (which the
        orchestrator treats as "out of scope").
        """
        t = f" {text.lower().strip()} "
        best_code: Optional[str] = None
        best_len = 0
        for node in self._incident_nodes():
            code = (node.get("origin") or {}).get("origin_id")
            m = _meta(node)
            terms = list(m.get("aliases", [])) + [node["name"].lower()] + \
                list(m.get("cv_labels", []))
            for term in terms:
                term = str(term).lower().strip()
                if not term:
                    continue
                # Prefer the longest matching alias for specificity.
                if f" {term} " in t or term in t.split():
                    if len(term) > best_len:
                        best_len = len(term)
                        best_code = code
        return best_code

    # ------------------------------------------------------------------ #
    # Routing (multi-hop graph retrieval)
    # ------------------------------------------------------------------ #
    def route(self, code: str) -> Optional[Dict[str, Any]]:
        """Resolve department + SLA + policies for a category via retrieval."""
        incident = self.incident(code)
        if incident is None:
            return None

        ctx = self.engine.retrieve(incident["label"], max_depth=2, max_nodes=25)
        nodes = ctx.get("nodes", [])
        edges = ctx.get("edges", [])

        department: Optional[Dict[str, Any]] = None
        sla: Optional[Dict[str, Any]] = None
        policies: List[str] = []
        for node in nodes:
            ntype = node.get("type")
            if ntype == "department" and department is None:
                department = {"name": node["name"], "contact": _meta(node).get("contact", "")}
            elif ntype == "sla" and sla is None:
                m = _meta(node)
                sla = {
                    "response_hours": int(m.get("response_hours", 24)),
                    "priority": m.get("priority", "medium"),
                }
            elif ntype == "policy":
                policies.append(node["name"])

        id_to_name = {n["id"]: n["name"] for n in nodes}
        reasoning_path = [
            f"{id_to_name.get(e['source'], '?')} --[{e.get('description') or 'related_to'}]--> "
            f"{id_to_name.get(e['target'], '?')}"
            for e in edges
        ]

        return {
            "incident": incident,
            "department": department or {"name": "General Enquiries", "contact": ""},
            "sla": sla or {"response_hours": 48, "priority": "medium"},
            "policies": policies,
            "reasoning_path": reasoning_path,
            "subgraph": {"nodes": nodes, "edges": edges},
        }

    # ------------------------------------------------------------------ #
    # Grounded reply
    # ------------------------------------------------------------------ #
    def grounded_reply(self, route: Dict[str, Any]) -> str:
        """Build a citizen-facing answer using ONLY retrieved graph facts."""
        inc = route["incident"]
        dept = route["department"]
        sla = route["sla"]
        policy = f" Under our {route['policies'][0]}," if route.get("policies") else ""
        return (
            f"Thanks for reporting a possible **{inc['label']}** issue.{policy} "
            f"this is handled by the **{dept['name']}** "
            f"(target response: {sla['response_hours']}h, priority: {sla['priority']}). "
            f"Let me verify your photo and location before I register the case."
        )
