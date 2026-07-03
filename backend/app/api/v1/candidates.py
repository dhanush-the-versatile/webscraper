"""Candidate endpoints: browse the talent pool, fetch full profiles."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from app.api.deps import DB, CurrentUser, Pagination
from app.schemas import CandidateDetail, CandidateRead, Page, SearchFilters
from app.services import CandidateService

router = APIRouter()


@router.get("", response_model=Page[CandidateRead],
            summary="Browse/filter collected candidates (keyword, semantic, or hybrid)")
async def list_candidates(
    user: CurrentUser,
    db: DB,
    params: Pagination,
    q: str | None = Query(default=None, max_length=200, description="Search query"),
    mode: Literal["keyword", "semantic", "hybrid"] = Query(
        default="keyword",
        description="keyword = SQL match; semantic = vector similarity; hybrid = blend",
    ),
    skills: list[str] = Query(default=[]),
    countries: list[str] = Query(default=[]),
    cities: list[str] = Query(default=[]),
    companies: list[str] = Query(default=[]),
    industries: list[str] = Query(default=[]),
    technologies: list[str] = Query(default=[]),
    min_years_experience: int | None = Query(default=None, ge=0, le=60),
) -> Page[CandidateRead]:
    filters = SearchFilters(
        skills=skills,
        countries=countries,
        cities=cities,
        companies=companies,
        industries=industries,
        technologies=technologies,
        min_years_experience=min_years_experience,
    )
    return await CandidateService(db).list_candidates(
        keyword=q, filters=filters, params=params, mode=mode
    )


@router.get("/{candidate_id}", response_model=CandidateDetail,
            summary="Full public profile for a candidate")
async def get_candidate(candidate_id: str, user: CurrentUser, db: DB) -> CandidateDetail:
    return await CandidateService(db).get_detail(candidate_id)
