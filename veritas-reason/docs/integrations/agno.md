# Agno Integration

VeritasReason's Agno integration (`veritas-reason[agno]`) wires the full VeritasReason
semantic intelligence stack into the [Agno](https://github.com/agno-agi/agno)
agentic framework via five focused components.

## Installation

```bash
# Core integration
pip install veritas-reason[agno]

# With a graph store backend
pip install veritas-reason[agno,graph-neo4j]
pip install veritas-reason[agno,graph-falkordb]

# Full stack
pip install veritas-reason[agno,graph-neo4j,vectorstore-pgvector]
```

## Components at a Glance

| Class | Agno Primitive | VeritasReason Backing |
|---|---|---|
| `AgnoContextStore` | `AgentMemory(db=…)` | `AgentContext` + `VectorStore` |
| `AgnoKnowledgeGraph` | `Agent(knowledge=…)` | `ContextGraph` + KG pipeline |
| `AgnoDecisionKit` | `Agent(tools=[…])` | `DecisionQuery`, `CausalChainAnalyzer`, `PolicyEngine` |
| `AgnoKGToolkit` | `Agent(tools=[…])` | `NERExtractor`, `RelationExtractor`, `Reasoner` |
| `AgnoSharedContext` | Team-level | Shared `ContextGraph` across agents |

---

## 1. AgnoContextStore

Replaces Agno's flat conversation storage with a hybrid **vector + context
graph** memory store.  Implements `agno.memory.db.base.MemoryDb`.

```python
from agno.agent import Agent
from agno.memory import AgentMemory
from agno.models.openai import OpenAIChat

from veritasreason.context import ContextGraph
from veritasreason.vector_store import VectorStore
from integrations.agno import AgnoContextStore

store = AgnoContextStore(
    vector_store=VectorStore(backend="faiss"),
    knowledge_graph=ContextGraph(advanced_analytics=True),
    decision_tracking=True,
    graph_expansion=True,
    session_id="user_session_42",
)

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    memory=AgentMemory(db=store),
    description="A financially aware assistant with persistent decision intelligence.",
)

agent.print_response("Recommend a portfolio allocation for a risk-averse investor.")
```

### Key behaviours

- `upsert_memory()` — stores text in `AgentContext` (vector index + graph node)
- `read_memories()` — hybrid retrieval: vector similarity + optional graph hop expansion
- `record_decision()` — records a structured decision with reasoning & outcome
- `find_precedents()` — returns veritasreasonlly similar historical decisions

---

## 2. AgnoKnowledgeGraph

Gives Agno agents a queryable `ContextGraph` instead of a flat document store.
Ingested documents pass through the full VeritasReason extraction pipeline.

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat

from veritasreason.kg import GraphBuilder
from veritasreason.semantic_extract import NERExtractor, RelationExtractor
from integrations.agno import AgnoKnowledgeGraph

kg = AgnoKnowledgeGraph(
    graph_builder=GraphBuilder(),
    ner_extractor=NERExtractor(),
    relation_extractor=RelationExtractor(),
)

# Ingest local files
kg.load("regulatory_docs/", recursive=True)

# Ingest raw text
kg.load(texts=["Basel IV capital requirements apply from January 2026."])

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    knowledge=kg,
    search_knowledge=True,
)
```

### Ingestion pipeline

```
parse → NER → relation extract → graph build → vector index
```

### Search: multi-hop GraphRAG

```
vector retrieval → entity lookup → graph hop expansion → context injection
```

### Get entity subgraph

```python
ctx = kg.get_graph_context("Basel IV")
# Returns a text summary of the entity's immediate neighbourhood in the graph
```

---

## 3. AgnoDecisionKit

Exposes VeritasReason's decision intelligence as native Agno tools.

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat

from veritasreason.context import AgentContext
from integrations.agno import AgnoDecisionKit

ctx = AgentContext(decision_tracking=True)

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[AgnoDecisionKit(context=ctx)],
    show_tool_calls=True,
)

agent.print_response("Should we approve this mortgage application?")
```

### Tools

| Tool | Description | Key Parameters |
|---|---|---|
| `record_decision` | Record decision with reasoning and outcome | `category`, `scenario`, `reasoning`, `outcome`, `confidence`, `entities` |
| `find_precedents` | Search for similar past decisions | `scenario`, `category`, `limit` |
| `trace_causal_chain` | Trace causal chain of a decision | `decision_id`, `depth` |
| `analyze_impact` | Assess downstream influence of a decision | `decision_id` |
| `check_policy` | Validate decision against policy rules | `decision_data`, `policy_rules` |
| `get_decision_summary` | Summarise decision history by category | `category`, `since`, `limit` |

