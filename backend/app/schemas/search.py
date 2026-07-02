"""Search request/response schemas and the AI requirement structures."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import SearchStatus, SourceType
from app.schemas.candidate import CandidateRead, ScoreBreakdown
from app.schemas.common import ORMModel


class ParsedRequirement(BaseModel):
    """Structured requirement extracted from a natural-language query.

    Shared between the API layer and the AI understanding module so the same
    contract is used end-to-end.
    """

    job_titles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    seniority: str | None = None
    min_years_experience: int | None = None
    max_years_experience: int | None = None
    countries: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    employment_type: str | None = None  # full-time | freelance | contract | ...
    remote: bool | None = None

    def all_skills(self) -> list[str]:
        """Union of skills/technologies/frameworks/languages, de-duplicated."""
        seen: dict[str, None] = {}
        for group in (
            self.skills,
            self.technologies,
            self.frameworks,
            self.programming_languages,
        ):
            for item in group:
                seen.setdefault(item.strip().lower(), None)
        return list(seen.keys())


class GeneratedQuery(BaseModel):
    """A single optimized search-engine query bound to a source."""

    query: str
    source: SourceType = SourceType.SEARCH_ENGINE
    rationale: str | None = None


class SearchFilters(BaseModel):
    """Optional structured filters applied on top of a search."""

    skills: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    min_years_experience: int | None = None
    min_score: float | None = Field(default=None, ge=0, le=100)


class SearchCreate(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    filters: SearchFilters | None = None
    max_results: int = Field(default=30, ge=1, le=100)


class SearchRead(ORMModel):
    id: str
    raw_query: str
    status: SearchStatus
    parsed_requirement: dict = Field(default_factory=dict)
    generated_queries: list = Field(default_factory=list)
    filters: dict = Field(default_factory=dict)
    result_count: int
    error: str | None
    created_at: datetime
    completed_at: datetime | None


class SearchResultRead(ORMModel):
    """A ranked candidate within a search."""

    id: str
    rank: int
    candidate: CandidateRead
    scores: ScoreBreakdown
    summary: str | None
    explanation: str | None
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)

    @classmethod
    def from_orm_result(cls, result) -> "SearchResultRead":
        return cls(
            id=result.id,
            rank=result.rank,
            candidate=CandidateRead.model_validate(result.candidate),
            scores=ScoreBreakdown(
                overall_score=result.overall_score,
                skill_match=result.skill_match,
                experience_match=result.experience_match,
                technology_match=result.technology_match,
                location_match=result.location_match,
                portfolio_score=result.portfolio_score,
                github_activity_score=result.github_activity_score,
                relevance_score=result.relevance_score,
            ),
            summary=result.summary,
            explanation=result.explanation,
            matched_skills=result.matched_skills or [],
            missing_skills=result.missing_skills or [],
        )


class SearchDetail(SearchRead):
    results: list[SearchResultRead] = Field(default_factory=list)
