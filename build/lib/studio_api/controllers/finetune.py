"""Controllers for the Fine-tune section (queue simulation)."""

from __future__ import annotations

import asyncio

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from studio_api.models import FineTuneJobRequest
from studio_api.store import StudioStore


async def list_jobs(store: StudioStore) -> JSONResponse:
    jobs = await asyncio.to_thread(store.list_finetunes)
    return JSONResponse(
        content={
            "message": "Fine-tune jobs retrieved successfully",
            "jobs": [j.model_dump(mode="json") for j in jobs],
            "count": len(jobs),
        }
    )


async def get_job(store: StudioStore, job_id: str) -> JSONResponse:
    job = await asyncio.to_thread(store.get_finetune, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Fine-tune job not found")
    return JSONResponse(content={"message": "Fine-tune job retrieved successfully", "job": job.model_dump(mode="json")})


async def queue_job(store: StudioStore, payload: FineTuneJobRequest) -> JSONResponse:
    job = await asyncio.to_thread(store.queue_finetune, payload)
    return JSONResponse(
        status_code=201,
        content={"message": "Fine-tune job queued", "job": job.model_dump(mode="json")},
    )
