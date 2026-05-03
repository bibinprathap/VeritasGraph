# 📣 Marketing Copy — VeritasGraph + VeritasReason launch

> Paste-ready posts for the v0.4.0 launch. **Manual posting only** — do not
> automate from a personal browser profile, that violates every platform's ToS.
> If you want programmatic posting, use each platform's official developer API
> with your own credentials.

---

## 🐦 X / Twitter (≤ 280 chars)

> 🚀 Open-sourced **VeritasGraph + VeritasReason** — GraphRAG that doesn't just retrieve, it *reasons* over your policies.
>
> Ask "which POs violate SoD?" → get violators, the rule, and the citation. 100% local.
>
> `pip install veritas-reason`
>
> github.com/bibinprathap/VeritasGraph

---

## 💼 LinkedIn (long-form)

> Most "AI compliance" demos answer **"what does the policy say?"**.
> The hard enterprise question is the inverse:
> **"Who is currently violating it — and prove it."**
>
> That needs three things vector RAG can't give you:
>   1. A **graph** of who-did-what (employees, POs, vendors, approvals).
>   2. A **rule engine** that runs forward-chaining over that graph.
>   3. **Citations** back to the source policy clause for every finding.
>
> We open-sourced exactly that today: **VeritasGraph + VeritasReason**.
>
>  • GraphRAG over your structured + unstructured corpus
>  • Forward-chaining rule engine (YAML-defined, auditable)
>  • PROV-O lineage on every triple
>  • 100% local — Ollama + Llama 3.1, no data leaves your VPC
>  • One-command demo: `pip install veritas-reason && veritasreason-policy-demo`
>
> Try the 30-second SoX Segregation-of-Duties demo:
> 👉 github.com/bibinprathap/VeritasGraph
>
> #GraphRAG #Compliance #OpenSource #LLM #KnowledgeGraph

---

## 🤖 Reddit — r/LocalLLaMA

**Title:** I built a fully-local GraphRAG that *reasons* over enterprise
policies (not just retrieves) — Llama 3.1 + Ollama + a YAML rule engine

**Body:**

Hey r/LocalLLaMA — sharing something I've been chipping away at.

Most local-RAG stacks I see can answer *"what does our procurement policy
say about Segregation of Duties?"* — they just stuff the policy PDF into a
vector DB.

The harder question every CFO actually asks is *"which Purchase Orders this
quarter are violating SoD, who approved them, and where in the policy is the
clause they broke?"*

That requires:
- a **knowledge graph** of your structured ERP data (employees, POs, vendors,
  approvals) — built with Microsoft GraphRAG,
- a **forward-chaining rule engine** (YAML rules → Datalog-style evaluation)
  that scans that graph,
- **provenance** so every finding cites the source clause.

The whole thing is open-source, runs on Ollama with Llama 3.1, and the
rule-engine-only demo installs in ~5 seconds (no torch / spaCy / FAISS):

```
pip install veritas-reason
veritasreason-policy-demo
```

→ detects 4 SoD violations on a synthetic ERP fixture, with rule IDs +
policy-PDF citations.

Repo: https://github.com/bibinprathap/VeritasGraph

Would love feedback on the rule DSL — currently YAML, considering Rego next.

---

## 🟧 Hacker News — Show HN

**Title:** Show HN: VeritasGraph – Open-source GraphRAG that reasons over
enterprise policies

**Body (first comment):**

Hi HN — author here. VeritasGraph combines Microsoft's GraphRAG with a
forward-chaining rule engine ("VeritasReason") so you can ask compliance
questions like *"which POs violate Segregation of Duties this quarter?"*
and get back violators **with the rule ID and the policy clause that was
breached** — not just a paragraph of LLM prose.

It's fully local (Ollama + Llama 3.1, your data never leaves the box) and
the rule-engine portion has zero ML deps — `pip install veritas-reason` is
a ~1 MB wheel. The full GraphRAG side is opt-in via `[full]`.

Demo runs in 30 seconds:

```
pip install veritas-reason
veritasreason-policy-demo
```

Repo: https://github.com/bibinprathap/VeritasGraph

Honest feedback on the rule DSL design, the PROV-O integration, and the
GraphRAG ↔ rule-engine boundary very welcome.

---

## ✍️ Dev.to / Medium — article hook

**Headline candidates:**
- *"Stop asking RAG what your policy says. Ask it who's breaking the policy."*
- *"GraphRAG ≠ Compliance. Here's the missing layer."*
- *"From 'retrieve relevant docs' to 'name the violators': adding a rule
  engine on top of GraphRAG"*

**Lede:** Six months ago I shipped a GraphRAG bot for a Fortune-500 finance
team. Their first real question wasn't *"summarise the SoD policy"*. It was
*"give me the list of POs from Q3 that violate it, with the approver names
and the clause numbers."* This post is what I built next.

---

## 🎨 Visual asset

`demos/policy-compliance/demo.gif` — drop into any of the above for the
hero image. Already 960×540, 2.8 MB, plays in ~6 s.


# List what's wired up
python marketing/draft_opener.py --list

# Preview every body without opening anything
python marketing/draft_opener.py --dry-run

# Real run — all 9 platforms in sequence
python marketing/draft_opener.py

# Just two platforms
python marketing/draft_opener.py reddit-localllama hackernews

# Just the HN flow (single platform, no waiting)
python marketing/draft_opener.py hackernews