### Example agent turn

```
User: Should we approve this mortgage application?

Agent [tool: find_precedents]         → 12 similar mortgage approvals found
Agent [tool: check_policy]            → complies with lending policy v2.3
Agent [tool: record_decision]         → recorded: loan_approval / approved / confidence=0.94
Agent: Based on 12 historical precedents and full policy compliance, I recommend
       approval. Credit score 740, 22% down payment, DTI 31% — all within thresholds.
```

---

## 4. AgnoKGToolkit

Lets agents actively build and query the context graph during reasoning.

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat

from integrations.agno import AgnoKGToolkit

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[AgnoKGToolkit()],
    show_tool_calls=True,
)

agent.print_response(
    "Extract entities and relationships from this article and store them in the knowledge graph."
)
```

### Tools

| Tool | Description |
|---|---|
| `extract_entities` | Extract named entities from text |
| `extract_relations` | Extract relationships between entities |
| `add_to_graph` | Add entities / relations to the context graph |
| `query_graph` | Query the graph (natural-language or Cypher) |
| `find_related` | Find concepts related to a given entity |
| `infer_facts` | Apply rules to infer new facts from the graph |
| `export_subgraph` | Export a subgraph as RDF / JSON-LD |

---

## 5. AgnoSharedContext

A single `ContextGraph` shared across an Agno `Team`.  Each agent gets a
**role-scoped view** via `bind_agent()`.

```python
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIChat

from veritasreason.context import ContextGraph
from veritasreason.vector_store import VectorStore
from integrations.agno import AgnoSharedContext, AgnoDecisionKit, AgnoKGToolkit

shared = AgnoSharedContext(
    vector_store=VectorStore(backend="faiss"),
    knowledge_graph=ContextGraph(advanced_analytics=True),
    decision_tracking=True,
)

research_agent = Agent(
    name="Researcher",
    model=OpenAIChat(id="gpt-4o"),
    memory=shared.bind_agent("researcher"),
    tools=[AgnoKGToolkit(context=shared)],
)

decision_agent = Agent(
    name="Analyst",
    model=OpenAIChat(id="gpt-4o"),
    memory=shared.bind_agent("analyst"),
    tools=[AgnoDecisionKit(context=shared)],
)

team = Team(
    name="Research & Decision Team",
    agents=[research_agent, decision_agent],
    mode="coordinate",
)

team.print_response(
    "Analyse the competitive landscape and recommend our product strategy."
)
```

### Shared memory pool

Memories written by one agent are immediately visible to all other agents in the
team.  Each agent's writes are tagged with their role so they can be filtered
independently.

### Shared decisions

```python
# Record a team-level decision
decision_id = shared.record_decision(
    category="strategy",
    scenario="Expand to EU market",
    reasoning="Strong demand signals from Q1 survey",
    outcome="approved",
    confidence=0.87,
    agent_role="cfo",
)

# Query precedents across all agents' history
precedents = shared.find_precedents("market expansion")

# Get cross-agent analytics
insights = shared.get_shared_insights()
```

---

## Use Cases

### Regulated Industry Agents (Finance, Healthcare, Legal)

Agents that log every decision with full provenance, reasoning chain, and policy
compliance check for audit trails.

```python
kit = AgnoDecisionKit(context=ctx)
# Every agent turn: find_precedents → check_policy → record_decision
```

### Long-Running Research Agents

Agents that accumulate a persistent `ContextGraph` over days or weeks, enabling
multi-hop reasoning over a growing knowledge base.

```python
kg = AgnoKnowledgeGraph(graph_builder=GraphBuilder(), ...)
# Agents load new documents continuously; search benefits from the growing graph
```

### Enterprise Multi-Agent Coordination

Teams using `AgnoSharedContext` to prevent contradictory decisions and share
structured knowledge across specialist agents.

### GraphRAG Customer Support

Support agents that retrieve answers via graph traversal, providing more
contextually grounded responses than flat vector search.

### Explainable AI Pipelines

Every agent step, entity reference, and causal chain is traceable back to a
source document or prior decision.

---

## API Reference

```python
from integrations.agno import (
    AgnoContextStore,       # MemoryDb implementation
    AgnoKnowledgeGraph,     # AgentKnowledge implementation
    AgnoDecisionKit,        # Decision intelligence Toolkit
    AgnoKGToolkit,          # Knowledge graph Toolkit
    AgnoSharedContext,      # Team-level shared context
    AGNO_AVAILABLE,         # bool — True if agno is installed
)
```

All five classes are usable **without** `agno` installed — they carry the full
VeritasReason API and degrade gracefully when passed to Agno constructors.
