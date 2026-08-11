"""The patient/cohort knowledge graph, backed by NetworkX.

Nodes: Patient, Encounter, Condition, Medication, LabResult, Procedure, Concept,
Span. Every clinical fact node is linked to the ``Span`` that evidences it via an
``EVIDENCED_BY`` edge, giving 100% citation attributability.

The graph is fully in-process and on-prem. A Neo4j backend can be swapped in
behind the same ``KnowledgeGraph`` API without touching the pipeline.
"""

from __future__ import annotations

import networkx as nx

from . import interactions as _interactions
from .models import AFFIRMED, Assertion, Span


class KnowledgeGraph:
    def __init__(self) -> None:
        self.g = nx.MultiDiGraph()

    # -- node helpers ------------------------------------------------------
    def _add(self, node_id: str, ntype: str, **attrs) -> str:
        if node_id not in self.g:
            self.g.add_node(node_id, ntype=ntype, **attrs)
        return node_id

    def add_patient(self, patient_id: str) -> str:
        return self._add(f"patient:{patient_id}", "Patient", patient_id=patient_id)

    def add_encounter(self, patient_id: str, doc_id: str, date: str | None, etype: str) -> str:
        pid = self.add_patient(patient_id)
        eid = self._add(
            f"encounter:{doc_id}", "Encounter", doc_id=doc_id, date=date, etype=etype
        )
        self._edge(pid, eid, "HAS_ENCOUNTER")
        return eid

    def _span_node(self, span: Span) -> str:
        sid = f"span:{span.doc_id}:{span.chunk_id}:{span.start}"
        return self._add(
            sid,
            "Span",
            doc_id=span.doc_id,
            chunk_id=span.chunk_id,
            section=span.section,
            start=span.start,
            end=span.end,
            text=span.text,
            citation=span.citation(),
        )

    def _edge(self, src: str, dst: str, rel: str, **attrs) -> None:
        if not self.g.has_edge(src, dst, key=rel):
            self.g.add_edge(src, dst, key=rel, rel=rel, **attrs)

    # -- ingestion ---------------------------------------------------------
    def add_assertion(self, patient_id: str, assertion: Assertion) -> str:
        """Add one reconciled assertion (and its provenance) for a patient."""
        pid = self.add_patient(patient_id)
        concept = assertion.concept
        node_id = f"{concept.key()}"

        rel_by_label = {
            "CONDITION": "HAS_CONDITION",
            "MEDICATION": "TAKES",
            "LAB": "HAS_LAB",
            "PROCEDURE": "HAD_PROCEDURE",
        }
        ntype_by_label = {
            "CONDITION": "Condition",
            "MEDICATION": "Medication",
            "LAB": "LabResult",
            "PROCEDURE": "Procedure",
        }
        rel = rel_by_label[assertion.label]
        ntype = ntype_by_label[assertion.label]

        # A patient-scoped fact node (so two patients don't share status/value).
        fact_id = f"{node_id}@{patient_id}"
        self._add(
            fact_id,
            ntype,
            system=concept.system,
            code=concept.code,
            display=concept.display,
            negation=assertion.negation,
            certainty=assertion.certainty,
            temporality=assertion.temporality,
            experiencer=assertion.experiencer,
            contradiction=assertion.contradiction,
            **assertion.attributes,
        )
        self._edge(pid, fact_id, rel)

        # Shared canonical concept node (for cohort grouping).
        cid = self._add(
            f"concept:{concept.key()}", "Concept",
            system=concept.system, code=concept.code, display=concept.display,
        )
        self._edge(fact_id, cid, "IS_A")

        # Provenance.
        for span in assertion.evidence:
            sid = self._span_node(span)
            self._edge(fact_id, sid, "EVIDENCED_BY")
        for span in assertion.conflicting_spans:
            sid = self._span_node(span)
            self._edge(fact_id, sid, "CONFLICTS_WITH")

        return fact_id

    # -- introspection -----------------------------------------------------
    def stats(self) -> dict:
        counts: dict[str, int] = {}
        for _, data in self.g.nodes(data=True):
            counts[data["ntype"]] = counts.get(data["ntype"], 0) + 1
        return {"nodes": self.g.number_of_nodes(), "edges": self.g.number_of_edges(), "by_type": counts}

    def facts_for(self, patient_id: str) -> list[dict]:
        pid = f"patient:{patient_id}"
        out: list[dict] = []
        if pid not in self.g:
            return out
        for _, fact_id, data in self.g.out_edges(pid, data=True):
            fdata = self.g.nodes[fact_id]
            if fdata["ntype"] in ("Condition", "Medication", "LabResult", "Procedure"):
                citations = [
                    self.g.nodes[s]["citation"]
                    for _, s, ed in self.g.out_edges(fact_id, data=True)
                    if self.g.nodes[s]["ntype"] == "Span" and ed["rel"] == "EVIDENCED_BY"
                ]
                out.append({**fdata, "node_id": fact_id, "citations": sorted(set(citations))})
        return out

    # -- drug-drug interaction enrichment ---------------------------------
    def enrich_drug_interactions(self) -> int:
        """Add ``INTERACTS_WITH`` edges between RxNorm ``Concept`` nodes.

        Uses the reference DDI table; only pairs where both concepts already
        exist in the graph are linked. Returns the number of edges added.
        """
        rx_concepts = {
            data["code"]: n
            for n, data in self.g.nodes(data=True)
            if data["ntype"] == "Concept" and data.get("system") == "RxNorm"
        }
        added = 0
        for ddi in _interactions.all_interactions():
            a, b = rx_concepts.get(ddi.rxnorm_a), rx_concepts.get(ddi.rxnorm_b)
            if not a or not b:
                continue
            if not self.g.has_edge(a, b, key="INTERACTS_WITH"):
                self.g.add_edge(
                    a, b, key="INTERACTS_WITH", rel="INTERACTS_WITH",
                    severity=ddi.severity, description=ddi.description, source=ddi.source,
                )
                added += 1
        return added

    def patient_interactions(self, patient_id: str) -> list[dict]:
        """Flag drug-drug interactions among a patient's affirmed medications.

        Each flag carries the interaction severity/description plus the source
        citations of BOTH medication facts, preserving provenance.
        """
        pid = f"patient:{patient_id}"
        if pid not in self.g:
            return []

        meds: list[dict] = []
        for _, fact_id, ed in self.g.out_edges(pid, data=True):
            fdata = self.g.nodes[fact_id]
            if (
                fdata["ntype"] == "Medication"
                and fdata.get("system") == "RxNorm"
                and fdata.get("negation") == AFFIRMED
            ):
                citations = [
                    self.g.nodes[s]["citation"]
                    for _, s, e in self.g.out_edges(fact_id, data=True)
                    if self.g.nodes[s]["ntype"] == "Span" and e["rel"] == "EVIDENCED_BY"
                ]
                meds.append({"code": fdata["code"], "display": fdata["display"],
                             "citations": sorted(set(citations))})

        flags: list[dict] = []
        for i in range(len(meds)):
            for j in range(i + 1, len(meds)):
                ddi = _interactions.interaction_for(meds[i]["code"], meds[j]["code"])
                if ddi is None:
                    continue
                flags.append({
                    "patient_id": patient_id,
                    "drug_a": meds[i]["display"],
                    "drug_b": meds[j]["display"],
                    "severity": ddi.severity,
                    "description": ddi.description,
                    "source": ddi.source,
                    "citations": sorted(set(meds[i]["citations"] + meds[j]["citations"])),
                })
        flags.sort(key=lambda f: _interactions.SEVERITY_RANK.get(f["severity"], 0), reverse=True)
        return flags

    def cytoscape(self, patient_id: str | None = None) -> dict:
        """Export nodes/edges for the UI graph viewer."""
        nodes, edges = [], []
        keep = set(self.g.nodes)
        if patient_id:
            pid = f"patient:{patient_id}"
            keep = {pid}
            keep |= set(nx.descendants(self.g, pid)) if pid in self.g else set()
        for n in keep:
            d = self.g.nodes[n]
            label = d.get("display") or d.get("patient_id") or d.get("doc_id") or d.get("text", n)
            nodes.append({"data": {"id": n, "label": str(label)[:40], "ntype": d["ntype"], **{k: str(v) for k, v in d.items() if k != "ntype"}}})
        for u, v, d in self.g.edges(data=True):
            if u in keep and v in keep:
                edges.append({"data": {"source": u, "target": v, "rel": d["rel"]}})
        return {"nodes": nodes, "edges": edges}
