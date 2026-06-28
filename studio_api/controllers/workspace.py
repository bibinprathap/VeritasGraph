"""Controllers for workspace-level actions: KPIs, draft, deploy, guardrail hits."""

from __future__ import annotations

import asyncio

from fastapi.responses import JSONResponse

from studio_api.models import DeployRequest, WorkspaceDraft
from studio_api.store import StudioStore


async def get_kpis(store: StudioStore) -> JSONResponse:
    kpis = await asyncio.to_thread(store.kpis)
    return JSONResponse(content={"message": "KPIs retrieved successfully", "kpis": kpis})


async def get_draft(store: StudioStore) -> JSONResponse:
    draft = await asyncio.to_thread(store.get_draft)
    return JSONResponse(content={"message": "Draft retrieved successfully", "draft": draft.model_dump(mode="json")})


async def save_draft(store: StudioStore, draft: WorkspaceDraft) -> JSONResponse:
    saved = await asyncio.to_thread(store.save_draft, draft)
    return JSONResponse(content={"message": "Draft saved successfully", "draft": saved.model_dump(mode="json")})


async def deploy(store: StudioStore, payload: DeployRequest) -> JSONResponse:
    record = await asyncio.to_thread(
        store.deploy, payload.workspace, payload.environment, payload.notes
    )
    return JSONResponse(content={"message": "Workspace deployed successfully", "deployment": record})


async def deploy_history(store: StudioStore) -> JSONResponse:
    history = await asyncio.to_thread(store.deploy_history)
    return JSONResponse(content={"message": "Deploy history retrieved successfully", "history": history})


async def record_guardrail_block(store: StudioStore, count: int) -> JSONResponse:
    total = await asyncio.to_thread(store.record_guardrail_block, count)
    return JSONResponse(content={"message": "Guardrail block recorded", "guardrail_blocks": total})
