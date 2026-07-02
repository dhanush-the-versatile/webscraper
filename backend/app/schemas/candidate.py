"""Candidate-related read/write schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import Seniority, SourceType
from app.schemas.common import ORMModel


class SkillRead(ORMModel):
    name: str
    weight: float = 1.0

    @classmethod
    def from_link(cls, link) -> "SkillRead":
        """Build from a ``CandidateSkill`` association object."""
        return cls(name=link.skill.name, weight=link.weight)


class ExperienceRead(ORMModel):
    id: str
    company: str | None
    title: str | None
    location: str | None
    start_date: str | None
    end_date: str | None
    is_current: bool
    duration_months: int | None
    description: str | None


class CandidateSourceRead(ORMModel):
    id: str
    source_type: SourceType
    url: str
    title: str | None
    snippet: str | None
    fetched_at: datetime | None


class CandidateBase(ORMModel):
    id: str
    full_name: str
    headline: str | None
    company: str | None
    industry: str | None
    seniority: Seniority
    years_experience: int | None
    country: str | None
    city: str | None
    avatar_url: str | None
    linkedin_url: str | None
    github_url: str | None
    portfolio_url: str | None
    website_url: str | None
    technologies: list[str] = Field(default_factory=list)


class CandidateRead(CandidateBase):
    """Summary card representation."""

    public_email: str | None = None
    social_links: dict = Field(default_factory=dict)


class CandidateDetail(CandidateRead):
    """Full profile with nested public data."""

    bio: str | None = None
    github_stats: dict = Field(default_factory=dict)
    extraction_confidence: float = 0.0
    created_at: datetime
    skills: list[SkillRead] = Field(default_factory=list)
    experiences: list[ExperienceRead] = Field(default_factory=list)
    sources: list[CandidateSourceRead] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    """0-100 score components for a candidate within a search."""

    overall_score: float = 0.0
    skill_match: float = 0.0
    experience_match: float = 0.0
    technology_match: float = 0.0
    location_match: float = 0.0
    portfolio_score: float = 0.0
    github_activity_score: float = 0.0
    relevance_score: float = 0.0
