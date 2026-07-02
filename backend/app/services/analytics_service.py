"""Analytics service: aggregates for the dashboard."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Candidate,
    CandidateSkill,
    SavedCandidate,
    Search,
    SearchResult,
    SearchStatus,
    Skill,
)
from app.schemas import AnalyticsOverview, CountPoint, TimeSeriesPoint


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def overview(self, user_id: str, *, days: int = 30) -> AnalyticsOverview:
        since = datetime.now(UTC) - timedelta(days=days)

        total_searches = await self._scalar(
            select(func.count()).select_from(Search).where(Search.user_id == user_id)
        )
        completed_searches = await self._scalar(
            select(func.count()).select_from(Search).where(
                Search.user_id == user_id, Search.status == SearchStatus.COMPLETED
            )
        )
        total_candidates = await self._scalar(select(func.count()).select_from(Candidate))
        total_saved = await self._scalar(
            select(func.count()).select_from(SavedCandidate).where(SavedCandidate.user_id == user_id)
        )
        avg_results = await self._scalar(
            select(func.coalesce(func.avg(Search.result_count), 0)).where(
                Search.user_id == user_id, Search.status == SearchStatus.COMPLETED
            ),
            as_float=True,
        )

        return AnalyticsOverview(
            total_searches=total_searches,
            completed_searches=completed_searches,
            total_candidates=total_candidates,
            total_saved=total_saved,
            avg_results_per_search=round(avg_results, 1),
            searches_over_time=await self._searches_over_time(user_id, since),
            top_skills=await self._top_skills(),
            top_countries=await self._top_countries(),
            top_technologies=await self._top_technologies(),
            candidates_by_source=await self._by_source(),
            score_distribution=await self._score_distribution(user_id),
        )

    # ------------------------------------------------------------------ #
    async def _scalar(self, stmt, *, as_float: bool = False):
        value = (await self.db.execute(stmt)).scalar_one()
        return float(value or 0) if as_float else int(value or 0)

    async def _searches_over_time(self, user_id: str, since: datetime) -> list[TimeSeriesPoint]:
        stmt = select(Search.created_at).where(
            Search.user_id == user_id, Search.created_at >= since
        )
        dates = [row[0] for row in (await self.db.execute(stmt)).all()]
        counter = Counter(d.date().isoformat() for d in dates if d)
        return [TimeSeriesPoint(date=k, value=v) for k, v in sorted(counter.items())]

    async def _top_skills(self, limit: int = 10) -> list[CountPoint]:
        stmt = (
            select(Skill.name, func.count(CandidateSkill.id).label("n"))
            .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
            .group_by(Skill.name)
            .order_by(func.count(CandidateSkill.id).desc())
            .limit(limit)
        )
        return [CountPoint(label=name, value=int(n)) for name, n in (await self.db.execute(stmt)).all()]

    async def _top_countries(self, limit: int = 10) -> list[CountPoint]:
        stmt = (
            select(Candidate.country, func.count(Candidate.id))
            .where(Candidate.country.is_not(None))
            .group_by(Candidate.country)
            .order_by(func.count(Candidate.id).desc())
            .limit(limit)
        )
        return [CountPoint(label=c or "Unknown", value=int(n)) for c, n in (await self.db.execute(stmt)).all()]

    async def _top_technologies(self, limit: int = 10) -> list[CountPoint]:
        # technologies is a JSON list; aggregate portably in Python.
        stmt = select(Candidate.technologies).where(Candidate.technologies.is_not(None))
        counter: Counter[str] = Counter()
        for (techs,) in (await self.db.execute(stmt)).all():
            for t in techs or []:
                counter[str(t).lower()] += 1
        return [CountPoint(label=k, value=v) for k, v in counter.most_common(limit)]

    async def _by_source(self) -> list[CountPoint]:
        stmt = select(Candidate.primary_source, func.count(Candidate.id)).group_by(
            Candidate.primary_source
        )
        return [
            CountPoint(label=src.value if hasattr(src, "value") else str(src), value=int(n))
            for src, n in (await self.db.execute(stmt)).all()
        ]

    async def _score_distribution(self, user_id: str) -> list[CountPoint]:
        stmt = (
            select(SearchResult.overall_score)
            .join(Search, Search.id == SearchResult.search_id)
            .where(Search.user_id == user_id)
        )
        buckets = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
        for (score,) in (await self.db.execute(stmt)).all():
            idx = min(4, int((score or 0) // 20))
            buckets[list(buckets)[idx]] += 1
        return [CountPoint(label=k, value=v) for k, v in buckets.items()]
