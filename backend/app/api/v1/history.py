"""User activity history endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DB, CurrentUser, Pagination
from app.schemas import HistoryRead, Page
from app.services import HistoryService

router = APIRouter()


@router.get("", response_model=Page[HistoryRead], summary="My activity history")
async def history(user: CurrentUser, db: DB, params: Pagination) -> Page[HistoryRead]:
    return await HistoryService(db).list(user.id, params)
