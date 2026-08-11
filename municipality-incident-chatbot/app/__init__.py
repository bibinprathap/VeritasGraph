"""Municipality Incident Reporting Chatbot — reference implementation.

A runnable implementation of the solution design in this folder, built on top of
the **VeritasGraph** GraphRAG engine (``studio_api.graphrag_engine``).

Layers (see ``01_architecture.md``):

* :mod:`app.knowledge_graph` — VeritasGraph-backed knowledge graph (grounding + routing)
* :mod:`app.cv_service`      — computer-vision validation (YOLO / VLM, with a
  deterministic fallback backend so the pipeline runs offline)
* :mod:`app.external_sources`— CCTV / IoT-sensor corroboration connectors
* :mod:`app.fusion`          — evidence fusion & scoring
* :mod:`app.case_service`    — case registration + duplicate detection
* :mod:`app.orchestrator`    — the chatbot that ties it all together
"""

from .orchestrator import IncidentChatbot, ReportResult

__all__ = ["IncidentChatbot", "ReportResult"]
