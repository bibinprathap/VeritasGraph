"""Generic CRUD controllers for the collection-style studio sections."""

from __future__ import annotations

import asyncio

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from studio_api.models import (
    ResourceCreateRequest,
    ResourceUpdateRequest,
    Section,
)
from studio_api.store import StudioStore


def _validate_section(section: str) -> str:
    try:
        return Section(section).value
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown section '{section}'") from exc


async def list_resources(store: StudioStore, section: str) -> JSONResponse:
    section = _validate_section(section)
    items = await asyncio.to_thread(store.list_resources, section)
    return JSONResponse(
        content={
            "message": f"{section} retrieved successfully",
            "section": section,
            "items": [r.model_dump(mode="json") for r in items],
            "count": len(items),
        }
    )


async def get_resource(store: StudioStore, section: str, resource_id: str) -> JSONResponse:
    section = _validate_section(section)
    record = await asyncio.to_thread(store.get_resource, section, resource_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return JSONResponse(
        content={"message": "Resource retrieved successfully", "item": record.model_dump(mode="json")}
    )


async def create_resource(
    store: StudioStore, section: str, payload: ResourceCreateRequest
) -> JSONResponse:
    section = _validate_section(section)
    record = await asyncio.to_thread(store.create_resource, section, payload)
    return JSONResponse(
        status_code=201,
        content={"message": "Resource created successfully", "item": record.model_dump(mode="json")},
    )


async def update_resource(
    store: StudioStore, section: str, resource_id: str, payload: ResourceUpdateRequest
) -> JSONResponse:
    section = _validate_section(section)
    record = await asyncio.to_thread(store.update_resource, section, resource_id, payload)
    if record is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return JSONResponse(
        content={"message": "Resource updated successfully", "item": record.model_dump(mode="json")}
    )


async def delete_resource(store: StudioStore, section: str, resource_id: str) -> JSONResponse:
    section = _validate_section(section)
    deleted = await asyncio.to_thread(store.delete_resource, section, resource_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resource not found")
    return JSONResponse(content={"message": "Resource deleted successfully", "id": resource_id})
