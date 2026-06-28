"""Controllers for the Evaluation section (run simulation + trend)."""

from __future__ import annotations

import asyncio

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from studio_api.models import EvaluationRunRequest
from studio_api.store import StudioStore


async def list_runs(store: StudioStore) -> JSONResponse:
    runs = await asyncio.to_thread(store.list_evaluations)
    return JSONResponse(
        content={
            "message": "Evaluation runs retrieved successfully",
            "runs": [r.model_dump(mode="json") for r in runs],
            "count": len(runs),
        }
    )


async def get_run(store: StudioStore, run_id: str) -> JSONResponse:
    run = await asyncio.to_thread(store.get_evaluation, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return JSONResponse(content={"message": "Evaluation run retrieved successfully", "run": run.model_dump(mode="json")})


async def start_run(store: StudioStore, payload: EvaluationRunRequest) -> JSONResponse:
    run = await asyncio.to_thread(store.start_evaluation, payload)
    return JSONResponse(
        status_code=201,
        content={"message": "Evaluation run started", "run": run.model_dump(mode="json")},
    )


async def advance(store: StudioStore) -> JSONResponse:
    counts = await asyncio.to_thread(store.advance)
    return JSONResponse(content={"message": "Simulations advanced", **counts})
