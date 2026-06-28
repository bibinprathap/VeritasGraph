"""Routers for the six collection-style sections.

Agents, tools, knowledge, guardrails, memory and data all expose the same CRUD
surface, so a small factory builds one ``APIRouter`` per section instead of
duplicating handlers. Each section is reachable at ``/{section}``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from studio_api.controllers import resources as ctrl
from studio_api.dependencies import get_store
from studio_api.models import (
    ResourceCreateRequest,
    ResourceUpdateRequest,
    Section,
)
from studio_api.store import StudioStore


def _build_router(section: str) -> APIRouter:
    router = APIRouter(prefix=f"/{section}", tags=[section])

    @router.get("/")
    async def list_items(store: StudioStore = Depends(get_store)):
        return await ctrl.list_resources(store, section)

    @router.post("/")
    async def create_item(
        payload: ResourceCreateRequest, store: StudioStore = Depends(get_store)
    ):
        return await ctrl.create_resource(store, section, payload)

    @router.get("/{resource_id}")
    async def get_item(resource_id: str, store: StudioStore = Depends(get_store)):
        return await ctrl.get_resource(store, section, resource_id)

    @router.patch("/{resource_id}")
    async def update_item(
        resource_id: str,
        payload: ResourceUpdateRequest,
        store: StudioStore = Depends(get_store),
    ):
        return await ctrl.update_resource(store, section, resource_id, payload)

    @router.delete("/{resource_id}")
    async def delete_item(resource_id: str, store: StudioStore = Depends(get_store)):
        return await ctrl.delete_resource(store, section, resource_id)

    return router


resource_routers = [_build_router(section.value) for section in Section]
