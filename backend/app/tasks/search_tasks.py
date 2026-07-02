"""Celery tasks for the search pipeline (collection, extraction, ranking)."""

from __future__ import annotations

import asyncio

from app.core.logging import configure_logging, get_logger
from app.tasks.celery_app import celery_app

logger = get_logger("tasks.search")


async def _run_search_async(search_id: str, max_results: int) -> int:
    """Execute the full pipeline with a task-local engine.

    A fresh engine is created inside this coroutine's event loop: the task may
    run on a Celery worker or in a FastAPI threadpool, and an asyncpg pool
    must never be shared across event loops.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.core.config import settings
    from app.services import SearchService

    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with maker() as session:
            service = SearchService(session)
            search = await service.execute(search_id, max_results=max_results)
            return search.result_count or 0
    finally:
        await engine.dispose()


def run_search_sync(search_id: str, max_results: int = 30) -> int:
    """Sync entrypoint shared by Celery and the inline fallback."""
    return asyncio.run(_run_search_async(search_id, max_results))


@celery_app.task(
    name="search.run",
    bind=True,
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def run_search_task(self, search_id: str, max_results: int = 30) -> int:
    configure_logging()
    logger.info("worker_search_started", search_id=search_id)
    count = run_search_sync(search_id, max_results)
    logger.info("worker_search_finished", search_id=search_id, results=count)
    return count
