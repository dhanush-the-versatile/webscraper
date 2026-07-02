"""Repository layer — persistence access behind a stable interface."""

from app.repositories.base import BaseRepository
from app.repositories.candidate_repo import (
    CandidateRepository,
    compute_dedup_hash,
    slugify,
)
from app.repositories.interaction_repo import (
    AuditRepository,
    ExportRepository,
    HistoryRepository,
    NoteRepository,
    SavedCandidateRepository,
)
from app.repositories.search_repo import SearchRepository, SearchResultRepository
from app.repositories.user_repo import UserRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "CandidateRepository",
    "SearchRepository",
    "SearchResultRepository",
    "SavedCandidateRepository",
    "NoteRepository",
    "HistoryRepository",
    "ExportRepository",
    "AuditRepository",
    "compute_dedup_hash",
    "slugify",
]
