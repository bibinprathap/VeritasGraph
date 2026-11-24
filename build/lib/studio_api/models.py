"""Pydantic models for the Agent Studio backend.

The studio is organised into eight sections. Six of them (agents, tools,
knowledge, guardrails, memory, data) are plain resource collections that share a
common record shape, so they reuse :class:`ResourceRecord`. Evaluation and
fine-tune are simulations with their own progression state and therefore have
dedicated models.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
class Section(str, Enum):
    """The collection-style studio sections."""

    AGENTS = "agents"
    TOOLS = "tools"
    KNOWLEDGE = "knowledge"
    GUARDRAILS = "guardrails"
    MEMORY = "memory"
    DATA = "data"


# Default status badge applied to a freshly created record in each section.
DEFAULT_STATUS: Dict[str, str] = {
    Section.AGENTS.value: "draft",
    Section.TOOLS.value: "connected",
    Section.KNOWLEDGE.value: "indexing",
    Section.GUARDRAILS.value: "monitoring",
    Section.MEMORY.value: "active",
    Section.DATA.value: "syncing",
}

# The status values that count as "healthy"/active for KPI aggregation.
ACTIVE_STATUS: Dict[str, set] = {
    Section.AGENTS.value: {"active"},
    Section.TOOLS.value: {"connected"},
    Section.KNOWLEDGE.value: {"indexed"},
    Section.GUARDRAILS.value: {"enforcing", "monitoring"},
    Section.MEMORY.value: {"active"},
    Section.DATA.value: {"ready"},
}


# --------------------------------------------------------------------------- #
# Resource records (collection sections)
# --------------------------------------------------------------------------- #
class ResourceRecord(BaseModel):
    """A single item inside a collection section."""

    id: str
    section: str
    name: str
    kind: Optional[str] = Field(
        default=None, description="Sub-type, e.g. 'retrieval' tool or 'pii' guardrail."
    )
    status: str
    description: str = ""
    config: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class ResourceCreateRequest(BaseModel):
    """Payload for creating a resource in a collection section."""

    name: str = Field(..., min_length=1, description="Display name of the resource.")
    kind: Optional[str] = Field(default=None, description="Optional sub-type.")
    status: Optional[str] = Field(
        default=None, description="Initial status badge; section default if omitted."
    )
    description: str = ""
    config: Dict[str, Any] = Field(default_factory=dict)


class ResourceUpdateRequest(BaseModel):
    """Partial update for a resource. Only provided fields are changed."""

    name: Optional[str] = None
    kind: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
class EvaluationStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"


class EvaluationRun(BaseModel):
    """A single evaluation run with a progress trend for visualisation."""

    id: str
    name: str
    suite: str
    target_agent: Optional[str] = None
    total_cases: int
    status: str = EvaluationStatus.QUEUED.value
    progress: float = 0.0
    pass_rate: float = 0.0
    passed_cases: int = 0
    failed_cases: int = 0
    threshold: float = 0.8
    trend: List[Dict[str, float]] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class EvaluationRunRequest(BaseModel):
    name: Optional[str] = None
    suite: str = "regression"
    target_agent: Optional[str] = None
    total_cases: int = Field(default=40, ge=1, le=10_000)
    threshold: float = Field(default=0.8, ge=0.0, le=1.0)


# --------------------------------------------------------------------------- #
# Fine-tune
# --------------------------------------------------------------------------- #
class FineTuneStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"


# Ordered progression used by the queue simulation.
FINE_TUNE_PROGRESSION: List[str] = [
    FineTuneStatus.QUEUED.value,
    FineTuneStatus.RUNNING.value,
    FineTuneStatus.READY.value,
]


class FineTuneJob(BaseModel):
    """A fine-tune job that progresses queued -> running -> ready."""

    id: str
    name: str
    base_model: str
    dataset: str
    epochs: int = 3
    status: str = FineTuneStatus.QUEUED.value
    progress: float = 0.0
    loss: Optional[float] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class FineTuneJobRequest(BaseModel):
    name: Optional[str] = None
    base_model: str = "gpt-5.3-codex"
    dataset: str = "studio-default"
    epochs: int = Field(default=3, ge=1, le=50)


# --------------------------------------------------------------------------- #
# Workspace
# --------------------------------------------------------------------------- #
class WorkspaceDraft(BaseModel):
    """The persisted draft of the whole workspace (server-side 'local storage')."""

    name: str = "Untitled workspace"
    notes: str = ""
    selected_section: str = Section.AGENTS.value
    data: Dict[str, Any] = Field(default_factory=dict)


class DeployRequest(BaseModel):
    workspace: str = "default"
    environment: str = Field(default="staging")
    notes: str = ""


# --------------------------------------------------------------------------- #
# Playground (agent test runs)
# --------------------------------------------------------------------------- #
class ChatMessage(BaseModel):
    """A single conversation turn passed to the agent under test."""

    role: str = Field(default="user")
    content: str


class PlaygroundChatRequest(BaseModel):
    """Run a stored agent against its local model with a user message."""

    agent_id: str
    message: str = Field(min_length=1)
    history: List[ChatMessage] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# GraphRAG (VeritasGraph knowledge graph)
# --------------------------------------------------------------------------- #
class GraphIngestRequest(BaseModel):
    """Ingest a document into the knowledge graph."""

    title: str = Field(default="Untitled document", min_length=1)
    text: str = Field(min_length=1)
    model: str = Field(min_length=1)


class GraphQueryRequest(BaseModel):
    """Ask a question answered by graph-grounded multi-hop reasoning."""

    question: str = Field(min_length=1)
    model: str = Field(min_length=1)
    max_depth: int = Field(default=2, ge=1, le=4)
    max_nodes: int = Field(default=25, ge=1, le=200)
    mode: Literal["exploratory", "governed"] = Field(
        default="exploratory",
        description="governed: require certified glossary terms and withhold ungrounded answers.",
    )


class AnswerableRequest(BaseModel):
    """Check whether the graph can answer a question, without calling an LLM."""

    question: str = Field(min_length=1, max_length=4000)
    mode: Literal["exploratory", "governed"] = "exploratory"


class FeedbackRequest(BaseModel):
    rating: Literal[-1, 0, 1]
    comment: str = Field(default="", max_length=2000)


class SnapshotRequest(BaseModel):
    label: str = Field(default="", max_length=200)


class MergeEntitiesRequest(BaseModel):
    keep_id: str = Field(min_length=1)
    drop_id: str = Field(min_length=1)


# --------------------------------------------------------------------------- #
# Ontology
# --------------------------------------------------------------------------- #
class EntityTypeRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    parent: Optional[str] = Field(default=None, max_length=120)
    synonyms: List[str] = Field(default_factory=list, max_length=100)


class PredicateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    domain_type: Optional[str] = Field(default=None, max_length=120)
    range_type: Optional[str] = Field(default=None, max_length=120)
    inverse: Optional[str] = Field(default=None, max_length=120)
    synonyms: List[str] = Field(default_factory=list, max_length=100)


class TermRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    definition: str = Field(default="", max_length=4000)
    synonyms: List[str] = Field(default_factory=list, max_length=100)
    entity_ids: Optional[List[str]] = Field(default=None, max_length=1000)


class TermLinkRequest(BaseModel):
    entity_ids: List[str] = Field(min_length=1, max_length=1000)


class GraphImportRequest(BaseModel):
    """Import a pre-built knowledge graph produced by another tool.

    ``graph`` is the raw uploaded JSON (Graphify ``graph.json``,
    Understand-Anything ``KnowledgeGraph``, AI Atlas taxonomy, or any node/edge
    JSON). Imported nodes/edges are tagged with ``source_type`` provenance so
    curated content stays distinguishable from extracted or inferred additions.
    """

    graph: Dict[str, Any] = Field(..., description="Raw uploaded graph JSON.")
    format: str = Field(
        default="auto",
        description="auto | graphify | understand_anything | ai_atlas | generic",
    )
    source_type: str = Field(
        default="curated", description="Provenance: curated | extracted | inferred."
    )
    merge_strategy: str = Field(
        default="preserve_curated",
        description="preserve_curated | overwrite | skip_existing.",
    )
    title: Optional[str] = Field(
        default=None, description="Optional display title for the imported graph."
    )
    origin_version: Optional[str] = Field(
        default=None, description="Optional source version/commit to preserve."
    )


# --------------------------------------------------------------------------- #
# Structured data
# --------------------------------------------------------------------------- #
class ConnectionOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schemas: List[str] = Field(default_factory=list, max_length=50)
    exclude_schemas: List[str] = Field(default_factory=list, max_length=50)


class ConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.-]+$")
    dsn: str = Field(min_length=8, max_length=2000)
    options: ConnectionOptions = Field(default_factory=ConnectionOptions)


class FieldRoleUpdate(BaseModel):
    role: Literal["id", "measure", "dimension", "time", "text", "other"]


class StructuredTermRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    definition: str = Field(default="", max_length=2000)
    synonyms: List[str] = Field(default_factory=list, max_length=20)
    dataset_ids: List[str] = Field(default_factory=list, max_length=50)


class RelationshipCreate(BaseModel):
    from_field_id: str = Field(max_length=32)
    to_field_id: str = Field(max_length=32)


class MeasureRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    expression: str = Field(min_length=1, max_length=2000)
    dataset_id: str = Field(max_length=32)
    description: str = Field(default="", max_length=2000)
    grain: Optional[str] = Field(default=None, max_length=500)


class StructuredSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    kinds: List[Literal["term", "measure", "dataset", "field"]] = Field(default_factory=list)
    k: int = Field(default=10, ge=1, le=50)


class StructuredAskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    mode: Literal["exploratory", "governed"] = "exploratory"
    connection_id: Optional[str] = Field(default=None, max_length=32)

