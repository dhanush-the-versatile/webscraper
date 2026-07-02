"""User and authentication schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import AuthProvider, UserRole
from app.schemas.common import ORMModel


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserRead(ORMModel):
    id: str
    email: EmailStr
    full_name: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    auth_provider: AuthProvider
    avatar_url: str | None
    created_at: datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None
    type: str | None = None
    exp: int | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class OAuthLoginRequest(BaseModel):
    """Exchange an OAuth authorization code for platform tokens."""

    provider: AuthProvider
    code: str
    redirect_uri: str | None = None
