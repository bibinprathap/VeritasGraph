"""End-to-end ingestion pipeline: de-id -> extract -> reconcile -> load -> query.

    Pipeline()
        .ingest(document)          # runs the 7-step flow for one note
        .query("... eGFR < 30")    # multi-hop cohort query with citations
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import assertion as _assertion
from . import extract as _extract
from . import query as _query
from .deidentify import SurrogateVault, deidentify
from .graph import KnowledgeGraph
from .models import Assertion, Document, PatientMatch


@dataclass
class IngestResult:
    doc_id: str
    patient_id: str
    replacements: int
    vault_id: str
    assertions: list[Assertion]
    contradictions: list[Assertion] = field(default_factory=list)


class Pipeline:
    def __init__(self, *, deid: bool = True) -> None:
        self.kg = KnowledgeGraph()
        self.vault = SurrogateVault()
        self.deid_enabled = deid
        self._ingested: list[IngestResult] = []

    def ingest(self, doc: Document) -> IngestResult:
        # 1-2. De-identify (Safe Harbor) into a sealed vault.
        if self.deid_enabled:
            deid = deidentify(doc.text, self.vault)
            text, replacements, vault_id = deid.text, deid.replacements, deid.vault_id
        else:
            text, replacements, vault_id = doc.text, 0, ""

        # 3. Extract entities with provenance + ConText axes.
        entities = _extract.extract(text, doc.doc_id)

        # 4. Reconcile into document-level assertions (+ contradictions).
        assertions = _assertion.reconcile(entities)

        # 5-6. Load into the knowledge graph with provenance edges.
        self.kg.add_encounter(doc.patient_id, doc.doc_id, doc.encounter_date, doc.encounter_type)
        for a in assertions:
            # Only assert facts about the patient that are affirmed OR are
            # explicit contradictions worth surfacing; negated/other-experiencer
            # facts are still stored so cohort queries can reason over them.
            self.kg.add_assertion(doc.patient_id, a)

        result = IngestResult(
            doc_id=doc.doc_id,
            patient_id=doc.patient_id,
            replacements=replacements,
            vault_id=vault_id,
            assertions=assertions,
            contradictions=[a for a in assertions if a.contradiction],
        )
        self._ingested.append(result)
        return result

    def ingest_all(self, docs: list[Document]) -> list[IngestResult]:
        return [self.ingest(d) for d in docs]

    # -- querying ----------------------------------------------------------
    def query(self, text: str) -> list[PatientMatch]:
        cohort = _query.parse_query(text)
        return _query.run(self.kg, cohort)

    def query_structured(self, cohort: "_query.CohortQuery") -> list[PatientMatch]:
        return _query.run(self.kg, cohort)

    # -- introspection -----------------------------------------------------
    def stats(self) -> dict:
        return self.kg.stats()

    @property
    def ingested(self) -> list[IngestResult]:
        return self._ingested
