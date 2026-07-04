"""In-memory studio store with JSON persistence.

This is the studio equivalent of the ``data_adapter`` singleton used by the
surrounding services: a single object that owns all state and exposes synchronous
methods. Controllers call these methods through ``asyncio.to_thread`` so the event
loop is never blocked.

State is held in memory and snapshotted to a JSON file so a saved draft survives
a restart. The evaluation and fine-tune simulations advance deterministically
when :meth:`advance` is called and also auto-advance based on wall-clock time so
the UI shows progress without polling an advance endpoint.
"""

from __future__ import annotations

import json
import math
import os
import random
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from studio_api.models import (
    ACTIVE_STATUS,
    DEFAULT_STATUS,
    EvaluationRun,
    EvaluationRunRequest,
    EvaluationStatus,
    FINE_TUNE_PROGRESSION,
    FineTuneJob,
    FineTuneJobRequest,
    FineTuneStatus,
    ResourceCreateRequest,
    ResourceRecord,
    ResourceUpdateRequest,
    Section,
    WorkspaceDraft,
)

_DATA_DIR = Path(os.getenv("STUDIO_DATA_DIR", str(Path(__file__).resolve().parent / "data")))
_SNAPSHOT = _DATA_DIR / "workspace.json"

# Seconds of wall-clock time per simulated progression step.
_EVAL_STEP_SECONDS = float(os.getenv("STUDIO_EVAL_STEP_SECONDS", "2"))
_FT_STEP_SECONDS = float(os.getenv("STUDIO_FT_STEP_SECONDS", "3"))


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


