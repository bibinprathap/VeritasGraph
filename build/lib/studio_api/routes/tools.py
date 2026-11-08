"""Tool-specific routes that extend the generic ``/tools`` collection surface.

The CRUD endpoints for tools are provided by the generic resource router
factory. This router adds ``POST /tools/{id}/test`` so an operator can validate a
registered tool by actually calling its real endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from studio_api.controllers import tools as ctrl
from studio_api.dependencies import get_store
from studio_api.store import StudioStore

tools_router = APIRouter(prefix="/tools", tags=["tools"])


@tools_router.post("/{tool_id}/test")
async def test_tool(tool_id: str, store: StudioStore = Depends(get_store)):
    return await ctrl.test_tool(store, tool_id)
