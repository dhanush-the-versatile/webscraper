"""FastAPI dependencies: authentication, RBAC, and pagination."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, PermissionError
from app.core.security import JWTError, decode_token
from app.db.session import get_db
from app.models import User, UserRole
from app.repositories import UserRepository
from app.schemas import PaginationParams

_bearer = HTTPBearer(auto_error=False)

DB = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DB,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    if credentials is None:
        raise AuthenticationError("Not authenticated.")
    try:
        claims = decode_token(credentials.credentials)
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired token.") from exc
    if claims.get("type") != "access":
        raise AuthenticationError("Access token required.")
    user = await UserRepository(db).get(claims.get("sub", ""))
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    """Role-based access guard. Admin passes all checks."""

    async def guard(user: CurrentUser) -> User:
        if user.role == UserRole.ADMIN or user.role in roles:
            return user
        raise PermissionError("Insufficient permissions for this action.")

    return guard


RecruiterUser = Annotated[User, Depends(require_roles(UserRole.RECRUITER))]
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


def pagination(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


Pagination = Annotated[PaginationParams, Depends(pagination)]
