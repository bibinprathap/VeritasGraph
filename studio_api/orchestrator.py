"""Agent orchestration pipeline.

This is where the Knowledge Graph is wired into the rest of the studio. A single
agent run flows through six cooperating sections, each toggled by the agent's
``config``:

    1. Guardrails (in)   -> redact PII / block disallowed input
    2. Memory (recall)   -> prepend prior conversation turns
    3. Knowledge Graph   -> multi-hop retrieval of grounding context + citations
    4. Headroom budget   -> fit graph context into a token budget (CCR markers)
    5. Tools             -> advertise callable tools (incl. the graph retriever)
    6. Data              -> log the interaction for later inspection

The LLM call itself stays in the route (it owns Ollama error handling); this
module prepares the message buffer and finalises the reply, returning a rich
``trace`` so the UI can show exactly how each section contributed.

Everything here is synchronous and dependency-injected (store, graph engine,
budgeter) so the pipeline is unit-testable without a running model.
"""

from __future__ import annotations

import json
import re
from urllib import parse as urlparse
from urllib import request as urlrequest
from typing import Any, Dict, List, Optional

from studio_api.compression import ContextBudgeter, budgeter as _default_budgeter
from studio_api.graphrag_engine import GraphRAGEngine, engine as _default_engine
from studio_api.store import StudioStore

# --------------------------------------------------------------------------- #
# Guardrail primitives
# --------------------------------------------------------------------------- #
_PII_PATTERNS = [
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("phone", re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
]

# Status values that mean a guardrail is live.
_ACTIVE_GUARDRAIL = {"enforcing", "monitoring", "active"}
_PII_KINDS = {"pii", "redaction", "privacy"}
_BLOCK_KINDS = {"safety", "toxicity", "blocklist", "moderation", "policy"}
_DEFAULT_BLOCK_TERMS = ["bomb", "weapon", "malware", "ransomware"]


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}
    return False


def _redact_pii(text: str) -> tuple[str, int]:
    """Replace PII matches with a typed placeholder; return (text, count)."""
    redactions = 0
    for label, pattern in _PII_PATTERNS:

        def _sub(_m: "re.Match[str]", _label: str = label) -> str:
            nonlocal redactions
            redactions += 1
            return f"[redacted:{_label}]"

        text = pattern.sub(_sub, text)
    return text, redactions


def _split_terms(raw: Any) -> List[str]:
    if isinstance(raw, list):
        return [str(t).strip().lower() for t in raw if str(t).strip()]
    if isinstance(raw, str):
        return [t.strip().lower() for t in raw.split(",") if t.strip()]
    return []


