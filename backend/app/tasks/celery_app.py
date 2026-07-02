"""Celery application configuration."""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "talent_discovery",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.search_tasks", "app.tasks.maintenance_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=15 * 60,
    task_time_limit=20 * 60,
    broker_connection_retry_on_startup=True,
    result_expires=24 * 3600,
    task_routes={
        "search.*": {"queue": "search"},
        "maintenance.*": {"queue": "maintenance"},
    },
    task_default_queue="search",
    beat_schedule={
        "refresh-stale-caches": {
            "task": "maintenance.refresh_cache",
            "schedule": 6 * 3600.0,
        },
        "purge-old-exports": {
            "task": "maintenance.purge_expired",
            "schedule": 24 * 3600.0,
        },
    },
)
