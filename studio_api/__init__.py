"""Agent Studio backend.

A self-contained FastAPI service that powers the Agent Studio UI. It mirrors the
routes -> controllers -> adapter layering used elsewhere in this repository and
implements every studio section (Agents, Tools, Knowledge, Guardrails, Memory,
Data, Evaluation, Fine-tune) plus workspace-level KPIs, draft persistence and a
deploy mock.
"""

__all__ = ["__version__"]

__version__ = "1.0.0"
