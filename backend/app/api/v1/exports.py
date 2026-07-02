"""Export endpoints: stream search results as CSV/XLSX/PDF/JSON."""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.api.deps import DB, CurrentUser, Pagination
from app.models import ExportFormat
from app.repositories import HistoryRepository
from app.schemas import ExportCreate, ExportRead, Page
from app.repositories import ExportRepository
from app.services import ExportService

router = APIRouter()


@router.post("", summary="Export a search's results (returns the file)")
async def create_export(payload: ExportCreate, user: CurrentUser, db: DB) -> Response:
    data, filename, media_type = await ExportService(db).export_search(
        user_id=user.id, search_id=payload.search_id, fmt=payload.format
    )
    await HistoryRepository(db).record(
        user.id, "export.created", entity_type="search", entity_id=payload.search_id,
        meta={"format": payload.format.value},
    )
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("", response_model=Page[ExportRead], summary="My export history")
async def list_exports(user: CurrentUser, db: DB, params: Pagination) -> Page[ExportRead]:
    items, total = await ExportRepository(db).list_for_user(
        user.id, offset=params.offset, limit=params.limit
    )
    return Page.create(
        items=[ExportRead.model_validate(e) for e in items], total=total, params=params
    )


@router.get("/formats", response_model=list[str], summary="Supported export formats")
async def formats(user: CurrentUser) -> list[str]:
    return [f.value for f in ExportFormat]
