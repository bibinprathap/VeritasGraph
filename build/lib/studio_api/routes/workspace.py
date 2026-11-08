"""Workspace routes: KPI header cards, draft persistence, deploy, guardrail hits."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from studio_api.controllers import workspace as ctrl
from studio_api.dependencies import get_store
from studio_api.models import DeployRequest, WorkspaceDraft
from studio_api.store import StudioStore

workspace_router = APIRouter(prefix="/workspace", tags=["workspace"])


@workspace_router.get("/kpis")
async def get_kpis(store: StudioStore = Depends(get_store)):
    return await ctrl.get_kpis(store)


@workspace_router.get("/draft")
async def get_draft(store: StudioStore = Depends(get_store)):
    return await ctrl.get_draft(store)


@workspace_router.put("/draft")
async def save_draft(draft: WorkspaceDraft, store: StudioStore = Depends(get_store)):
    return await ctrl.save_draft(store, draft)


@workspace_router.post("/deploy")
async def deploy(payload: DeployRequest, store: StudioStore = Depends(get_store)):
    return await ctrl.deploy(store, payload)


@workspace_router.get("/deploy")
async def deploy_history(store: StudioStore = Depends(get_store)):
    return await ctrl.deploy_history(store)


@workspace_router.post("/guardrail-blocks")
async def record_guardrail_block(
    count: int = 1, store: StudioStore = Depends(get_store)
):
    return await ctrl.record_guardrail_block(store, count)
