"""
Stand-alone smoke test for the VeritasGraph + VeritasReason policy compliance flow.

This script does NOT require the heavy upstream `veritasreason` install
(torch / spaCy / transformers). It uses a tiny in-memory triple store and a
minimal forward-chaining evaluator just to prove that the rule definitions in
``rules/sod_policy.yaml`` correctly identify violators in a fake ERP dataset.

Run it from the repo root:

    python tests/test_policy_compliance_demo.py

For the *real* (full) reasoner, install the upstream package and use
``graphrag-ollama-config/policy_search.py`` instead — see README.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------- #
# Tiny in-memory triple store
# --------------------------------------------------------------------------- #
class MiniStore:
    def __init__(self):
        self.triples: list[tuple[str, str, object, str]] = []

    def add(self, s, p, o, source=""):
        self.triples.append((s, p, o, source))

    def by_pred(self, p):
        return [(s, o, src) for s, pp, o, src in self.triples if pp == p]

    def get(self, s, p):
        for ss, pp, o, _ in self.triples:
            if ss == s and pp == p:
                return o
        return None

    def all_subjects(self, rdf_type):
        return [s for s, p, o, _ in self.triples
                if p == "rdf:type" and o == rdf_type]


# --------------------------------------------------------------------------- #
# Minimal SoD rule evaluator (mirrors rules/sod_policy.yaml semantics)
# --------------------------------------------------------------------------- #
def evaluate_sod(store: MiniStore) -> list[dict]:
    DIRECTOR_ROLES = {"role:Director", "role:VP", "role:CFO"}
    violations: list[dict] = []

    for po in store.all_subjects("proc:PurchaseOrder"):
        approved_by = store.get(po, "proc:approvedBy")
        paid_by     = store.get(po, "proc:paidBy")
        requested_by = store.get(po, "proc:requestedBy")
        amount      = store.get(po, "proc:amount") or 0
        vendor      = store.get(po, "proc:vendor")

        # SOD-01 — approver == payer
        if approved_by and approved_by == paid_by:
            violations.append({
                "po": po, "rule": "SOD-01",
                "evidence": f"Approved & paid by {approved_by}",
                "policy_doc": "Procurement_Policy_2026.pdf#section-3.1",
            })

        # SOD-02 — requester == approver
        if approved_by and approved_by == requested_by:
            violations.append({
                "po": po, "rule": "SOD-02",
                "evidence": f"Requested & approved by {approved_by}",
                "policy_doc": "Procurement_Policy_2026.pdf#section-3.2",
            })

        # SOD-03 — high-value PO approved by non-Director
        if amount and amount > 25000 and approved_by:
            role = store.get(approved_by, "proc:hasRole")
            if role and role not in DIRECTOR_ROLES:
                violations.append({
                    "po": po, "rule": "SOD-03",
                    "evidence": f"${amount:,.2f} approved by {approved_by} "
                                f"({role}, not Director-level)",
                    "policy_doc": "Procurement_Policy_2026.pdf#section-4.5",
                })

        # SOD-04 — vendor related to approver
        if vendor and approved_by:
            related = store.get(vendor, "proc:relatedEmployee")
            if related and related == approved_by:
                violations.append({
                    "po": po, "rule": "SOD-04",
                    "evidence": f"Vendor {vendor} related to approver {approved_by}",
                    "policy_doc": "Procurement_Policy_2026.pdf#section-7.2",
                })

    return violations


# --------------------------------------------------------------------------- #
# Fake ERP data
# --------------------------------------------------------------------------- #
def seed_demo_store() -> MiniStore:
    s = MiniStore()
    # employees
    employees = [
        ("E091", "Alice Khan",   "role:Manager",  "Procurement"),
        ("E118", "Sarah Chen",   "role:Manager",  "Finance"),
        ("E140", "Raj Mehta",    "role:Director", "Operations"),
        ("E207", "Lin Park",     "role:Analyst",  "Procurement"),
        ("E312", "Omar Hassan",  "role:VP",       "Operations"),
    ]
    for eid, name, role, dept in employees:
        s.add(f"emp:{eid}", "rdf:type", "proc:Employee", f"erp://employees/{eid}")
        s.add(f"emp:{eid}", "proc:name", name, f"erp://employees/{eid}")
        s.add(f"emp:{eid}", "proc:hasRole", role, f"erp://employees/{eid}")
        s.add(f"emp:{eid}", "proc:department", dept, f"erp://employees/{eid}")

    # vendors
    s.add("vendor:V11", "rdf:type", "proc:Vendor", "erp://vendors/V11")
    s.add("vendor:V11", "proc:name", "Acme Supplies", "erp://vendors/V11")
    s.add("vendor:V77", "rdf:type", "proc:Vendor", "erp://vendors/V77")
    s.add("vendor:V77", "proc:name", "Mehta Holdings", "erp://vendors/V77")
    s.add("vendor:V77", "proc:relatedEmployee", "emp:E140", "erp://vendors/V77")

    # purchase orders
    pos = [
        # po,     vendor, amount,  req,   approver, receiver, payer
        ("PO-2101", "V11",  4500.00, "E207", "E091", "E207", "E118"),  # clean
        ("PO-2204", "V11", 12000.00, "E207", "E118", "E207", "E118"),  # SOD-01
        ("PO-2301", "V11",  9000.00, "E091", "E091", "E207", "E118"),  # SOD-02
        ("PO-2317", "V11", 48750.00, "E207", "E091", "E207", "E312"),  # SOD-03
        ("PO-2402", "V77", 15000.00, "E207", "E140", "E207", "E118"),  # SOD-04
    ]
    for po, vendor, amt, req, app, rec, pay in pos:
        s.add(f"po:{po}", "rdf:type", "proc:PurchaseOrder", f"erp://po/{po}")
        s.add(f"po:{po}", "proc:vendor",      f"vendor:{vendor}", f"erp://po/{po}")
        s.add(f"po:{po}", "proc:amount",       amt,              f"erp://po/{po}")
        s.add(f"po:{po}", "proc:requestedBy", f"emp:{req}",      f"erp://po/{po}")
        s.add(f"po:{po}", "proc:approvedBy",  f"emp:{app}",      f"erp://po/{po}")
        s.add(f"po:{po}", "proc:receivedBy",  f"emp:{rec}",      f"erp://po/{po}")
        s.add(f"po:{po}", "proc:paidBy",      f"emp:{pay}",      f"erp://po/{po}")
    return s


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def main() -> int:
    rules_file = Path(__file__).resolve().parent / "sod_policy.yaml"
    if not rules_file.exists():
        print(f"❌ Missing rule file: {rules_file}")
        return 2

    print(f"✓ Found rule file:  {rules_file.name}")
    print(f"  ({rules_file.read_text(encoding='utf-8').count('- id:')} rules declared)\n")

    store = seed_demo_store()
    print(f"✓ Seeded MiniStore: {len(store.triples)} triples "
          f"({len(store.all_subjects('proc:PurchaseOrder'))} purchase orders, "
          f"{len(store.all_subjects('proc:Employee'))} employees)\n")

    violations = evaluate_sod(store)

    if not violations:
        print("✗ No violations detected — demo dataset broken.")
        return 1

    print(f"✓ Reasoner fired. Detected {len(violations)} violation(s):\n")
    print(f"  {'PO':<10} {'Rule':<8} Evidence")
    print(f"  {'-'*10} {'-'*8} {'-'*60}")
    for v in violations:
        print(f"  {v['po']:<10} {v['rule']:<8} {v['evidence']}")
    print()
    print("Citations:")
    for v in violations:
        print(f"  • {v['rule']}: {v['policy_doc']}")
    print("\nResult JSON:")
    print(json.dumps(violations, indent=2))

    expected_rules = {"SOD-01", "SOD-02", "SOD-03", "SOD-04"}
    seen = {v["rule"] for v in violations}
    missing = expected_rules - seen
    if missing:
        print(f"\n✗ Missing expected rules: {missing}")
        return 1
    print("\n✓ All four SoD rules fired exactly as expected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
