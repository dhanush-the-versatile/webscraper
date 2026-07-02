"""Candidate notes endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import DB, CurrentUser
from app.schemas import Message, NoteCreate, NoteRead, NoteUpdate
from app.services import NoteService

router = APIRouter()


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED,
             summary="Add a note to a candidate")
async def create_note(payload: NoteCreate, user: CurrentUser, db: DB) -> NoteRead:
    return await NoteService(db).create(user.id, payload)


@router.get("/candidate/{candidate_id}", response_model=list[NoteRead],
            summary="My notes for a candidate")
async def list_notes(candidate_id: str, user: CurrentUser, db: DB) -> list[NoteRead]:
    return await NoteService(db).list_for_candidate(user.id, candidate_id)


@router.patch("/{note_id}", response_model=NoteRead, summary="Edit a note")
async def update_note(note_id: str, payload: NoteUpdate, user: CurrentUser, db: DB) -> NoteRead:
    return await NoteService(db).update(user.id, note_id, payload)


@router.delete("/{note_id}", response_model=Message, summary="Delete a note")
async def delete_note(note_id: str, user: CurrentUser, db: DB) -> Message:
    await NoteService(db).delete(user.id, note_id)
    return Message(message="Note deleted.")