class Orchestrator:
    """Runs the studio's agent pipeline around a single LLM call."""

    def __init__(
        self,
        store: StudioStore,
        engine: Optional[GraphRAGEngine] = None,
        budgeter: Optional[ContextBudgeter] = None,
    ) -> None:
        self.store = store
        self.engine = engine or _default_engine
        self.budgeter = budgeter or _default_budgeter

    # ------------------------------------------------------------------ #
    # Section helpers
    # ------------------------------------------------------------------ #
    def _active_guardrails(self, agent) -> list:
        cfg = agent.config or {}
        if not _truthy(cfg.get("use_guardrails")):
            return []
        wanted = set(cfg.get("guardrail_ids") or [])
        rails = []
        for gr in self.store.list_resources("guardrails"):
            if gr.status not in _ACTIVE_GUARDRAIL:
                continue
            if wanted and gr.id not in wanted:
                continue
            rails.append(gr)
        return rails

    def _apply_input_guardrails(self, agent, text: str) -> Dict[str, Any]:
        """Redact PII and block disallowed input. Returns a guardrail report."""
        rails = self._active_guardrails(agent)
        applied: List[str] = []
        redactions = 0
        blocked = False
        block_reason = ""
        cleaned = text

        for gr in rails:
            kind = (gr.kind or "").lower()
            if kind in _PII_KINDS:
                cleaned, n = _redact_pii(cleaned)
                if n:
                    redactions += n
                applied.append(gr.name)
            elif kind in _BLOCK_KINDS:
                terms = _split_terms((gr.config or {}).get("block_terms")) or _DEFAULT_BLOCK_TERMS
                hit = next((t for t in terms if t and t in cleaned.lower()), None)
                if hit:
                    blocked = True
                    block_reason = f"'{gr.name}' blocked input containing '{hit}'."
                applied.append(gr.name)

        if redactions:
            self.store.record_guardrail_block(redactions)
        if blocked:
            self.store.record_guardrail_block(1)

        return {
            "applied": applied,
            "redactions": redactions,
            "blocked": blocked,
            "reason": block_reason,
            "text": cleaned,
        }

    def _apply_output_guardrails(self, agent, text: str) -> Dict[str, Any]:
        rails = self._active_guardrails(agent)
        applied: List[str] = []
        redactions = 0
        cleaned = text
        for gr in rails:
            if (gr.kind or "").lower() in _PII_KINDS:
                cleaned, n = _redact_pii(cleaned)
                redactions += n
                applied.append(gr.name)
        if redactions:
            self.store.record_guardrail_block(redactions)
        return {"applied": applied, "redactions": redactions, "text": cleaned}

    def _graph_context(self, agent, query: str) -> Dict[str, Any]:
        cfg = agent.config or {}
        if not _truthy(cfg.get("use_graph")):
            return {"used": False}
        depth = int(cfg.get("graph_depth") or 2)
        nodes = int(cfg.get("graph_nodes") or 20)
        ctx = self.engine.retrieve(query, max_depth=depth, max_nodes=nodes)
        id_to_name = {e["id"]: e["name"] for e in ctx["nodes"]}
        reasoning_path = [
            f"{id_to_name.get(r['source'], '?')} --[{r['description'] or 'related to'}]--> "
            f"{id_to_name.get(r['target'], '?')}"
            for r in ctx["edges"]
        ]
        # Each retrieved fact/source becomes a budgetable chunk.
        chunks: List[str] = []
        if ctx["nodes"]:
            chunks.append(
                "ENTITIES:\n"
                + "\n".join(f"- {e['name']} ({e['type']}): {e['description']}" for e in ctx["nodes"])
            )
        if reasoning_path:
            chunks.append("RELATIONSHIPS:\n" + "\n".join(reasoning_path))
        for s in ctx["sources"]:
            chunks.append(f"[{s['id']}] {s['title']}: {s['text']}")
        return {
            "used": True,
            "seeds": [self.engine.entities[s]["name"] for s in ctx["seeds"] if s in self.engine.entities],
            "node_count": len(ctx["nodes"]),
            "edge_count": len(ctx["edges"]),
            "reasoning_path": reasoning_path,
            "citations": [{"id": s["id"], "title": s["title"]} for s in ctx["sources"]],
            "chunks": chunks,
            "subgraph": {
                "nodes": [{"id": e["id"], "name": e["name"], "type": e["type"]} for e in ctx["nodes"]],
                "edges": [
                    {"source": r["source"], "target": r["target"], "description": r["description"]}
                    for r in ctx["edges"]
                ],
            },
        }

    def _tool_catalog(self, agent) -> Dict[str, Any]:
        cfg = agent.config or {}
        if not _truthy(cfg.get("use_tools")):
            return {"used": False, "available": [], "registered": []}
        wanted = set(cfg.get("tool_ids") or [])
        profile = set(cfg.get("tool_profile") or [])
        names: List[str] = []
        registered: List[Dict[str, str]] = []
        for tool in self.store.list_resources("tools"):
            if tool.status == "disabled":
                continue
            if wanted and tool.id not in wanted:
                continue
            if profile and tool.name not in profile:
                continue
            names.append(tool.name)
            registered.append(
                {
                    "name": tool.name,
                    "kind": tool.kind or "read",
                    "endpoint": str((tool.config or {}).get("endpoint") or "").strip(),
                }
            )
        if _truthy(cfg.get("use_graph")) and "Knowledge Graph" not in names:
            names.append("Knowledge Graph")
        return {"used": True, "available": names, "registered": registered}

    def _invoke_tools(self, agent, query: str, tools: Dict[str, Any], graph: Dict[str, Any]) -> Dict[str, Any]:
        cfg = agent.config or {}
        if not tools.get("used"):
            return {"invoked": 0, "succeeded": 0, "failed": 0, "results": [], "errors": []}

        max_calls = int(cfg.get("max_tool_calls") or 3)
        timeout_s = float(cfg.get("tool_timeout_seconds") or 4.0)
        allow_external = _truthy(cfg.get("allow_external_tools"))

        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        invoked = 0

        for tool in tools.get("registered", [])[:max_calls]:
            endpoint = tool.get("endpoint") or ""
            if not endpoint:
                continue

            parsed = urlparse.urlparse(endpoint)
            host = (parsed.hostname or "").lower()
            is_loopback = host in {"127.0.0.1", "localhost", "::1"}
            if not allow_external and not is_loopback:
                errors.append({"tool": tool["name"], "status": "skipped", "error": "external endpoint blocked"})
                continue

            payload: Dict[str, Any]
            if endpoint.endswith("/graphrag/query"):
                payload = {
                    "question": query,
                    "model": agent.kind,
                    "max_depth": 2,
                    "max_nodes": 20,
                }
            else:
                payload = {
                    "query": query,
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "citations": [c.get("id") for c in graph.get("citations", [])],
                }

            body = json.dumps(payload).encode("utf-8")
            req = urlrequest.Request(endpoint, data=body, method="POST")
            req.add_header("Content-Type", "application/json")

            try:
                with urlrequest.urlopen(req, timeout=timeout_s) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                    content_type = (resp.headers.get("Content-Type") or "").lower()
                    data: Any
                    if "application/json" in content_type:
                        data = json.loads(raw) if raw else {}
                    else:
                        try:
                            data = json.loads(raw)
                        except Exception:
                            data = raw

                    if isinstance(data, dict):
                        summary = (
                            data.get("answer")
                            or data.get("summary")
                            or data.get("result")
                            or data.get("message")
                            or str(data)[:240]
                        )
                    else:
                        summary = str(data)[:240]

                    results.append(
                        {
                            "tool": tool["name"],
                            "status": "ok",
                            "endpoint": endpoint,
                            "summary": str(summary),
                        }
                    )
                    invoked += 1
            except Exception as exc:
                errors.append(
                    {
                        "tool": tool["name"],
                        "status": "failed",
                        "endpoint": endpoint,
                        "error": str(exc),
                    }
                )
                invoked += 1

        return {
            "invoked": invoked,
            "succeeded": len(results),
            "failed": len([e for e in errors if e.get("status") == "failed"]),
            "results": results,
            "errors": errors,
        }

    # ------------------------------------------------------------------ #
    # Public pipeline
    # ------------------------------------------------------------------ #
    def prepare(self, agent, message: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Stages 1-5: build the message buffer and a pipeline trace.

        Returns a dict with ``blocked``, ``messages``, ``model`` and ``trace``.
        When ``blocked`` is True, ``messages`` is empty and ``block_reason`` holds
        the refusal text to surface to the user.
        """
        cfg = agent.config or {}
        trace: Dict[str, Any] = {}

        # 1. Input guardrails -------------------------------------------------
        gin = self._apply_input_guardrails(agent, message)
        trace["guardrails_in"] = {
            "applied": gin["applied"],
            "redactions": gin["redactions"],
            "blocked": gin["blocked"],
            "reason": gin["reason"],
        }
        if gin["blocked"]:
            return {
                "blocked": True,
                "block_reason": (
                    "I can't help with that request. "
                    + gin["reason"]
                ),
                "messages": [],
                "model": agent.kind,
                "trace": trace,
                "citations": [],
                "reasoning_path": [],
                "subgraph": {"nodes": [], "edges": []},
            }
        user_text = gin["text"]

        # 2. Memory recall ----------------------------------------------------
        use_memory = _truthy(cfg.get("use_memory"))
        memory_turns: List[Dict[str, str]] = []
        if use_memory:
            limit = int(cfg.get("memory_turns") or 6)
            memory_turns = [
                {"role": t["role"], "content": t["content"]}
                for t in self.store.get_memory(agent.id, limit=limit)
            ]
        elif history:
            memory_turns = [{"role": t["role"], "content": t["content"]} for t in history]
        trace["memory"] = {"used": use_memory, "recalled_turns": len(memory_turns)}

        # 3. Knowledge graph retrieval ---------------------------------------
        graph = self._graph_context(agent, user_text)
        graph_chunks = graph.get("chunks", []) if graph.get("used") else []

        # 4. Headroom budgeting ----------------------------------------------
        budget_tokens = int(cfg.get("context_budget") or 600)
        kept_chunks = graph_chunks
        budget_trace = {"used": False}
        if graph_chunks:
            result = self.budgeter.budget(graph_chunks, query=user_text, max_tokens=budget_tokens)
            kept_chunks = result.kept
            budget_trace = {
                "used": True,
                "budget_tokens": result.budget_tokens,
                "used_tokens": result.used_tokens,
                "kept": len(result.kept),
                "dropped": result.dropped_count,
                "markers": result.markers,
            }
        trace["budget"] = budget_trace
        trace["graph"] = {
            "used": graph.get("used", False),
            "seeds": graph.get("seeds", []),
            "nodes": graph.get("node_count", 0),
            "edges": graph.get("edge_count", 0),
            "reasoning_path": graph.get("reasoning_path", []),
            "citations": graph.get("citations", []),
        }

        # 5. Tools ------------------------------------------------------------
        tools = self._tool_catalog(agent)
        tool_run = self._invoke_tools(agent, user_text, tools, graph)
        trace["tools"] = {
            **tools,
            "invoked": tool_run["invoked"],
            "succeeded": tool_run["succeeded"],
            "failed": tool_run["failed"],
            "results": tool_run["results"],
            "errors": tool_run["errors"],
        }

        # Assemble the system prompt ----------------------------------------
        base_prompt = cfg.get("prompt") or agent.description or "You are a helpful assistant."
        system_parts = [base_prompt]
        if tools["used"] and tools["available"]:
            system_parts.append("Available tools: " + ", ".join(tools["available"]) + ".")
        if tool_run["results"]:
            system_parts.append(
                "Tool results:\n"
                + "\n".join(
                    f"- {r['tool']}: {r['summary']}" for r in tool_run["results"]
                )
            )
        if kept_chunks:
            system_parts.append(
                "Use ONLY the following knowledge-graph context to answer. Cite the "
                "source id in square brackets, e.g. [doc_xxx#0]. If it is insufficient, "
                "say so.\n\n" + "\n\n".join(kept_chunks)
            )
        system_prompt = "\n\n".join(p for p in system_parts if p)

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        messages.extend(memory_turns)
        messages.append({"role": "user", "content": user_text})

        return {
            "blocked": False,
            "block_reason": "",
            "messages": messages,
            "model": agent.kind,
            "user_text": user_text,
            "trace": trace,
            "citations": graph.get("citations", []),
            "reasoning_path": graph.get("reasoning_path", []),
            "subgraph": graph.get("subgraph", {"nodes": [], "edges": []}),
        }

    def finalize(self, agent, user_text: str, reply: str, trace: Dict[str, Any]) -> Dict[str, Any]:
        """Stages 1(out) & 6: redact the reply, persist memory, log the run."""
        cfg = agent.config or {}

        gout = self._apply_output_guardrails(agent, reply)
        trace["guardrails_out"] = {"applied": gout["applied"], "redactions": gout["redactions"]}
        clean_reply = gout["text"]

        if _truthy(cfg.get("use_memory")):
            self.store.append_memory(agent.id, "user", user_text)
            self.store.append_memory(agent.id, "assistant", clean_reply)

        if _truthy(cfg.get("use_data")):
            self.store.log_interaction(
                agent.id,
                {
                    "question": user_text,
                    "answer": clean_reply[:500],
                    "citations": [c.get("id") for c in trace.get("graph", {}).get("citations", [])],
                },
            )
            trace["data"] = {"logged": True}
        else:
            trace["data"] = {"logged": False}

        return {"reply": clean_reply, "trace": trace}
