"""User interaction models: saved candidates, notes, history, exports, audit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.db.types import JSONB
from app.models.enums import ExportFormat, ExportStatus

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.user import User


class SavedCandidate(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "saved_candidates"
    __table_args__ = (UniqueConstraint("user_id", "candidate_id", name="user_candidate"),)

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    tags: Mapped[list] = mapped_column(JSONB, default=list)

    user: Mapped[User] = relationship(back_populates="saved_candidates")
    candidate: Mapped[Candidate] = relationship(back_populates="saved_by")


class Note(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "notes"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped[User] = relationship(back_populates="notes")
    candidate: Mapped[Candidate] = relationship(back_populates="notes")


class SearchHistory(UUIDPKMixin, TimestampMixin, Base):
    """Lightweight activity log of user actions (search views, exports, etc.)."""

    __tablename__ = "search_history"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)

    user: Mapped[User] = relationship(back_populates="history")


class Export(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "exports"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    search_id: Mapped[str | None] = mapped_column(
        ForeignKey("searches.id", ondelete="SET NULL"), index=True
    )
    format: Mapped[ExportFormat] = mapped_column(
        Enum(ExportFormat, native_enum=False, length=10), nullable=False
    )
    status: Mapped[ExportStatus] = mapped_column(
        Enum(ExportStatus, native_enum=False, length=20),
        default=ExportStatus.PENDING,
        nullable=False,
    )
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    file_path: Mapped[str | None] = mapped_column(String(1024))
    error: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="exports")


class AuditLog(UUIDPKMixin, TimestampMixin, Base):
    """Immutable security/audit trail."""

    __tablename__ = "audit_logs"

    actor_user_id: Mapped[str | None] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
