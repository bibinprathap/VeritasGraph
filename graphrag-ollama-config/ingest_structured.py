"""
Structured-data ingester for VeritasGraph + VeritasReason.

Loads rows from any SQL database (or CSV) and emits two artefacts:

1. **Narrative text files** into ``input/`` so VeritasGraph's GraphRAG indexer
   can describe the records in natural language (and quote them).
2. **RDF triples** into the VeritasReason ``TripletStore`` so the rule engine
   can reason over them deterministically. Every triple carries a ``source``
   URI for W3C PROV-O attribution.

The example below targets a **procurement / SOX segregation-of-duties** schema
but the pattern generalises to any HRIS, EHR, or ERP system: define the
SQL → triple mapping in ``MAPPINGS`` and run ``ingest_structured(...)``.
"""

from __future__ import annotations

import os
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

import pandas as pd

try:
    import sqlalchemy
except ImportError:  # pragma: no cover
    sqlalchemy = None  # type: ignore[assignment]

try:
    from veritas_reason import TripletStore
except Exception:  # pragma: no cover - veritas_reason optional at import time
    TripletStore = None  # type: ignore[assignment]


SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_DIR = SCRIPT_DIR / "input"


# --------------------------------------------------------------------------- #
# Mapping declaration
# --------------------------------------------------------------------------- #
@dataclass
class TableMapping:
    """How a SQL table becomes triples + narrative text."""

    name: str
    sql: str
    subject: Callable[[pd.Series], str]
    triples: Callable[[pd.Series], Iterable[tuple[str, str, Any, dict]]]
    narrative: Callable[[pd.Series], str]
    source_uri: Callable[[pd.Series], str]


# --------------------------------------------------------------------------- #
# Example: Procurement / Segregation-of-Duties
# --------------------------------------------------------------------------- #
PROCUREMENT_MAPPINGS: list[TableMapping] = [
    TableMapping(
        name="employees",
        sql="SELECT emp_id, name, role, department FROM employees",
        subject=lambda r: f"emp:{r.emp_id}",
        triples=lambda r: [
            (f"emp:{r.emp_id}", "rdf:type", "proc:Employee", {}),
            (f"emp:{r.emp_id}", "proc:name", r.name, {}),
            (f"emp:{r.emp_id}", "proc:hasRole", f"role:{r.role}", {}),
            (f"emp:{r.emp_id}", "proc:department", r.department, {}),
        ],
        narrative=lambda r: (
            f"{r.name} (id {r.emp_id}) holds the role of {r.role} in the "
            f"{r.department} department."
        ),
        source_uri=lambda r: f"erp://employees/{r.emp_id}",
    ),
    TableMapping(
        name="purchase_orders",
        sql=(
            "SELECT po_id, vendor_id, amount, requested_by, approved_by, "
            "received_by, paid_by, created_at FROM purchase_orders "
            "WHERE created_at >= :from"
        ),
        subject=lambda r: f"po:{r.po_id}",
        triples=lambda r: [
            (f"po:{r.po_id}", "rdf:type", "proc:PurchaseOrder", {}),
            (f"po:{r.po_id}", "proc:vendor", f"vendor:{r.vendor_id}", {}),
            (f"po:{r.po_id}", "proc:amount", float(r.amount), {}),
            (f"po:{r.po_id}", "proc:requestedBy", f"emp:{r.requested_by}", {}),
            (f"po:{r.po_id}", "proc:approvedBy", f"emp:{r.approved_by}", {}),
            (f"po:{r.po_id}", "proc:receivedBy", f"emp:{r.received_by}", {}),
            (f"po:{r.po_id}", "proc:paidBy", f"emp:{r.paid_by}", {}),
            (f"po:{r.po_id}", "proc:createdAt", str(r.created_at), {}),
        ],
        narrative=lambda r: (
            f"Purchase order {r.po_id} for ${r.amount:,.2f} to vendor "
            f"{r.vendor_id} was requested by employee {r.requested_by}, "
            f"approved by {r.approved_by}, received by {r.received_by}, "
            f"and paid by {r.paid_by} on {r.created_at}."
        ),
        source_uri=lambda r: f"erp://purchase_orders/{r.po_id}",
    ),
    TableMapping(
        name="vendors",
        sql="SELECT vendor_id, name, owner_emp_id, status FROM vendors",
        subject=lambda r: f"vendor:{r.vendor_id}",
        triples=lambda r: [
            (f"vendor:{r.vendor_id}", "rdf:type", "proc:Vendor", {}),
            (f"vendor:{r.vendor_id}", "proc:name", r.name, {}),
            (f"vendor:{r.vendor_id}", "proc:status", r.status, {}),
        ] + (
            [(f"vendor:{r.vendor_id}", "proc:relatedEmployee",
              f"emp:{r.owner_emp_id}", {})]
            if pd.notna(r.owner_emp_id) else []
        ),
        narrative=lambda r: (
            f"Vendor {r.name} (id {r.vendor_id}, status {r.status})"
            + (f" is related to employee {r.owner_emp_id}."
               if pd.notna(r.owner_emp_id) else ".")
        ),
        source_uri=lambda r: f"erp://vendors/{r.vendor_id}",
    ),
]


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def ingest_structured(
    db_url: str | None = None,
    mappings: list[TableMapping] | None = None,
    sql_params: dict | None = None,
    triplet_store: Any | None = None,
    write_narrative: bool = True,
) -> dict:
    """Load tables → emit triples + narrative text files.

    Returns a small report dict suitable for logging / display in the UI.
    """
    db_url = db_url or os.environ.get("ERP_DB_URL") or os.environ.get("HRIS_DB_URL")
    if not db_url:
        raise RuntimeError(
            "No database URL configured. Set ERP_DB_URL or HRIS_DB_URL "
            "in the environment, or pass db_url= explicitly."
        )
    if sqlalchemy is None:
        raise RuntimeError("sqlalchemy is required: pip install sqlalchemy")

    mappings = mappings or PROCUREMENT_MAPPINGS
    sql_params = sql_params or {"from": "2026-01-01"}
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    if triplet_store is None:
        if TripletStore is None:
            raise RuntimeError(
                "veritas_reason is not installed. Run: "
                "pip install -e ./veritas-reason"
            )
        triplet_store = TripletStore.connect()

    engine = sqlalchemy.create_engine(db_url)
    report = {"started_at": datetime.utcnow().isoformat(), "tables": {}}

    for mapping in mappings:
        df = pd.read_sql(sqlalchemy.text(mapping.sql), engine, params=sql_params)
        triple_count = 0
        narratives: list[str] = []

        for _, row in df.iterrows():
            source = mapping.source_uri(row)
            for s, p, o, qual in mapping.triples(row):
                triplet_store.add(s, p, o, source=source, qualifiers=qual)
                triple_count += 1
            if write_narrative:
                narratives.append(mapping.narrative(row))

        if write_narrative and narratives:
            out_path = INPUT_DIR / f"structured_{mapping.name}.txt"
            out_path.write_text("\n".join(narratives), encoding="utf-8")

        report["tables"][mapping.name] = {
            "rows": int(len(df)),
            "triples": triple_count,
            "narrative_file": (
                str(INPUT_DIR / f"structured_{mapping.name}.txt")
                if write_narrative else None
            ),
        }

    report["finished_at"] = datetime.utcnow().isoformat()
    return report


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(ingest_structured(), indent=2, default=str))
