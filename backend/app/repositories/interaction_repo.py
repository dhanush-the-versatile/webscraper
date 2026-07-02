"""Repositories for saved candidates, notes, history, exports, and audit."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import (
    AuditLog,
    Export,
    Note,
    SavedCandidate,
    SearchHistory,
)
from app.repositories.base import BaseRepository


class SavedCandidateRepository(BaseRepository[SavedCandidate]):
    model = SavedCandidate

    async def list_for_user(
        self, user_id: str, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[SavedCandidate], int]:
        total = await self.count(user_id=user_id)
        stmt = (
            select(SavedCandidate)
            .where(SavedCandidate.user_id == user_id)
            .options(selectinload(SavedCandidate.candidate))
            .order_by(SavedCandidate.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        return items, total

    async def get_for_user(self, user_id: str, candidate_id: str) -> SavedCandidate | None:
        return await self.get_by(user_id=user_id, candidate_id=candidate_id)


class NoteRepository(BaseRepository[Note]):
    model = Note

    async def list_for_candidate(
        self, user_id: str, candidate_id: str, *, offset: int = 0, limit: int = 50
    ) -> list[Note]:
        return await self.list(
            user_id=user_id,
            candidate_id=candidate_id,
            offset=offset,
            limit=limit,
            order_by=Note.created_at.desc(),
        )


class HistoryRepository(BaseRepository[SearchHistory]):
    model = SearchHistory

    async def record(
        self,
        user_id: str,
        action: str,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        meta: dict | None = None,
    ) -> SearchHistory:
        return await self.create(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            meta=meta or {},
        )

    async def list_for_user(
        self, user_id: str, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[SearchHistory], int]:
        total = await self.count(user_id=user_id)
        items = await self.list(
            user_id=user_id,
            offset=offset,
            limit=limit,
            order_by=SearchHistory.created_at.desc(),
        )
        return items, total


class ExportRepository(BaseRepository[Export]):
    model = Export

    async def list_for_user(
        self, user_id: str, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[Export], int]:
        total = await self.count(user_id=user_id)
        items = await self.list(
            user_id=user_id, offset=offset, limit=limit, order_by=Export.created_at.desc()
        )
        return items, total


class AuditRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def record(
        self,
        action: str,
        *,
        actor_user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        meta: dict | None = None,
    ) -> AuditLog:
        return await self.create(
            action=action,
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            meta=meta or {},
        )
