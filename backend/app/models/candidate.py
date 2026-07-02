"""Candidate and related public-profile models.

A ``Candidate`` is the canonical, de-duplicated representation of a person
assembled from one or more public ``CandidateSource`` records. Only publicly
available information is stored.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.db.types import JSONB, Vector
from app.models.enums import Seniority, SourceType

if TYPE_CHECKING:
    from app.models.interaction import Note, SavedCandidate
    from app.models.search import SearchResult


class Candidate(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "candidates"

    # ---- Identity ----
    full_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    headline: Mapped[str | None] = mapped_column(String(512))
    company: Mapped[str | None] = mapped_column(String(255), index=True)
    industry: Mapped[str | None] = mapped_column(String(255))
    seniority: Mapped[Seniority] = mapped_column(
        Enum(Seniority, native_enum=False, length=20), default=Seniority.UNKNOWN, nullable=False
    )
    years_experience: Mapped[int | None] = mapped_column(Integer)

    # ---- Location ----
    country: Mapped[str | None] = mapped_column(String(120), index=True)
    city: Mapped[str | None] = mapped_column(String(120))

    # ---- Public content ----
    bio: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(String(1024))
    public_email: Mapped[str | None] = mapped_column(String(320))

    # ---- Public links ----
    linkedin_url: Mapped[str | None] = mapped_column(String(1024))
    github_url: Mapped[str | None] = mapped_column(String(1024))
    portfolio_url: Mapped[str | None] = mapped_column(String(1024))
    website_url: Mapped[str | None] = mapped_column(String(1024))
    social_links: Mapped[dict] = mapped_column(JSONB, default=dict)

    # ---- Derived / structured ----
    technologies: Mapped[list] = mapped_column(JSONB, default=list)
    github_stats: Mapped[dict] = mapped_column(JSONB, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector())

    # ---- Provenance / dedup ----
    primary_source: Mapped[SourceType] = mapped_column(
        Enum(SourceType, native_enum=False, length=20), default=SourceType.OTHER, nullable=False
    )
    dedup_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    raw: Mapped[dict] = mapped_column(JSONB, default=dict)

    # ---- Relationships ----
    sources: Mapped[list[CandidateSource]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    skills: Mapped[list[CandidateSkill]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    experiences: Mapped[list[Experience]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    results: Mapped[list[SearchResult]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    saved_by: Mapped[list[SavedCandidate]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    notes: Mapped[list[Note]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Candidate {self.full_name!r}>"


class CandidateSource(UUIDPKMixin, TimestampMixin, Base):
    """A single public page/source from which candidate data was collected."""

    __tablename__ = "candidate_sources"
    __table_args__ = (UniqueConstraint("candidate_id", "url", name="candidate_source_url"),)

    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, native_enum=False, length=20), nullable=False
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512))
    snippet: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)

    candidate: Mapped[Candidate] = relationship(back_populates="sources")


class Skill(UUIDPKMixin, TimestampMixin, Base):
    """Normalized skill catalog entry."""

    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(80))

    candidates: Mapped[list[CandidateSkill]] = relationship(back_populates="skill")


class CandidateSkill(UUIDPKMixin, Base):
    """Association object linking candidates to skills with a weight."""

    __tablename__ = "candidate_skills"
    __table_args__ = (UniqueConstraint("candidate_id", "skill_id", name="candidate_skill"),)

    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    skill_id: Mapped[str] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    inferred_from: Mapped[str | None] = mapped_column(String(80))

    candidate: Mapped[Candidate] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship(back_populates="candidates")


class Experience(UUIDPKMixin, Base):
    """A public work-experience entry."""

    __tablename__ = "experiences"

    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    company: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[str | None] = mapped_column(String(32))  # public data is often coarse
    end_date: Mapped[str | None] = mapped_column(String(32))
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_months: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)

    candidate: Mapped[Candidate] = relationship(back_populates="experiences")
