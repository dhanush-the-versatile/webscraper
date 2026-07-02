"""Search and search-result repositories."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Search, SearchResult, SearchStatus
from app.repositories.base import BaseRepository


class SearchRepository(BaseRepository[Search]):
    model = Search

    async def list_for_user(
        self, user_id: str, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[Search], int]:
        total = await self.count(user_id=user_id)
        items = await self.list(
            user_id=user_id, offset=offset, limit=limit, order_by=Search.created_at.desc()
        )
        return items, total

    async def get_with_results(self, search_id: str) -> Search | None:
        stmt = (
            select(Search)
            .where(Search.id == search_id)
            .options(
                selectinload(Search.results).selectinload(SearchResult.candidate)
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def set_status(
        self, search: Search, status: SearchStatus, *, error: str | None = None
    ) -> Search:
        return await self.update(search, status=status, error=error)


class SearchResultRepository(BaseRepository[SearchResult]):
    model = SearchResult

    async def list_for_search(
        self,
        search_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
        min_score: float | None = None,
    ) -> tuple[list[SearchResult], int]:
        stmt = (
            select(SearchResult)
            .where(SearchResult.search_id == search_id)
            .options(selectinload(SearchResult.candidate))
        )
        if min_score is not None:
            stmt = stmt.where(SearchResult.overall_score >= min_score)

        from sqlalchemy import func

        total = int(
            (
                await self.db.execute(
                    select(func.count()).select_from(stmt.subquery())
                )
            ).scalar_one()
        )
        stmt = stmt.order_by(SearchResult.rank.asc()).offset(offset).limit(limit)
        items = list((await self.db.execute(stmt)).scalars().all())
        return items, total

    async def get_for_candidate(
        self, search_id: str, candidate_id: str
    ) -> SearchResult | None:
        return await self.get_by(search_id=search_id, candidate_id=candidate_id)
