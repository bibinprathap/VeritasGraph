"""Fine-tune routes: queue jobs and watch status progression."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from studio_api.controllers import finetune as ctrl
from studio_api.dependencies import get_store
from studio_api.models import FineTuneJobRequest
from studio_api.store import StudioStore

finetune_router = APIRouter(prefix="/finetune", tags=["finetune"])


@finetune_router.get("/jobs")
async def list_jobs(store: StudioStore = Depends(get_store)):
    return await ctrl.list_jobs(store)


@finetune_router.post("/jobs")
async def queue_job(
    payload: FineTuneJobRequest, store: StudioStore = Depends(get_store)
):
    return await ctrl.queue_job(store, payload)


@finetune_router.get("/jobs/{job_id}")
async def get_job(job_id: str, store: StudioStore = Depends(get_store)):
    return await ctrl.get_job(store, job_id)
