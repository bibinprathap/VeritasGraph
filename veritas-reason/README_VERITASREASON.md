# VeritasReason

> Deterministic reasoning & decision-intelligence layer for **[VeritasGraph](../README.md)**.

VeritasGraph excels at multi-hop retrieval over **unstructured text** (policies,
contracts, reports). VeritasReason adds the missing half of an enterprise answer:
**deterministic, auditable rule evaluation over structured facts** — purchase
orders, attendance rows, ledger entries, lab results — with full W3C PROV-O
provenance on every derived fact.

This directory contains the upstream VeritasReason engine (forward chaining, Rete,
SPARQL, conflict detection, deduplication) plus a lightweight `veritas_reason`
namespace that re-exports it under the VeritasGraph brand.

## Where it fits

```
                ┌──────────────────────────────┐
  unstructured  │ VeritasGraph (GraphRAG)      │  multi-hop retrieval,
  ───────────▶  │  entities, communities, RAG  │  citations over prose
                └──────────────┬───────────────┘
                               │ policy clauses, ontology hints
                               ▼
                ┌──────────────────────────────┐
  structured    │ VeritasReason (this folder)  │  rule firing, conflicts,
  ───────────▶  │  triplet store + reasoner    │  PROV-O on every fact
                └──────────────┬───────────────┘
                               ▼
                       compliance answer
```

See the parent project's [Enterprise Compliance section](../README.md#-enterprise-compliance-veritasgraph--veritasreason)
for an end-to-end procurement-fraud example, and
[plan.md](plan.md) for the original design notes and a leave-policy walk-through.

## Install

```bash
pip install -e ./veritas-reason          # installs upstream veritasreason + wrapper
```

## Quick start

```python
from veritas_reason import TripletStore, ForwardChainer, RuleSet

ts = TripletStore.connect()
rules = RuleSet.load("rules/")
chainer = ForwardChainer(ts, rules)
result = chainer.run()

for fact, prov in result.derivations:
    print(fact, "←", prov.cited_sources)
```

The engine itself is documented in [README.md](README.md) (the original
VeritasReason documentation, kept verbatim for reference).
