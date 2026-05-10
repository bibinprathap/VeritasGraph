# Plan: Enterprise Policy Compliance with VeritasGraph + VeritasReason

## Understanding the Two Projects

### VeritasGraph (parent repo)
A **GraphRAG** framework (built on Microsoft GraphRAG + Ollama) that ingests **unstructured text** (PDFs, articles, YouTube transcripts) and builds a knowledge graph of *entities → relationships → community summaries*. Pipeline:

- [graphrag-ollama-config/ingest.py](../graphrag-ollama-config/ingest.py) – pulls text into [graphrag-ollama-config/input/](../graphrag-ollama-config/input)
- `graphrag index` builds Parquet tables (`create_final_entities`, `create_final_relationships`, `create_final_community_reports`) in [graphrag-ollama-config/output/](../graphrag-ollama-config/output)
- [graphrag-ollama-config/app.py](../graphrag-ollama-config/app.py) – Gradio UI runs `local`, `global`, `reasoning`, `hybrid` searches over those Parquet tables

**Strength:** multi-hop reasoning + citation over **prose**.
**Weakness:** no native concept of structured records (who clocked in when, employee IDs, dates).

### VeritasReason (this repo)
An **accountability/intelligence layer** on top of an LLM stack. From [veritasreason/](veritasreason/) you can see modules for `ontology/`, `reasoning/` (forward chaining, Rete networks, deductive/abductive, SPARQL), `provenance/` (W3C PROV-O), `conflicts/`, `kg/`, `triplet_store/`, `change_management/`. It is rule-based and explainable — exactly what you need to evaluate *policy clauses* against *facts*.

---

## Why VeritasGraph alone can't answer "Which expense reports breach the per-diem cap?"

That question is a **rule-evaluation problem**, not a similarity-search problem. It needs:

1. The **policy** ("meal reimbursements may not exceed $75 per traveler per day").
2. **Structured facts** (each expense line × employee × date × category × amount).
3. A **reasoner** that joins them and emits violators.

VeritasGraph chunks text and does graph RAG; it will *describe* the policy but won't *enumerate violators* deterministically. You need to combine it with VeritasReason's reasoning engine and a SQL/structured loader.

---

## Recommended Architecture

```
┌──────────────────┐   ┌────────────────────┐   ┌───────────────────┐
│ Policy PDFs/Docs │   │ Expense DB         │   │ Employee Master   │
│ (T&E handbook)   │   │ (Postgres / MySQL) │   │ (HRIS / CSV)      │
└────────┬─────────┘   └──────────┬─────────┘   └─────────┬─────────┘
         │                        │                       │
         ▼                        ▼                       ▼
 ┌──────────────────┐   ┌────────────────────────────────────────┐
 │ VeritasGraph     │   │ Structured Loader (new module)         │
 │ Indexer (text)   │   │ → emits triples into VeritasReason KG  │
 │  → entities,     │   │   (:Exp-1234)-[:AMOUNT 92.40]→         │
 │    relationships │   │   (:Date 2026-04-12)                   │
 └────────┬─────────┘   └──────────────┬─────────────────────────┘
          │                            │
          └─────────────┬──────────────┘
                        ▼
          ┌──────────────────────────────┐
          │ Unified Knowledge Graph      │
          │ (VeritasReason triplet_store)    │
          └──────────────┬───────────────┘
                         ▼
          ┌──────────────────────────────┐
          │ VeritasReason Reasoner           │
          │  - Rete / forward chaining   │
          │  - Rules derived from policy │
          │  - Provenance per fact       │
          └──────────────┬───────────────┘
                         ▼
          ┌──────────────────────────────────┐
          │ VeritasGraph Query UI            │
          │ "Which expense reports breach    │
          │  the per-diem cap?"              │
          │ → Violators + citation +         │
          │   policy clause + evidence       │
          └──────────────────────────────────┘
```

---

## Concrete Steps to Modify VeritasGraph

### 1. Add a structured-data ingester
Create `graphrag-ollama-config/ingest_structured.py` that connects to your DB and emits two things:

- **GraphRAG-compatible text** for the policy + each employee's leave summary (so RAG can quote it).
- **Triples** for VeritasReason:

```python
# pseudo
import sqlalchemy, pandas as pd
from veritasreason.triplet_store import TripletStore

eng = sqlalchemy.create_engine(os.environ["FINANCE_DB_URL"])
emp   = pd.read_sql("SELECT emp_id, name, dept, manager_id FROM employees", eng)
lines = pd.read_sql("""SELECT report_id, emp_id, expense_date, category, amount, currency
                       FROM expense_lines WHERE expense_date >= :from""", eng,
                    params={"from": "2026-04-01"})

ts = TripletStore.connect()
for _, r in emp.iterrows():
    ts.add(f"emp:{r.emp_id}", "rdf:type", "hr:Employee",
           source=f"hris://employees/{r.emp_id}")
    ts.add(f"emp:{r.emp_id}", "hr:name",       r.name)
    ts.add(f"emp:{r.emp_id}", "hr:department", r.dept)

for _, r in lines.iterrows():
    src = f"finance://expense_lines/{r.report_id}"
    ts.add(f"exp:{r.report_id}", "rdf:type",        "fin:ExpenseLine", source=src)
    ts.add(f"exp:{r.report_id}", "fin:submittedBy", f"emp:{r.emp_id}", source=src)
    ts.add(f"exp:{r.report_id}", "fin:incurredOn",  f"date:{r.expense_date}", source=src)
    ts.add(f"exp:{r.report_id}", "fin:category",    f"cat:{r.category}", source=src)
    ts.add(f"exp:{r.report_id}", "fin:amount",      float(r.amount),
           qualifiers={"currency": r.currency}, source=src)
```