class StudioStore:
    """Single owner of all studio state."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._collections: Dict[str, Dict[str, ResourceRecord]] = {
            s.value: {} for s in Section
        }
        self._evaluations: Dict[str, EvaluationRun] = {}
        self._finetunes: Dict[str, FineTuneJob] = {}
        self._guardrail_blocks: int = 0
        self._draft = WorkspaceDraft()
        self._deploy_history: List[Dict[str, Any]] = []
        # Per-agent conversation memory and interaction data logs, used by the
        # orchestration pipeline to wire Memory and Data into agent runs.
        self._agent_memory: Dict[str, List[Dict[str, Any]]] = {}
        self._agent_data: Dict[str, List[Dict[str, Any]]] = {}
        self._loaded = self._load()
        if not self._loaded:
            self._seed()
        # Keep the default catalog in sync for existing persisted snapshots.
        self._ensure_default_catalog()

    # ------------------------------------------------------------------ #
    # Collection CRUD
    # ------------------------------------------------------------------ #
    def list_resources(self, section: str) -> List[ResourceRecord]:
        self._auto_advance()
        with self._lock:
            items = list(self._collections[section].values())
        return sorted(items, key=lambda r: r.created_at)

    def get_resource(self, section: str, resource_id: str) -> Optional[ResourceRecord]:
        with self._lock:
            return self._collections[section].get(resource_id)

    def create_resource(
        self, section: str, payload: ResourceCreateRequest
    ) -> ResourceRecord:
        record = ResourceRecord(
            id=_new_id(section[:3]),
            section=section,
            name=payload.name,
            kind=payload.kind,
            status=payload.status or DEFAULT_STATUS[section],
            description=payload.description,
            config=payload.config,
        )
        with self._lock:
            self._collections[section][record.id] = record
        self._persist()
        return record

    def update_resource(
        self, section: str, resource_id: str, payload: ResourceUpdateRequest
    ) -> Optional[ResourceRecord]:
        with self._lock:
            record = self._collections[section].get(resource_id)
            if record is None:
                return None
            updates = payload.model_dump(exclude_none=True)
            for key, value in updates.items():
                setattr(record, key, value)
            record.updated_at = time.time()
        self._persist()
        return record

    def delete_resource(self, section: str, resource_id: str) -> bool:
        with self._lock:
            existed = self._collections[section].pop(resource_id, None) is not None
        if existed:
            self._persist()
        return existed

    # ------------------------------------------------------------------ #
    # Agent conversation memory (wires the Memory section into agent runs)
    # ------------------------------------------------------------------ #
    def append_memory(self, agent_id: str, role: str, content: str) -> None:
        with self._lock:
            turns = self._agent_memory.setdefault(agent_id, [])
            turns.append({"role": role, "content": content, "at": time.time()})
            # Keep memory bounded so the snapshot stays small.
            self._agent_memory[agent_id] = turns[-50:]
        self._persist()

    def get_memory(self, agent_id: str, limit: int = 6) -> List[Dict[str, Any]]:
        with self._lock:
            turns = list(self._agent_memory.get(agent_id, []))
        return turns[-limit:] if limit > 0 else turns

    def clear_memory(self, agent_id: str) -> None:
        with self._lock:
            self._agent_memory.pop(agent_id, None)
        self._persist()

    # ------------------------------------------------------------------ #
    # Agent interaction data log (wires the Data section into agent runs)
    # ------------------------------------------------------------------ #
    def log_interaction(self, agent_id: str, record: Dict[str, Any]) -> None:
        entry = {"id": _new_id("intxn"), "at": time.time(), **record}
        with self._lock:
            log = self._agent_data.setdefault(agent_id, [])
            log.append(entry)
            self._agent_data[agent_id] = log[-200:]
        self._persist()

    def get_interactions(self, agent_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            log = list(self._agent_data.get(agent_id, []))
        return log[-limit:] if limit > 0 else log

    # ------------------------------------------------------------------ #
    # Guardrails — block counter
    # ------------------------------------------------------------------ #
    def record_guardrail_block(self, count: int = 1) -> int:
        with self._lock:
            self._guardrail_blocks += max(count, 0)
            total = self._guardrail_blocks
        self._persist()
        return total

    # ------------------------------------------------------------------ #
    # Evaluation simulation
    # ------------------------------------------------------------------ #
    def list_evaluations(self) -> List[EvaluationRun]:
        self._auto_advance()
        with self._lock:
            return sorted(self._evaluations.values(), key=lambda r: r.created_at)

    def get_evaluation(self, run_id: str) -> Optional[EvaluationRun]:
        self._auto_advance()
        with self._lock:
            return self._evaluations.get(run_id)

    def start_evaluation(self, payload: EvaluationRunRequest) -> EvaluationRun:
        run = EvaluationRun(
            id=_new_id("eval"),
            name=payload.name or f"{payload.suite} run",
            suite=payload.suite,
            target_agent=payload.target_agent,
            total_cases=payload.total_cases,
            threshold=payload.threshold,
            status=EvaluationStatus.RUNNING.value,
        )
        with self._lock:
            self._evaluations[run.id] = run
        self._persist()
        return run

    def _advance_evaluation(self, run: EvaluationRun) -> None:
        if run.status not in (
            EvaluationStatus.QUEUED.value,
            EvaluationStatus.RUNNING.value,
        ):
            return
        run.status = EvaluationStatus.RUNNING.value
        step = max(1, math.ceil(run.total_cases / 5))
        done = int(round(run.progress * run.total_cases)) + step
        done = min(done, run.total_cases)
        # Stable per-run quality target so the trend converges smoothly.
        rng = random.Random(run.id)
        target = 0.78 + rng.random() * 0.2
        passed = int(round(done * target))
        run.passed_cases = passed
        run.failed_cases = done - passed
        run.progress = done / run.total_cases
        run.pass_rate = passed / done if done else 0.0
        run.trend.append({"completed": done, "pass_rate": round(run.pass_rate, 4)})
        run.updated_at = time.time()
        if done >= run.total_cases:
            run.status = (
                EvaluationStatus.PASSED.value
                if run.pass_rate >= run.threshold
                else EvaluationStatus.FAILED.value
            )

    # ------------------------------------------------------------------ #
    # Fine-tune simulation
    # ------------------------------------------------------------------ #
    def list_finetunes(self) -> List[FineTuneJob]:
        self._auto_advance()
        with self._lock:
            return sorted(self._finetunes.values(), key=lambda j: j.created_at)

    def get_finetune(self, job_id: str) -> Optional[FineTuneJob]:
        self._auto_advance()
        with self._lock:
            return self._finetunes.get(job_id)

    def queue_finetune(self, payload: FineTuneJobRequest) -> FineTuneJob:
        job = FineTuneJob(
            id=_new_id("ft"),
            name=payload.name or f"{payload.base_model} tune",
            base_model=payload.base_model,
            dataset=payload.dataset,
            epochs=payload.epochs,
        )
        with self._lock:
            self._finetunes[job.id] = job
        self._persist()
        return job

    def _advance_finetune(self, job: FineTuneJob) -> None:
        if job.status not in FINE_TUNE_PROGRESSION[:-1]:
            return
        idx = FINE_TUNE_PROGRESSION.index(job.status)
        job.status = FINE_TUNE_PROGRESSION[idx + 1]
        rng = random.Random(job.id)
        if job.status == FineTuneStatus.RUNNING.value:
            job.progress = 0.5
            job.loss = round(0.9 - rng.random() * 0.2, 4)
        elif job.status == FineTuneStatus.READY.value:
            job.progress = 1.0
            job.loss = round((job.loss or 0.7) * 0.45, 4)
        job.updated_at = time.time()

    # ------------------------------------------------------------------ #
    # Manual + automatic progression
    # ------------------------------------------------------------------ #
    def advance(self) -> Dict[str, int]:
        """Advance every in-flight evaluation and fine-tune by one step."""
        with self._lock:
            evals = [
                r
                for r in self._evaluations.values()
                if r.status
                in (EvaluationStatus.QUEUED.value, EvaluationStatus.RUNNING.value)
            ]
            for run in evals:
                self._advance_evaluation(run)
            jobs = [
                j
                for j in self._finetunes.values()
                if j.status in FINE_TUNE_PROGRESSION[:-1]
            ]
            for job in jobs:
                self._advance_finetune(job)
        self._persist()
        return {"evaluations": len(evals), "finetunes": len(jobs)}

    def _auto_advance(self) -> None:
        """Advance simulations based on elapsed wall-clock time."""
        now = time.time()
        changed = False
        with self._lock:
            for run in self._evaluations.values():
                if run.status in (
                    EvaluationStatus.QUEUED.value,
                    EvaluationStatus.RUNNING.value,
                ):
                    steps = int((now - run.updated_at) // _EVAL_STEP_SECONDS)
                    for _ in range(steps):
                        self._advance_evaluation(run)
                        changed = True
                        if run.status not in (
                            EvaluationStatus.QUEUED.value,
                            EvaluationStatus.RUNNING.value,
                        ):
                            break
            for job in self._finetunes.values():
                if job.status in FINE_TUNE_PROGRESSION[:-1]:
                    steps = int((now - job.updated_at) // _FT_STEP_SECONDS)
                    for _ in range(steps):
                        self._advance_finetune(job)
                        changed = True
                        if job.status not in FINE_TUNE_PROGRESSION[:-1]:
                            break
        if changed:
            self._persist()

    # ------------------------------------------------------------------ #
    # KPIs
    # ------------------------------------------------------------------ #
    def kpis(self) -> Dict[str, Any]:
        self._auto_advance()
        with self._lock:
            active_agents = sum(
                1
                for r in self._collections[Section.AGENTS.value].values()
                if r.status in ACTIVE_STATUS[Section.AGENTS.value]
            )
            connected_tools = sum(
                1
                for r in self._collections[Section.TOOLS.value].values()
                if r.status in ACTIVE_STATUS[Section.TOOLS.value]
            )
            finished = [
                r
                for r in self._evaluations.values()
                if r.status
                in (EvaluationStatus.PASSED.value, EvaluationStatus.FAILED.value)
            ]
            eval_pass_rate = (
                sum(r.pass_rate for r in finished) / len(finished) if finished else 0.0
            )
            guardrail_blocks = self._guardrail_blocks
        return {
            "active_agents": active_agents,
            "tools_connected": connected_tools,
            "eval_pass_rate": round(eval_pass_rate, 4),
            "guardrail_blocks": guardrail_blocks,
        }

    # ------------------------------------------------------------------ #
    # Workspace draft + deploy
    # ------------------------------------------------------------------ #
    def get_draft(self) -> WorkspaceDraft:
        with self._lock:
            return self._draft.model_copy(deep=True)

    def save_draft(self, draft: WorkspaceDraft) -> WorkspaceDraft:
        with self._lock:
            self._draft = draft
        self._persist()
        return draft

    def deploy(self, workspace: str, environment: str, notes: str) -> Dict[str, Any]:
        self._auto_advance()
        kpis = self.kpis()
        record = {
            "id": _new_id("deploy"),
            "workspace": workspace,
            "environment": environment,
            "notes": notes,
            "status": "succeeded",
            "deployed_at": time.time(),
            "snapshot": kpis,
        }
        with self._lock:
            self._deploy_history.insert(0, record)
            self._deploy_history = self._deploy_history[:50]
        self._persist()
        return record

    def deploy_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._deploy_history)

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def _persist(self) -> None:
        snapshot = {
            "collections": {
                section: [r.model_dump(mode="json") for r in items.values()]
                for section, items in self._collections.items()
            },
            "evaluations": [r.model_dump(mode="json") for r in self._evaluations.values()],
            "finetunes": [j.model_dump(mode="json") for j in self._finetunes.values()],
            "guardrail_blocks": self._guardrail_blocks,
            "draft": self._draft.model_dump(mode="json"),
            "deploy_history": self._deploy_history,
            "agent_memory": self._agent_memory,
            "agent_data": self._agent_data,
        }
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            tmp = _SNAPSHOT.with_suffix(".tmp")
            tmp.write_text(json.dumps(snapshot, indent=2))
            tmp.replace(_SNAPSHOT)
        except OSError:
            # Persistence is best-effort; the in-memory state remains authoritative.
            pass

    def _load(self) -> bool:
        if not _SNAPSHOT.is_file():
            return False
        try:
            snapshot = json.loads(_SNAPSHOT.read_text())
        except (OSError, json.JSONDecodeError):
            return False
        with self._lock:
            for section, items in snapshot.get("collections", {}).items():
                if section in self._collections:
                    self._collections[section] = {
                        item["id"]: ResourceRecord(**item) for item in items
                    }
            self._evaluations = {
                item["id"]: EvaluationRun(**item)
                for item in snapshot.get("evaluations", [])
            }
            self._finetunes = {
                item["id"]: FineTuneJob(**item)
                for item in snapshot.get("finetunes", [])
            }
            self._guardrail_blocks = snapshot.get("guardrail_blocks", 0)
            if snapshot.get("draft"):
                self._draft = WorkspaceDraft(**snapshot["draft"])
            self._deploy_history = snapshot.get("deploy_history", [])
            self._agent_memory = snapshot.get("agent_memory", {})
            self._agent_data = snapshot.get("agent_data", {})
        return True

    # ------------------------------------------------------------------ #
    # Seed data (first run only)
    # ------------------------------------------------------------------ #
    def _default_catalog(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            Section.AGENTS.value: [
                {
                    "name": "Research Orchestrator",
                    "kind": "orchestrator",
                    "status": "active",
                    "description": "Routes research questions across graph, web, and document tools.",
                    "config": {
                        "tags": "research, orchestration",
                        "prompt": "Plan, retrieve evidence, then synthesize with citations.",
                        "use_graph": True,
                        "use_tools": True,
                        "use_memory": True,
                        "use_guardrails": True,
                        "use_data": True,
                        "context_budget": 700,
                    },
                },
                {
                    "name": "Compliance Reviewer",
                    "kind": "reviewer",
                    "status": "active",
                    "description": "Evaluates policy and risk with guardrails enabled.",
                    "config": {
                        "tags": "compliance, risk",
                        "prompt": "Use policy sources first and explain any violations clearly.",
                        "use_graph": True,
                        "use_tools": True,
                        "use_memory": True,
                        "use_guardrails": True,
                        "use_data": True,
                        "context_budget": 650,
                    },
                },
                {
                    "name": "Draft Assistant",
                    "kind": "assistant",
                    "status": "draft",
                    "description": "General drafting assistant for iterative editing workflows.",
                    "config": {
                        "tags": "drafting",
                        "prompt": "Draft concise, structured responses and ask clarifying questions.",
                        "use_graph": False,
                        "use_tools": True,
                        "use_memory": True,
                        "use_guardrails": True,
                        "use_data": False,
                        "context_budget": 500,
                    },
                },
                {
                    "name": "General Tools Explorer",
                    "kind": "explorer",
                    "status": "active",
                    "description": "Sample explorer agent wired to the full general-purpose toolset.",
                    "config": {
                        "tags": "sample, explorer, tools",
                        "prompt": "Select the best tool for each task and explain tool choice briefly.",
                        "use_graph": True,
                        "use_tools": True,
                        "use_memory": True,
                        "use_guardrails": True,
                        "use_data": True,
                        "context_budget": 800,
                        "tool_profile": [
                            "Graph Retriever",
                            "Web Search",
                            "Email Assistant",
                            "Docs Workspace",
                            "Sheets Analyst",
                            "Task Planner",
                            "GitHub Repo",
                        ],
                    },
                },
                {
                    "name": "Data & BI Explorer",
                    "kind": "explorer",
                    "status": "active",
                    "description": "Sample explorer agent focused on data, dashboarding, and reporting.",
                    "config": {
                        "tags": "sample, explorer, data",
                        "prompt": "Use tabular tools first, then produce concise KPI summaries.",
                        "use_graph": True,
                        "use_tools": True,
                        "use_memory": True,
                        "use_guardrails": True,
                        "use_data": True,
                        "context_budget": 750,
                        "tool_profile": [
                            "Sheets Analyst",
                            "Power BI Connector",
                            "Tableau Connector",
                            "Cloud Drive",
                        ],
                    },
                },
            ],
            Section.TOOLS.value: [
                {
                    "name": "Graph Retriever",
                    "kind": "retrieval",
                    "status": "connected",
                    "description": "Graph-aware retrieval over indexed knowledge.",
                    "config": {"endpoint": "http://127.0.0.1:8200/graphrag/query"},
                },
                {
                    "name": "Web Search",
                    "kind": "search",
                    "status": "connected",
                    "description": "External web lookup for fresh context.",
                    "config": {"endpoint": "https://api.example.local/web-search"},
                },
                {
                    "name": "Code Runner",
                    "kind": "execution",
                    "status": "disabled",
                    "description": "Sandboxed code execution for deterministic snippets.",
                    "config": {"endpoint": "https://api.example.local/code-runner"},
                },
                {
                    "name": "Slack Connector",
                    "kind": "communication",
                    "status": "connected",
                    "description": "Post updates and fetch channel context.",
                    "config": {"endpoint": "https://api.example.local/slack"},
                },
                {
                    "name": "Teams Connector",
                    "kind": "communication",
                    "status": "connected",
                    "description": "Send and read Microsoft Teams messages.",
                    "config": {"endpoint": "https://api.example.local/teams"},
                },
                {
                    "name": "Email Assistant",
                    "kind": "email",
                    "status": "connected",
                    "description": "Compose, classify, and route email actions.",
                    "config": {"endpoint": "https://api.example.local/email"},
                },
                {
                    "name": "Docs Workspace",
                    "kind": "document",
                    "status": "connected",
                    "description": "Create and edit long-form docs.",
                    "config": {"endpoint": "https://api.example.local/docs"},
                },
                {
                    "name": "Sheets Analyst",
                    "kind": "spreadsheet",
                    "status": "connected",
                    "description": "Tabular analysis and formula generation.",
                    "config": {"endpoint": "https://api.example.local/sheets"},
                },
                {
                    "name": "Slides Builder",
                    "kind": "presentation",
                    "status": "connected",
                    "description": "Generate decks from structured outlines.",
                    "config": {"endpoint": "https://api.example.local/slides"},
                },
                {
                    "name": "Cloud Drive",
                    "kind": "storage",
                    "status": "connected",
                    "description": "Search, upload, and share workspace files.",
                    "config": {"endpoint": "https://api.example.local/drive"},
                },
                {
                    "name": "Task Planner",
                    "kind": "project",
                    "status": "connected",
                    "description": "Track tasks across boards and sprints.",
                    "config": {"endpoint": "https://api.example.local/tasks"},
                },
                {
                    "name": "Design Board",
                    "kind": "design",
                    "status": "connected",
                    "description": "Draft UI/artwork concepts and review states.",
                    "config": {"endpoint": "https://api.example.local/design"},
                },
                {
                    "name": "GitHub Repo",
                    "kind": "development",
                    "status": "connected",
                    "description": "Read issues, PRs, and repository metadata.",
                    "config": {"endpoint": "https://api.example.local/github"},
                },
                {
                    "name": "Postman API Runner",
                    "kind": "development",
                    "status": "connected",
                    "description": "Execute and validate API collections.",
                    "config": {"endpoint": "https://api.example.local/postman"},
                },
                {
                    "name": "Power BI Connector",
                    "kind": "bi",
                    "status": "connected",
                    "description": "Publish metrics to Power BI dashboards.",
                    "config": {"endpoint": "https://api.example.local/powerbi"},
                },
                {
                    "name": "Tableau Connector",
                    "kind": "bi",
                    "status": "connected",
                    "description": "Sync curated datasets into Tableau workbooks.",
                    "config": {"endpoint": "https://api.example.local/tableau"},
                },
                {
                    "name": "AI Assistant Bridge",
                    "kind": "ai",
                    "status": "connected",
                    "description": "Route requests to approved assistant providers.",
                    "config": {"endpoint": "https://api.example.local/ai-bridge"},
                },
                {
                    "name": "VeritasGraph MCP · Query",
                    "kind": "mcp",
                    "status": "connected",
                    "description": "Graph-grounded, multi-hop answer with citations via the local VeritasGraph MCP server.",
                    "config": {"endpoint": "http://127.0.0.1:8200/mcp/tools/veritasgraph_query"},
                },
                {
                    "name": "VeritasGraph MCP · Search",
                    "kind": "mcp",
                    "status": "connected",
                    "description": "Fast subgraph lookup (entities + relationships) via the local VeritasGraph MCP server.",
                    "config": {"endpoint": "http://127.0.0.1:8200/mcp/tools/veritasgraph_search_entities"},
                },
            ],
            Section.KNOWLEDGE.value: [
                {
                    "name": "Policy Corpus",
                    "kind": "documents",
                    "status": "indexed",
                    "description": "Policy and compliance source corpus.",
                    "config": {},
                },
                {
                    "name": "Product Wiki",
                    "kind": "documents",
                    "status": "indexing",
                    "description": "Technical and product knowledge wiki.",
                    "config": {},
                },
            ],
            Section.GUARDRAILS.value: [
                {
                    "name": "PII Filter",
                    "kind": "pii",
                    "status": "enforcing",
                    "description": "Redacts emails, phones, and sensitive IDs.",
                    "config": {},
                },
                {
                    "name": "Toxicity Monitor",
                    "kind": "safety",
                    "status": "monitoring",
                    "description": "Flags harmful or unsafe output patterns.",
                    "config": {},
                },
            ],
            Section.MEMORY.value: [
                {
                    "name": "Session Memory",
                    "kind": "short_term",
                    "status": "active",
                    "description": "Conversation-level short-term context.",
                    "config": {},
                },
                {
                    "name": "Knowledge Notes",
                    "kind": "long_term",
                    "status": "active",
                    "description": "Persisted long-term notes and summaries.",
                    "config": {},
                },
            ],
            Section.DATA.value: [
                {
                    "name": "Support Tickets",
                    "kind": "table",
                    "status": "ready",
                    "description": "Operational support history and tags.",
                    "config": {},
                },
                {
                    "name": "Telemetry Stream",
                    "kind": "stream",
                    "status": "syncing",
                    "description": "Near-real-time events and metrics stream.",
                    "config": {},
                },
            ],
        }

    def _ensure_default_catalog(self) -> None:
        changed = False
        catalog = self._default_catalog()
        with self._lock:
            for section, rows in catalog.items():
                by_name = {r.name: r for r in self._collections[section].values()}
                for row in rows:
                    existing = by_name.get(row["name"])
                    if existing is None:
                        record = ResourceRecord(
                            id=_new_id(section[:3]),
                            section=section,
                            name=row["name"],
                            kind=row.get("kind"),
                            status=row.get("status") or DEFAULT_STATUS[section],
                            description=row.get("description", ""),
                            config=row.get("config", {}),
                        )
                        self._collections[section][record.id] = record
                        changed = True
                        continue

                    # Backfill descriptive defaults without overriding user edits.
                    if not existing.description and row.get("description"):
                        existing.description = row["description"]
                        existing.updated_at = time.time()
                        changed = True
                    if not existing.config and row.get("config"):
                        existing.config = row["config"]
                        existing.updated_at = time.time()
                        changed = True

            if self._guardrail_blocks <= 0:
                self._guardrail_blocks = 12
                changed = True

        if changed:
            self._persist()

    def _seed(self) -> None:
        seeds = self._default_catalog()
        with self._lock:
            for section, rows in seeds.items():
                for row in rows:
                    record = ResourceRecord(
                        id=_new_id(section[:3]),
                        section=section,
                        name=row["name"],
                        kind=row.get("kind"),
                        status=row.get("status") or DEFAULT_STATUS[section],
                        description=row.get("description", ""),
                        config=row.get("config", {}),
                    )
                    self._collections[section][record.id] = record
            self._guardrail_blocks = 12
        self._persist()


# Module-level singleton, mirroring the data_adapter pattern.
store = StudioStore()
