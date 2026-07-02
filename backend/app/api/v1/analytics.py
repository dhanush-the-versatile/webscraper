"""Analytics dashboard endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import DB, CurrentUser
from app.schemas import AnalyticsOverview
from app.services import AnalyticsService

router = APIRouter()


@router.get("", response_model=AnalyticsOverview, summary="Dashboard analytics overview")
async def overview(
    user: CurrentUser, db: DB, days: int = Query(default=30, ge=1, le=365)
) -> AnalyticsOverview:
    return await AnalyticsService(db).overview(user.id, days=days)
