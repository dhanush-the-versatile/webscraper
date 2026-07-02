"""Search dispatch: Celery when the broker is reachable, inline otherwise.

Keeps the API responsive in every environment: full docker-compose runs get
real background workers; a bare `uvicorn` dev session still works because the
pipeline falls back to a FastAPI background task.
"""

from __future__ import annotations

import time

from fastapi import BackgroundTasks

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("tasks.dispatch")

_BROKER_PROBE_TTL = 30.0
_broker_state: dict = {"checked_at": 0.0, "up": False}


def _broker_available() -> bool:
    now = time.monotonic()
    if now - _broker_state["checked_at"] < _BROKER_PROBE_TTL:
        return _broker_state["up"]
    up = False
    try:
        import redis

        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        up = bool(client.ping())
        client.close()
    except Exception:
        up = False
    _broker_state.update(checked_at=now, up=up)
    return up


def dispatch_search(
    background_tasks: BackgroundTasks, search_id: str, max_results: int = 30
) -> str:
    """Queue the search pipeline; returns the execution mode used."""
    if _broker_available():
        try:
            from app.tasks.search_tasks import run_search_task

            run_search_task.delay(search_id, max_results)
            logger.info("search_dispatched", mode="celery", search_id=search_id)
            return "celery"
        except Exception as exc:  # broker flapped between probe and publish
            logger.warning("celery_dispatch_failed", error=str(exc))

    from app.tasks.search_tasks import run_search_sync

    background_tasks.add_task(run_search_sync, search_id, max_results)
    logger.info("search_dispatched", mode="inline", search_id=search_id)
    return "inline"
