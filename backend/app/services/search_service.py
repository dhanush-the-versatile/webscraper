"""Search orchestration service.

Drives the full talent-search lifecycle for one search record:

    create → understand → generate queries → collect (public sources)
           → persist/dedupe candidates → rank (deterministic + semantic)
           → store ranked results → complete

The LangGraph pipeline handles stage flow; this service supplies the I/O
stages (collection + persistence/ranking) and keeps DB state in sync so the
frontend can poll progress.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import build_search_graph, cosine_similarity, embedding_service, generate_narratives
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models import Search, SearchStatus, Seniority, SourceType
from app.repositories import (
    CandidateRepository,
    HistoryRepository,
    SearchRepository,
    SearchResultRepository,
    compute_dedup_hash,
)
from app.schemas import (
    GeneratedQuery,
    Page,
    PaginationParams,
    ParsedRequirement,
    SearchCreate,
    SearchDetail,
    SearchRead,
    SearchResultRead,
)
from app.scraping import collection_pipeline
from app.services.ranking_service import RankingInput, RankingService

logger = get_logger("search.service")


class SearchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.searches = SearchRepository(db)
        self.results = SearchResultRepository(db)
        self.candidates = CandidateRepository(db)
        self.history = HistoryRepository(db)
        self.ranking = RankingService()

    # ------------------------------------------------------------------ #
    # CRUD / reads
    # ------------------------------------------------------------------ #
    async def create_search(self, user_id: str, payload: SearchCreate) -> Search:
        search = await self.searches.create(
            user_id=user_id,
            raw_query=payload.query.strip(),
            status=SearchStatus.PENDING,
            filters=payload.filters.model_dump(exclude_none=True) if payload.filters else {},
        )
        await self.history.record(
            user_id, "search.created", entity_type="search", entity_id=search.id,
            meta={"query": payload.query[:200]},
        )
        return search

    async def get_search(self, user_id: str, search_id: str) -> Search:
        search = await self.searches.get(search_id)
        if search is None or search.user_id != user_id:
            raise NotFoundError("Search not found.")
        return search

    async def get_detail(
        self, user_id: str, search_id: str, *, params: PaginationParams, min_score: float | None = None
    ) -> tuple[SearchDetail, int]:
        search = await self.get_search(user_id, search_id)
        results, total = await self.results.list_for_search(
            search_id, offset=params.offset, limit=params.limit, min_score=min_score
        )
        # Build from SearchRead first: validating SearchDetail directly against the
        # ORM object would touch the lazy `results` relationship outside a greenlet.
        detail = SearchDetail(
            **SearchRead.model_validate(search).model_dump(),
            results=[SearchResultRead.from_orm_result(r) for r in results],
        )
        return detail, total

    async def list_searches(
        self, user_id: str, params: PaginationParams
    ) -> Page[SearchRead]:
        items, total = await self.searches.list_for_user(
            user_id, offset=params.offset, limit=params.limit
        )
        return Page.create(
            items=[SearchRead.model_validate(s) for s in items], total=total, params=params
        )

    # ------------------------------------------------------------------ #
    # Pipeline execution
    # ------------------------------------------------------------------ #
    async def execute(self, search_id: str, *, max_results: int = 30) -> Search:
        """Run the full pipeline for an existing search record."""
        search = await self.searches.get(search_id)
        if search is None:
            raise NotFoundError("Search not found.")

        async def on_stage(stage: str, meta: dict[str, Any]) -> None:
            status = SearchStatus(stage) if stage in SearchStatus._value2member_map_ else None
            if status is not None:
                await self.searches.update(search, status=status)
            if requirement := meta.get("requirement"):
                await self.searches.update(search, parsed_requirement=requirement)
            if queries := meta.get("queries"):
                await self.searches.update(search, generated_queries=queries)
            await self.db.commit()

        async def collector(
            queries: list[GeneratedQuery], req: ParsedRequirement, limit: int
        ) -> list[dict[str, Any]]:
            return await collection_pipeline.collect(queries, req, max_results=limit)

        async def ranker(
            req: ParsedRequirement, profiles: list[dict[str, Any]]
        ) -> list[dict[str, Any]]:
            return await self._persist_and_rank(search, req, profiles)

        graph = build_search_graph(collector, ranker, on_stage)
        try:
            state = await graph.ainvoke(
                {"query": search.raw_query, "max_results": max_results}
            )
            await self.searches.update(
                search,
                status=SearchStatus.COMPLETED,
                result_count=len(state.get("results") or []),
                completed_at=datetime.now(UTC),
                error=None,
            )
            logger.info("search_completed", search_id=search.id,
                        results=len(state.get("results") or []))
        except Exception as exc:
            logger.exception("search_failed", search_id=search.id)
            await self.searches.update(
                search, status=SearchStatus.FAILED, error=str(exc)[:2000]
            )
        await self.db.commit()
        return search

    # ------------------------------------------------------------------ #
    async def _persist_and_rank(
        self, search: Search, req: ParsedRequirement, profiles: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Store collected profiles as candidates and rank them for this search."""
        requirement_embedding = await embedding_service.embed(
            embedding_service.requirement_document(req)
        )
        ranked: list[dict[str, Any]] = []

        for profile in profiles:
            source_info = profile.pop("_source", {})
            if not profile.get("full_name"):
                continue

            dedup = compute_dedup_hash(
                full_name=profile["full_name"],
                linkedin_url=profile.get("linkedin_url"),
                github_url=profile.get("github_url"),
                public_email=profile.get("public_email"),
                company=profile.get("company"),
            )
            seniority = Seniority.UNKNOWN
            if raw_seniority := profile.get("seniority"):
                try:
                    seniority = Seniority(str(raw_seniority).lower())
                except ValueError:
                    pass

            source_type = SourceType(source_info.get("type", "other"))
            candidate, _created = await self.candidates.upsert_by_hash(
                dedup,
                full_name=profile["full_name"],
                headline=profile.get("headline"),
                company=profile.get("company"),
                industry=profile.get("industry"),
                seniority=seniority,
                years_experience=profile.get("years_experience"),
                country=profile.get("country"),
                city=profile.get("city"),
                bio=profile.get("bio"),
                avatar_url=profile.get("avatar_url"),
                public_email=profile.get("public_email"),
                linkedin_url=profile.get("linkedin_url"),
                github_url=profile.get("github_url"),
                portfolio_url=profile.get("portfolio_url"),
                website_url=profile.get("website_url"),
                social_links=profile.get("social_links") or {},
                technologies=profile.get("technologies") or [],
                github_stats=profile.get("github_stats") or {},
                primary_source=source_type,
                extraction_confidence=profile.get("extraction_confidence", 0.0),
                raw={"sample": bool(source_info.get("meta", {}).get("is_sample"))},
            )

            skills = list(profile.get("skills") or []) + list(profile.get("technologies") or [])
            if skills:
                await self.candidates.set_skills(
                    candidate, skills[:25], inferred_from=source_type.value
                )
            if experiences := profile.get("experiences"):
                cleaned = [
                    {
                        "company": (e.get("company") or "")[:255] or None,
                        "title": (e.get("title") or "")[:255] or None,
                        "start_date": (str(e.get("start_date") or ""))[:32] or None,
                        "end_date": (str(e.get("end_date") or ""))[:32] or None,
                        "is_current": bool(e.get("is_current")),
                        "description": (e.get("description") or "")[:2000] or None,
                    }
                    for e in experiences[:10]
                    if isinstance(e, dict)
                ]
                if cleaned and not candidate.experiences:
                    await self.candidates.replace_experiences(candidate, cleaned)

            if source_url := source_info.get("url"):
                await self.candidates.add_source(
                    candidate,
                    url=source_url,
                    source_type=source_type,
                    title=(source_info.get("title") or "")[:512] or None,
                    snippet=(source_info.get("snippet") or "")[:2000] or None,
                    content=(source_info.get("content") or "")[:10000] or None,
                    fetched_at=datetime.now(UTC),
                    meta=source_info.get("meta") or {},
                )

            # semantic relevance via embeddings
            candidate_embedding = await embedding_service.embed(
                embedding_service.candidate_document(candidate)
            )
            candidate.embedding = candidate_embedding
            semantic = cosine_similarity(requirement_embedding, candidate_embedding)

            breakdown, matched, missing = self.ranking.score(
                req,
                RankingInput(
                    candidate=candidate,
                    candidate_skills=skills,
                    semantic_score=max(0.0, semantic) if any(candidate_embedding) else None,
                ),
            )
            summary, explanation = await generate_narratives(
                req, candidate, breakdown, matched, missing
            )
            ranked.append(
                {
                    "candidate_id": candidate.id,
                    "breakdown": breakdown,
                    "matched": matched,
                    "missing": missing,
                    "summary": summary,
                    "explanation": explanation,
                }
            )

        ranked.sort(key=lambda item: item["breakdown"].overall_score, reverse=True)

        for rank, item in enumerate(ranked, start=1):
            existing = await self.results.get_for_candidate(search.id, item["candidate_id"])
            fields = {
                "rank": rank,
                "overall_score": item["breakdown"].overall_score,
                "skill_match": item["breakdown"].skill_match,
                "experience_match": item["breakdown"].experience_match,
                "technology_match": item["breakdown"].technology_match,
                "location_match": item["breakdown"].location_match,
                "portfolio_score": item["breakdown"].portfolio_score,
                "github_activity_score": item["breakdown"].github_activity_score,
                "relevance_score": item["breakdown"].relevance_score,
                "summary": item["summary"],
                "explanation": item["explanation"],
                "matched_skills": item["matched"],
                "missing_skills": item["missing"],
            }
            if existing is None:
                await self.results.create(
                    search_id=search.id, candidate_id=item["candidate_id"], **fields
                )
            else:
                await self.results.update(existing, **fields)

        await self.db.commit()
        return ranked
