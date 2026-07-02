"""Candidate query service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models import Candidate
from app.repositories import CandidateRepository
from app.schemas import (
    CandidateDetail,
    CandidateRead,
    CandidateSourceRead,
    ExperienceRead,
    Page,
    PaginationParams,
    SearchFilters,
    SkillRead,
)


class CandidateService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CandidateRepository(db)

    async def get_detail(self, candidate_id: str) -> CandidateDetail:
        candidate = await self.repo.get_detail(candidate_id)
        if candidate is None:
            raise NotFoundError("Candidate not found.")
        # Validate the flat fields via CandidateRead, then attach the nested
        # collections explicitly (the ORM's skills are association objects).
        base = CandidateRead.model_validate(candidate).model_dump()
        return CandidateDetail(
            **base,
            bio=candidate.bio,
            github_stats=candidate.github_stats or {},
            extraction_confidence=candidate.extraction_confidence,
            created_at=candidate.created_at,
            skills=[SkillRead.from_link(link) for link in candidate.skills],
            experiences=[ExperienceRead.model_validate(e) for e in candidate.experiences],
            sources=[CandidateSourceRead.model_validate(s) for s in candidate.sources],
        )

    async def list_candidates(
        self,
        *,
        keyword: str | None = None,
        filters: SearchFilters | None = None,
        params: PaginationParams,
    ) -> Page[CandidateRead]:
        items, total = await self.repo.search(
            keyword=keyword,
            filters=filters.model_dump(exclude_none=True) if filters else None,
            offset=params.offset,
            limit=params.limit,
        )
        return Page.create(
            items=[CandidateRead.model_validate(c) for c in items], total=total, params=params
        )

    async def get_model(self, candidate_id: str) -> Candidate:
        candidate = await self.repo.get(candidate_id)
        if candidate is None:
            raise NotFoundError("Candidate not found.")
        return candidate
