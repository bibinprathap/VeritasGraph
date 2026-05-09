"""
VeritasReason × Agno Integration
=============================

First-class integration between the VeritasReason semantic intelligence stack and
the `Agno <https://github.com/agno-agi/agno>`_ agentic framework.

Public surface
--------------
AgnoContextStore   — Graph-backed ``MemoryDb`` (drop-in for ``AgentMemory(db=…)``)
AgnoKnowledgeGraph — Relational ``AgentKnowledge`` with multi-hop GraphRAG
AgnoDecisionKit    — Agno ``Toolkit`` exposing decision-intelligence tools
AgnoKGToolkit      — Agno ``Toolkit`` exposing KG construction/query tools
AgnoSharedContext  — Team-level shared ``ContextGraph`` with per-agent scoping

Quick start
-----------
    pip install veritas-reason[agno]

    >>> from integrations.agno import (
    ...     AgnoContextStore,
    ...     AgnoKnowledgeGraph,
    ...     AgnoDecisionKit,
    ...     AgnoKGToolkit,
    ...     AgnoSharedContext,
    ... )

Compatibility
-------------
Requires ``agno >= 1.0``.  All five classes degrade gracefully when ``agno``
is not installed — they are still importable and carry the full VeritasReason API,
but cannot be passed directly to Agno ``Agent`` / ``Team`` constructors.
"""

from .context_store import AGNO_AVAILABLE, AgnoContextStore
from .decision_kit import AgnoDecisionKit
from .kg_toolkit import AgnoKGToolkit
from .knowledge_graph import AgnoKnowledgeGraph
from .shared_context import AgnoSharedContext

__all__ = [
    "AgnoContextStore",
    "AgnoKnowledgeGraph",
    "AgnoDecisionKit",
    "AgnoKGToolkit",
    "AgnoSharedContext",
    "AGNO_AVAILABLE",
]

__version__ = "0.3.0"
