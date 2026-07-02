"""Schemas for saved candidates, notes, history, and exports."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ExportFormat, ExportStatus
from app.schemas.candidate import CandidateRead
from app.schemas.common import ORMModel


# ---- Saved candidates ----
class SavedCreate(BaseModel):
    candidate_id: str
    tags: list[str] = Field(default_factory=list)


class SavedRead(ORMModel):
    id: str
    candidate: CandidateRead
    tags: list[str] = Field(default_factory=list)
    created_at: datetime


# ---- Notes ----
class NoteCreate(BaseModel):
    candidate_id: str
    body: str = Field(min_length=1, max_length=5000)


class NoteUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class NoteRead(ORMModel):
    id: str
    candidate_id: str
    body: str
    created_at: datetime
    updated_at: datetime


# ---- History ----
class HistoryRead(ORMModel):
    id: str
    action: str
    entity_type: str | None
    entity_id: str | None
    meta: dict = Field(default_factory=dict)
    created_at: datetime


# ---- Exports ----
class ExportCreate(BaseModel):
    search_id: str
    format: ExportFormat = ExportFormat.CSV


class ExportRead(ORMModel):
    id: str
    search_id: str | None
    format: ExportFormat
    status: ExportStatus
    row_count: int
    file_path: str | None
    error: str | None
    created_at: datetime