Every triple carries **provenance** (`source=`) — that's how you keep VeritasGraph's "100% verifiable attribution" promise on structured data.

### 2. Encode the policy as rules
Have the LLM read the policy doc once and propose rules; a human approves them and stores them in `rules/expense_policy.yaml`:

```yaml
- id: EXP-01
  description: "Meal expenses above the $75 / day per-diem cap are a violation."
  when:
    - (?x rdf:type fin:ExpenseLine)
    - (?x fin:category cat:Meals)
    - (?x fin:amount   ?amt)  filter(?amt > 75)
  then:
    - (?x fin:violates policy:ExpensePolicy#EXP-01)
  cite:
    - policy_doc: "Travel_and_Expense_Policy_2026.pdf#section-2.3"
```

Load with [veritasreason/reasoning](veritasreason/reasoning) (Rete forward chainer). Each derived violation triple keeps both the **policy clause** and the **expense rows** as PROV-O sources.

### 3. Add a new query type in the UI
In [graphrag-ollama-config/app.py](../graphrag-ollama-config/app.py) the `QUERY_TYPE_OPTIONS` list already has `global`, `local`, `reasoning`, `hybrid`. Add:

```python
QUERY_TYPE_OPTIONS = [..., "policy_compliance"]
```

and a handler that:

1. Uses VeritasGraph's RAG to **identify which policy** the user is asking about ("per-diem" / "expense policy" → `policy:ExpensePolicy`).
2. Calls VeritasReason's reasoner to fire the rules tagged with that policy.
3. Returns a table of offending expense lines **plus** the rule, the clause text from the PDF, and the underlying expense rows.

```python
async def policy_compliance_search(question, ...):
    # a) retrieve policy context from GraphRAG
    policy_ctx = await reasoning_local_search(question, ...)
    policy_id  = llm_pick_policy(policy_ctx, question)   # e.g. "ExpensePolicy"

    # b) run VeritasReason reasoner
    from veritasreason.reasoning import ForwardChainer
    fc = ForwardChainer(rules_dir="rules/")
    derived = fc.run(filter_tag=policy_id)               # adds fin:violates triples

    # c) materialise answer
    violators = ts.query("""
        SELECT ?exp ?emp ?amt ?date
        WHERE { ?exp fin:violates  policy:ExpensePolicy#EXP-01 ;
                     fin:submittedBy ?emp ;
                     fin:amount      ?amt ;
                     fin:incurredOn  ?date .
                FILTER(?date >= '2026-04-01' && ?date < '2026-07-01') }""")

    return render_with_citations(violators, policy_ctx, derived.provenance)
```

### 4. Wire provenance into the existing UI
VeritasGraph already shows source spans for text answers. Extend the response renderer so each violator row links to:
- the policy paragraph (already a GraphRAG `text_unit_id`),
- the SQL row (`finance://expense_lines/<report_id>`).

Both come from VeritasReason's `provenance/` module — no new plumbing needed.

### 5. Keep it answerable in natural language
The user types: *"Which expense reports breached the per-diem cap last quarter?"*

Pipeline:
1. **VeritasGraph RAG** finds the policy doc and clause.
2. **LLM router** decides this is a `policy_compliance` query (vs. an explanatory one).
3. **VeritasReason** evaluates `EXP-01` over the expense-line triples.
4. **LLM** turns the result set into prose: *"3 expense reports violated EXP-01 in Q2 2026: EXP-1188 ($92.40 meal, Anu), EXP-1204 ($118.00 meal, Ravi)… Rule: §2.3 of the Travel & Expense Policy (cited)."*

---

## Minimal Change Checklist

| File / Module | Change |
|---|---|
| [graphrag-ollama-config/ingest.py](../graphrag-ollama-config/ingest.py) | Add DB connector branch alongside YouTube/Web |
| New `graphrag-ollama-config/ingest_structured.py` | SQL → text + VeritasReason triples |
| New `rules/*.yaml` | Policy rules (one file per policy) |
| New `graphrag-ollama-config/policy_search.py` | Orchestrates RAG + VeritasReason reasoner |
| [graphrag-ollama-config/app.py](../graphrag-ollama-config/app.py) | Add `policy_compliance` query type + handler + result table |
| `requirements.txt` | Add `veritasreason`, `sqlalchemy`, DB driver |
| `.env` | `FINANCE_DB_URL=postgresql://…` |

---

## Why this split is the right call

- **Unstructured policy text** → GraphRAG (VeritasGraph) is best-in-class.
- **Structured facts + deterministic rules** → VeritasReason's reasoner gives auditable, repeatable answers (critical for HR/compliance).
- **Provenance** is preserved end-to-end, which is VeritasGraph's core promise.
- You avoid the anti-pattern of asking an LLM to "count absences" — it will hallucinate. The reasoner does the counting; the LLM only narrates.
