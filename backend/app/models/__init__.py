"""ORM models package.

Importing this package registers every model on ``Base.metadata`` which is
what Alembic autogenerate and ``create_all`` rely on.
"""

from app.db.base import Base
from app.models.candidate import (
    Candidate,
    CandidateSkill,
    CandidateSource,
    Experience,
    Skill,
)
from app.models.enums import (
    AuthProvider,
    ExportFormat,
    ExportStatus,
    SearchStatus,
    Seniority,
    SourceType,
    UserRole,
)
from app.models.interaction import (
    AuditLog,
    Export,
    Note,
    SavedCandidate,
    SearchHistory,
)
from app.models.search import Search, SearchResult
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Search",
    "SearchResult",
    "Candidate",
    "CandidateSource",
    "Skill",
    "CandidateSkill",
    "Experience",
    "SavedCandidate",
    "Note",
    "SearchHistory",
    "Export",
    "AuditLog",
    # enums
    "UserRole",
    "AuthProvider",
    "SearchStatus",
    "SourceType",
    "Seniority",
    "ExportFormat",
    "ExportStatus",
]
