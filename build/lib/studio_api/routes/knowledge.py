"""Knowledge context-budgeting endpoints (in addition to the CRUD router)."""

from __future__ import annotations

from fastapi import APIRouter

from studio_api.controllers import knowledge as ctrl
from studio_api.controllers.knowledge import BudgetRequest

knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@knowledge_router.post("/budget")
async def budget_context(payload: BudgetRequest):
    """Select the highest-signal chunks that fit a token budget."""
    return await ctrl.budget_context(payload)


@knowledge_router.get("/chunks/{handle}")
async def retrieve_chunk(handle: str):
    """Resolve a chunk that was dropped by a previous budgeting call."""
    return await ctrl.retrieve_chunk(handle)
