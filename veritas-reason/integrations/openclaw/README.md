# VeritasReason × OpenClaw Integration

Connect [OpenClaw](https://openclaw.ai) — the open-source personal AI agent — to VeritasReason's full knowledge-graph and decision-intelligence stack.

Two integration paths are available:

| Path | When to use |
|---|---|
| **MCP (recommended)** | OpenClaw Gateway is running; zero extra code needed |
| **REST / native tool** | Embedding VeritasReason directly in a SOUL.md agent config |

---

## Path 1 — MCP Server (recommended)

### 1. Start the VeritasReason MCP server

```bash
python -m veritasreason.mcp_server
```

### 2. Add to `mcporter.json`

```json
{
  "mcpServers": {
    "veritasreason": {
      "command": "python",
      "args": ["-m", "veritasreason.mcp_server"],
      "transport": "stdio"
    }
  }
}
```

### 3. Restart the OpenClaw Gateway

```bash
openclaw gateway restart
```

All **12 VeritasReason tools** are now available to any OpenClaw agent:

| Tool | What it does |
|---|---|
| `extract_entities` | Named entity recognition from text |
| `extract_relations` | Relation / triplet extraction from text |
| `record_decision` | Record a decision with causal links |
| `query_decisions` | Search recorded decisions |
| `find_precedents` | Find past decisions similar to a query |
| `get_causal_chain` | Trace cause-effect chains from a node |
| `add_entity` | Add a node to the knowledge graph |
| `add_relationship` | Add an edge between two nodes |
| `run_reasoning` | Forward-chain rules over facts |
| `get_graph_analytics` | Centrality, communities, topology stats |
| `export_graph` | Export graph (JSON, RDF, GraphML, …) |
| `get_graph_summary` | High-level graph overview |

**3 resources** are also exposed: `veritasreason://graph/summary`, `veritasreason://decisions/list`, `veritasreason://schema/info`.

---

## Path 2 — Native Tool (REST)

Use `OpenClawKGTool` when you prefer a direct Python integration without the MCP gateway.

### Install

```bash
pip install veritas-reason[openclaw]   # pulls in 'requests'
```

### Quick start

```python
from integrations.openclaw import OpenClawKGTool

tool = OpenClawKGTool(base_url="http://localhost:8000")

# Extract knowledge from text
entities = tool.extract_entities("OpenClaw is an open-source AI agent built in Python.")
relations = tool.extract_relations("Alice manages the OpenClaw project at Hawksight.")

# Record and query decisions
tool.record_decision("Deploy model v2 to production", context="latency improved by 40%")
precedents = tool.find_precedents("roll back production deployment")

# Graph analytics
summary = tool.get_graph_summary()
analytics = tool.get_graph_analytics()

# Export
ttl = tool.export_graph(fmt="ttl")
```

### Generate `mcporter.json` programmatically

```python
from integrations.openclaw import OpenClawMCPConfig

cfg = OpenClawMCPConfig()
print(cfg.to_json())   # → paste into mcporter.json
```

---

## SOUL.md agent snippet

Add VeritasReason to any OpenClaw agent by referencing the tool in your `SOUL.md`:

```markdown
## Tools

- name: veritasreason_kg
  description: >
    VeritasReason knowledge-graph tool. Supports entity extraction, decision
    recording, graph querying, causal chain analysis, reasoning, and
    multi-format export.
  endpoint: http://localhost:8000
  auth: none

## Instructions

You have access to `veritasreason_kg`. Use it to:
- Extract entities and relations from any text the user provides.
- Record important decisions and retrieve precedents before recommending actions.
- Run graph analytics and export results when the user asks for a summary.
```

---

## Requirements

- Python 3.8+
- `pip install veritas-reason` (core)
- `pip install veritas-reason[openclaw]` (adds `requests` for the REST path)
- OpenClaw ≥ latest — [openclaw.ai](https://openclaw.ai)
