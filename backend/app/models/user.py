"""User account model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import AuthProvider, UserRole

if TYPE_CHECKING:
    from app.models.interaction import Export, Note, SavedCandidate, SearchHistory
    from app.models.search import Search


class User(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20), default=UserRole.RECRUITER, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    auth_provider: Mapped[AuthProvider] = mapped_column(
        Enum(AuthProvider, native_enum=False, length=20),
        default=AuthProvider.LOCAL,
        nullable=False,
    )
    oauth_subject: Mapped[str | None] = mapped_column(String(255), index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1024))

    searches: Mapped[list[Search]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    saved_candidates: Mapped[list[SavedCandidate]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    notes: Mapped[list[Note]] = relationship(back_populates="user", cascade="all, delete-orphan")
    history: Mapped[list[SearchHistory]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    exports: Mapped[list[Export]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email} ({self.role.value})>"
