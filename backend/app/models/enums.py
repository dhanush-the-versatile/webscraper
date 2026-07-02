"""Enumerations shared across the domain model."""

from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    RECRUITER = "recruiter"
    VIEWER = "viewer"


class AuthProvider(str, enum.Enum):
    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"


class SearchStatus(str, enum.Enum):
    PENDING = "pending"
    UNDERSTANDING = "understanding"
    SEARCHING = "searching"
    COLLECTING = "collecting"
    RANKING = "ranking"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceType(str, enum.Enum):
    LINKEDIN = "linkedin"
    GITHUB = "github"
    STACKOVERFLOW = "stackoverflow"
    KAGGLE = "kaggle"
    MEDIUM = "medium"
    DEVTO = "devto"
    BEHANCE = "behance"
    DRIBBBLE = "dribbble"
    PORTFOLIO = "portfolio"
    COMPANY = "company"
    RESEARCH = "research"
    SEARCH_ENGINE = "search_engine"
    OTHER = "other"


class Seniority(str, enum.Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"
    EXECUTIVE = "executive"
    UNKNOWN = "unknown"


class ExportFormat(str, enum.Enum):
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"
    JSON = "json"


class ExportStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
