"""Pydantic schema package — public API of the validation layer."""

from app.schemas.analytics import AnalyticsOverview, CountPoint, TimeSeriesPoint
from app.schemas.candidate import (
    CandidateDetail,
    CandidateRead,
    CandidateSourceRead,
    ExperienceRead,
    ScoreBreakdown,
    SkillRead,
)
from app.schemas.common import Message, ORMModel, Page, PaginationParams
from app.schemas.interaction import (
    ExportCreate,
    ExportRead,
    HistoryRead,
    NoteCreate,
    NoteRead,
    NoteUpdate,
    SavedCreate,
    SavedRead,
)
from app.schemas.search import (
    GeneratedQuery,
    ParsedRequirement,
    SearchCreate,
    SearchDetail,
    SearchFilters,
    SearchRead,
    SearchResultRead,
)
from app.schemas.user import (
    LoginRequest,
    OAuthLoginRequest,
    RefreshRequest,
    Token,
    TokenPayload,
    UserCreate,
    UserRead,
    UserUpdate,
)

__all__ = [
    # common
    "ORMModel",
    "Page",
    "PaginationParams",
    "Message",
    # user/auth
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "Token",
    "TokenPayload",
    "LoginRequest",
    "RefreshRequest",
    "OAuthLoginRequest",
    # candidate
    "CandidateRead",
    "CandidateDetail",
    "CandidateSourceRead",
    "SkillRead",
    "ExperienceRead",
    "ScoreBreakdown",
    # search
    "ParsedRequirement",
    "GeneratedQuery",
    "SearchFilters",
    "SearchCreate",
    "SearchRead",
    "SearchDetail",
    "SearchResultRead",
    # interaction
    "SavedCreate",
    "SavedRead",
    "NoteCreate",
    "NoteUpdate",
    "NoteRead",
    "HistoryRead",
    "ExportCreate",
    "ExportRead",
    # analytics
    "AnalyticsOverview",
    "CountPoint",
    "TimeSeriesPoint",
]
