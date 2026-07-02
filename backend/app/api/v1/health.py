"""Health and readiness probes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict:
    return {"status": "ok", "service": settings.PROJECT_NAME, "environment": settings.ENVIRONMENT}


@router.get("/ready", summary="Readiness probe (checks DB connectivity)")
async def ready(db: AsyncSession = Depends(get_db)) -> dict:
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok}
