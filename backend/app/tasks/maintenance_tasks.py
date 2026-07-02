"""Periodic maintenance tasks (cache refresh, cleanup)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.core.logging import configure_logging, get_logger
from app.tasks.celery_app import celery_app

logger = get_logger("tasks.maintenance")


async def _refresh_cache_async() -> int:
    """Re-embed candidates missing embeddings (e.g. after config changes)."""
    from app.ai import embedding_service
    from app.db.session import AsyncSessionLocal
    from app.models import Candidate

    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(Candidate).where(Candidate.embedding.is_(None)).limit(200)
            )
        ).scalars().all()
        for candidate in rows:
            candidate.embedding = await embedding_service.embed(
                embedding_service.candidate_document(candidate)
            )
        await session.commit()
        return len(rows)


async def _purge_expired_async() -> int:
    """Remove export records older than 30 days and stale failed searches."""
    from app.db.session import AsyncSessionLocal
    from app.models import Export, Search, SearchStatus

    cutoff = datetime.now(UTC) - timedelta(days=30)
    async with AsyncSessionLocal() as session:
        exports = await session.execute(delete(Export).where(Export.created_at < cutoff))
        stale = await session.execute(
            delete(Search).where(
                Search.status == SearchStatus.FAILED, Search.created_at < cutoff
            )
        )
        await session.commit()
        return (exports.rowcount or 0) + (stale.rowcount or 0)


@celery_app.task(name="maintenance.refresh_cache")
def refresh_cache() -> int:
    configure_logging()
    count = asyncio.run(_refresh_cache_async())
    logger.info("cache_refreshed", candidates=count)
    return count


@celery_app.task(name="maintenance.purge_expired")
def purge_expired() -> int:
    configure_logging()
    count = asyncio.run(_purge_expired_async())
    logger.info("expired_purged", rows=count)
    return count
