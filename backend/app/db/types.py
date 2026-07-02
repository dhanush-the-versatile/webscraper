"""Dialect-aware column types.

``Vector`` uses the native ``pgvector`` type on PostgreSQL for real
similarity search, and transparently falls back to a JSON-encoded array on
other dialects (e.g. SQLite in the test suite) so the same models work
everywhere.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import JSON, Text
from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB
from sqlalchemy.types import TypeDecorator

from app.core.config import settings

try:  # pragma: no cover - exercised only when pgvector is installed
    from pgvector.sqlalchemy import Vector as _PGVector

    _HAS_PGVECTOR = True
except Exception:  # pragma: no cover
    _PGVector = None  # type: ignore[assignment]
    _HAS_PGVECTOR = False

# JSONB on PostgreSQL, generic JSON elsewhere (keeps SQLite tests working).
JSONB = JSON().with_variant(_PG_JSONB, "postgresql")


class Vector(TypeDecorator):
    """Embedding vector column with a portable fallback."""

    impl = Text
    cache_ok = True

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim or settings.EMBEDDING_DIM
        super().__init__()

    class comparator_factory(TypeDecorator.Comparator):
        """Expose pgvector operators (valid on PostgreSQL only)."""

        def cosine_distance(self, other: Any):
            from sqlalchemy import Float

            return self.op("<=>", return_type=Float)(other)

        def l2_distance(self, other: Any):
            from sqlalchemy import Float

            return self.op("<->", return_type=Float)(other)

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql" and _HAS_PGVECTOR:
            return dialect.type_descriptor(_PGVector(self.dim))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql" and _HAS_PGVECTOR:
            return value  # pgvector handles list[float] natively
        return json.dumps(list(value))

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql" and _HAS_PGVECTOR:
            return list(value)
        return json.loads(value)
