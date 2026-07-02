"""SQLAlchemy declarative base and shared column mixins."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# A consistent naming convention keeps Alembic autogenerate deterministic.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _uuid_str() -> str:
    return uuid.uuid4().hex


class UUIDPKMixin:
    """Primary key as a 32-char hex UUID (portable across Postgres/SQLite)."""

    id: Mapped[str] = mapped_column(primary_key=True, default=_uuid_str)


class TimestampMixin:
    """created_at / updated_at columns maintained by the DB and ORM."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
