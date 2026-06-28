"""Evaluation routes: start runs, inspect trend, advance simulation."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from studio_api.controllers import evaluation as ctrl
from studio_api.dependencies import get_store
from studio_api.models import EvaluationRunRequest
from studio_api.store import StudioStore

evaluation_router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@evaluation_router.get("/runs")
async def list_runs(store: StudioStore = Depends(get_store)):
    return await ctrl.list_runs(store)


@evaluation_router.post("/runs")
async def start_run(
    payload: EvaluationRunRequest, store: StudioStore = Depends(get_store)
):
    return await ctrl.start_run(store, payload)


@evaluation_router.get("/runs/{run_id}")
async def get_run(run_id: str, store: StudioStore = Depends(get_store)):
    return await ctrl.get_run(store, run_id)


@evaluation_router.post("/advance")
async def advance(store: StudioStore = Depends(get_store)):
    """Advance every in-flight evaluation and fine-tune by one simulated step."""
    return await ctrl.advance(store)
