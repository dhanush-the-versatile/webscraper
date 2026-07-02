"""Saved-candidates endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import DB, CurrentUser, Pagination
from app.schemas import Message, Page, SavedCreate, SavedRead
from app.services import SavedCandidateService

router = APIRouter()


@router.get("", response_model=Page[SavedRead], summary="List saved candidates")
async def list_saved(user: CurrentUser, db: DB, params: Pagination) -> Page[SavedRead]:
    return await SavedCandidateService(db).list(user.id, params)


@router.post("", response_model=SavedRead, status_code=status.HTTP_201_CREATED,
             summary="Save a candidate")
async def save_candidate(payload: SavedCreate, user: CurrentUser, db: DB) -> SavedRead:
    return await SavedCandidateService(db).save(user.id, payload)


@router.delete("/{candidate_id}", response_model=Message, summary="Unsave a candidate")
async def unsave_candidate(candidate_id: str, user: CurrentUser, db: DB) -> Message:
    await SavedCandidateService(db).unsave(user.id, candidate_id)
    return Message(message="Candidate removed from saved list.")
