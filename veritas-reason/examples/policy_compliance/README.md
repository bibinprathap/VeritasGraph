# Policy-Compliance Example

This example demonstrates the **VeritasReason** rule engine on a Procurement /
Segregation-of-Duties (SoD) policy. Run it from anywhere — it depends only on
the Python standard library and ships with the rule file
[sod_policy.yaml](sod_policy.yaml).

```bash
python run_demo.py
```

Expected output (abridged):

```
✓ Found rule file:  sod_policy.yaml (4 rules declared)
✓ Seeded MiniStore: 60 triples (5 purchase orders, 5 employees)
✓ Reasoner fired. Detected 4 violation(s):
  po:PO-2204 SOD-01   Approved & paid by emp:E118
  po:PO-2301 SOD-02   Requested & approved by emp:E091
  po:PO-2317 SOD-03   $48,750 approved by emp:E091 (role:Manager, not Director-level)
  po:PO-2402 SOD-04   Vendor V77 related to approver emp:E140
```

See the parent project's [README](https://github.com/Hawksight-AI/veritas-reason)
for the production wiring (live SQL ingester, GraphRAG policy retrieval, and
LLM narration with PROV-O citations).
