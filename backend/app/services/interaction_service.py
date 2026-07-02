"""Saved candidates, notes, and history services."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories import (
    CandidateRepository,
    HistoryRepository,
    NoteRepository,
    SavedCandidateRepository,
)
from app.schemas import (
    CandidateRead,
    HistoryRead,
    NoteCreate,
    NoteRead,
    NoteUpdate,
    Page,
    PaginationParams,
    SavedCreate,
    SavedRead,
)


class SavedCandidateService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = SavedCandidateRepository(db)
        self.candidates = CandidateRepository(db)
        self.history = HistoryRepository(db)

    async def save(self, user_id: str, payload: SavedCreate) -> SavedRead:
        if await self.candidates.get(payload.candidate_id) is None:
            raise NotFoundError("Candidate not found.")
        if await self.repo.get_for_user(user_id, payload.candidate_id):
            raise ConflictError("Candidate is already saved.")
        saved = await self.repo.create(
            user_id=user_id, candidate_id=payload.candidate_id, tags=payload.tags
        )
        await self.history.record(
            user_id, "candidate.saved", entity_type="candidate", entity_id=payload.candidate_id
        )
        candidate = await self.candidates.get(payload.candidate_id)
        return SavedRead(
            id=saved.id,
            candidate=CandidateRead.model_validate(candidate),
            tags=saved.tags or [],
            created_at=saved.created_at,
        )

    async def unsave(self, user_id: str, candidate_id: str) -> None:
        saved = await self.repo.get_for_user(user_id, candidate_id)
        if saved is None:
            raise NotFoundError("Saved candidate not found.")
        await self.repo.delete(saved)
        await self.history.record(
            user_id, "candidate.unsaved", entity_type="candidate", entity_id=candidate_id
        )

    async def list(self, user_id: str, params: PaginationParams) -> Page[SavedRead]:
        items, total = await self.repo.list_for_user(
            user_id, offset=params.offset, limit=params.limit
        )
        return Page.create(
            items=[
                SavedRead(
                    id=s.id,
                    candidate=CandidateRead.model_validate(s.candidate),
                    tags=s.tags or [],
                    created_at=s.created_at,
                )
                for s in items
            ],
            total=total,
            params=params,
        )


class NoteService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = NoteRepository(db)
        self.candidates = CandidateRepository(db)

    async def create(self, user_id: str, payload: NoteCreate) -> NoteRead:
        if await self.candidates.get(payload.candidate_id) is None:
            raise NotFoundError("Candidate not found.")
        note = await self.repo.create(
            user_id=user_id, candidate_id=payload.candidate_id, body=payload.body
        )
        return NoteRead.model_validate(note)

    async def update(self, user_id: str, note_id: str, payload: NoteUpdate) -> NoteRead:
        note = await self.repo.get(note_id)
        if note is None or note.user_id != user_id:
            raise NotFoundError("Note not found.")
        note = await self.repo.update(note, body=payload.body)
        return NoteRead.model_validate(note)

    async def delete(self, user_id: str, note_id: str) -> None:
        note = await self.repo.get(note_id)
        if note is None or note.user_id != user_id:
            raise NotFoundError("Note not found.")
        await self.repo.delete(note)

    async def list_for_candidate(self, user_id: str, candidate_id: str) -> list[NoteRead]:
        notes = await self.repo.list_for_candidate(user_id, candidate_id)
        return [NoteRead.model_validate(n) for n in notes]


class HistoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = HistoryRepository(db)

    async def list(self, user_id: str, params: PaginationParams) -> Page[HistoryRead]:
        items, total = await self.repo.list_for_user(
            user_id, offset=params.offset, limit=params.limit
        )
        return Page.create(
            items=[HistoryRead.model_validate(h) for h in items], total=total, params=params
        )
