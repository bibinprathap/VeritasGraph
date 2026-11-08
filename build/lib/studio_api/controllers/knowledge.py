"""Controllers for the Knowledge section's context budgeting endpoints."""

from __future__ import annotations

import asyncio
from typing import List, Optional

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from studio_api.compression import budgeter


class BudgetRequest(BaseModel):
    chunks: List[str] = Field(..., description="Candidate context chunks.")
    query: str = Field(default="", description="Optional query to bias selection.")
    max_tokens: int = Field(default=1024, ge=1, description="Token budget.")


async def budget_context(payload: BudgetRequest) -> JSONResponse:
    result = await asyncio.to_thread(
        budgeter.budget,
        payload.chunks,
        query=payload.query,
        max_tokens=payload.max_tokens,
    )
    return JSONResponse(
        content={
            "message": "Context budgeted successfully",
            "kept": result.kept,
            "kept_count": len(result.kept),
            "dropped_handles": result.dropped_handles,
            "markers": result.markers,
            "dropped_count": result.dropped_count,
            "used_tokens": result.used_tokens,
            "budget_tokens": result.budget_tokens,
        }
    )


async def retrieve_chunk(handle: str) -> JSONResponse:
    chunk: Optional[str] = await asyncio.to_thread(budgeter.retrieve, handle)
    if chunk is None:
        raise HTTPException(status_code=404, detail="Handle not found")
    return JSONResponse(content={"message": "Chunk retrieved successfully", "handle": handle, "chunk": chunk})
