"""Celery tasks for the search pipeline (collection, extraction, ranking)."""

from __future__ import annotations

import asyncio

from app.core.logging import configure_logging, get_logger
from app.tasks.celery_app import celery_app

logger = get_logger("tasks.search")


async def _run_search_async(search_id: str, max_results: int) -> int:
    """Execute the full pipeline in a worker-local session."""
    # imported lazily so the worker controls event-loop/engine creation
    from app.db.session import AsyncSessionLocal
    from app.services import SearchService

    async with AsyncSessionLocal() as session:
        service = SearchService(session)
        search = await service.execute(search_id, max_results=max_results)
        return search.result_count or 0


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
