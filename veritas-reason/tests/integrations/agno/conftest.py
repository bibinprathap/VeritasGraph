"""
Shared pytest configuration for Agno integration tests.

Installs a comprehensive agno stub into sys.modules before any test in this
directory runs, so that every test file can import the integration modules
without a real agno installation.

Each per-file stub only runs `if "agno" in sys.modules: return`, which would
skip when another file already loaded a partial stub.  This conftest installs
ALL required sub-modules at session start so the guard works correctly for
every file.
"""
from __future__ import annotations

import sys
import types


def _install_agno_stubs() -> None:
    """Install a full set of agno stubs into sys.modules."""

    # -----------------------------------------------------------------------
    # agno root
    # -----------------------------------------------------------------------
    agno = sys.modules.get("agno") or types.ModuleType("agno")

    # -----------------------------------------------------------------------
    # agno.memory.db.base  — MemoryDb
    # -----------------------------------------------------------------------
    memory_pkg = types.ModuleType("agno.memory")
    memory_db_pkg = types.ModuleType("agno.memory.db")
    memory_db_base = types.ModuleType("agno.memory.db.base")
    memory_db_row = types.ModuleType("agno.memory.db.row")

    class MemoryDb:  # noqa: D101
        def __init__(self, *a, **kw): ...  # noqa: E704

    class MemoryRow:  # noqa: D101
        def __init__(self, memory: str, id=None, user_id=None, **kw):
            self.memory = memory
            self.id = id
            self.user_id = user_id
            self.last_updated = 0.0
            self.topics = kw.get("topics", [])

    memory_db_base.MemoryDb = MemoryDb  # type: ignore
    memory_db_row.MemoryRow = MemoryRow  # type: ignore
    memory_db_pkg.base = memory_db_base
    memory_db_pkg.row = memory_db_row
    memory_pkg.db = memory_db_pkg
    agno.memory = memory_pkg  # type: ignore

    # -----------------------------------------------------------------------
    # agno.tools.toolkit  — Toolkit
    # -----------------------------------------------------------------------
    tools_pkg = types.ModuleType("agno.tools")
    tools_toolkit_mod = types.ModuleType("agno.tools.toolkit")

    class Toolkit:  # noqa: D101
        def __init__(self, name: str = "toolkit", **kw):
            self.name = name
            self._tools: list = []

        def register(self, fn):  # noqa: D102
            self._tools.append(fn)

    tools_toolkit_mod.Toolkit = Toolkit  # type: ignore
    tools_pkg.toolkit = tools_toolkit_mod
    agno.tools = tools_pkg  # type: ignore

    # -----------------------------------------------------------------------
    # agno.knowledge.base  — AgentKnowledge
    # -----------------------------------------------------------------------
    knowledge_pkg = types.ModuleType("agno.knowledge")
    knowledge_base_mod = types.ModuleType("agno.knowledge.base")

    class AgentKnowledge:  # noqa: D101
        def __init__(self, *a, **kw): ...  # noqa: E704

        def search(self, query, num_documents=None, filters=None):  # noqa: D102
            return []

    knowledge_base_mod.AgentKnowledge = AgentKnowledge  # type: ignore
    knowledge_pkg.base = knowledge_base_mod
    agno.knowledge = knowledge_pkg  # type: ignore

    # -----------------------------------------------------------------------
    # agno.document.base  — Document
    # -----------------------------------------------------------------------
    document_pkg = types.ModuleType("agno.document")
    document_base_mod = types.ModuleType("agno.document.base")

    class Document:  # noqa: D101
        def __init__(self, content="", id=None, name=None, meta_data=None):
            self.content = content
            self.id = id
            self.name = name
            self.meta_data = meta_data or {}

    document_base_mod.Document = Document  # type: ignore
    document_pkg.base = document_base_mod
    agno.document = document_pkg  # type: ignore

    # -----------------------------------------------------------------------
    # Register everything
    # -----------------------------------------------------------------------
    _mods = {
        "agno": agno,
        "agno.memory": memory_pkg,
        "agno.memory.db": memory_db_pkg,
        "agno.memory.db.base": memory_db_base,
        "agno.memory.db.row": memory_db_row,
        "agno.tools": tools_pkg,
        "agno.tools.toolkit": tools_toolkit_mod,
        "agno.knowledge": knowledge_pkg,
        "agno.knowledge.base": knowledge_base_mod,
        "agno.document": document_pkg,
        "agno.document.base": document_base_mod,
    }
    for name, mod in _mods.items():
        sys.modules[name] = mod


# Install once at import time (conftest is imported before any test file)
_install_agno_stubs()
