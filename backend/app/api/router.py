"""Aggregate API v1 router.

Each feature exposes its own ``APIRouter``; they are composed here and mounted
under the configured API prefix by the application factory.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    auth,
    candidates,
    exports,
    health,
    notes,
    saved,
    searches,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(searches.router, prefix="/searches", tags=["searches"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
api_router.include_router(saved.router, prefix="/saved", tags=["saved"])
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
api_router.include_router(exports.router, prefix="/exports", tags=["exports"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
