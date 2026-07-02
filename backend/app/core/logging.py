"""Structured logging configuration built on ``structlog``.

Emits human-friendly console logs in development and JSON in production
(controlled by ``LOG_JSON``). A per-request ``request_id`` is bound via a
context variable so every log line within a request is correlated.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

import structlog

from app.core.config import settings

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def _add_request_id(_: object, __: str, event_dict: dict) -> dict:
    rid = request_id_ctx.get()
    if rid is not None:
        event_dict["request_id"] = rid
    return event_dict


def configure_logging() -> None:
    """Configure the stdlib + structlog logging pipeline. Idempotent."""
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_request_id,
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.LOG_JSON:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.LOG_LEVEL)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging (uvicorn, sqlalchemy) through the same level.
    logging.basicConfig(
        format="%(message)s",
        level=logging.getLevelName(settings.LOG_LEVEL),
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    for noisy in ("uvicorn.access", "sqlalchemy.engine.Engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)
