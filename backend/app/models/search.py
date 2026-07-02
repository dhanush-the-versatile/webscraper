"""Search job and per-candidate ranked result models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.db.types import JSONB
from app.models.enums import SearchStatus

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.user import User


class Search(UUIDPKMixin, TimestampMixin, Base):
    """A natural-language talent search and its processing state."""

    __tablename__ = "searches"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    raw_query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SearchStatus] = mapped_column(
        Enum(SearchStatus, native_enum=False, length=20),
        default=SearchStatus.PENDING,
        nullable=False,
        index=True,
    )

    # AI-derived artefacts
    parsed_requirement: Mapped[dict] = mapped_column(JSONB, default=dict)
    generated_queries: Mapped[list] = mapped_column(JSONB, default=list)
    filters: Mapped[dict] = mapped_column(JSONB, default=dict)

    result_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="searches")
    results: Mapped[list[SearchResult]] = relationship(
        back_populates="search", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Search {self.id} status={self.status.value}>"


class SearchResult(UUIDPKMixin, TimestampMixin, Base):
    """A candidate's ranking within a specific search (normalized join)."""

    __tablename__ = "search_results"
    __table_args__ = (
        UniqueConstraint("search_id", "candidate_id", name="search_candidate"),
    )

    search_id: Mapped[str] = mapped_column(
        ForeignKey("searches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )

    rank: Mapped[int] = mapped_column(Integer, default=0, index=True)

    # ---- Score breakdown (0-100) ----
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    skill_match: Mapped[float] = mapped_column(Float, default=0.0)
    experience_match: Mapped[float] = mapped_column(Float, default=0.0)
    technology_match: Mapped[float] = mapped_column(Float, default=0.0)
    location_match: Mapped[float] = mapped_column(Float, default=0.0)
    portfolio_score: Mapped[float] = mapped_column(Float, default=0.0)
    github_activity_score: Mapped[float] = mapped_column(Float, default=0.0)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)

    # ---- AI narrative ----
    summary: Mapped[str | None] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)
    matched_skills: Mapped[list] = mapped_column(JSONB, default=list)
    missing_skills: Mapped[list] = mapped_column(JSONB, default=list)

    search: Mapped[Search] = relationship(back_populates="results")
    candidate: Mapped[Candidate] = relationship(back_populates="results")
