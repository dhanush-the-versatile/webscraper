"""Authentication endpoints: email/password, refresh, OAuth, profile."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import DB, CurrentUser
from app.core.security import hash_password
from app.repositories import UserRepository
from app.schemas import (
    LoginRequest,
    OAuthLoginRequest,
    RefreshRequest,
    Token,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.services import AuthService

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED,
             summary="Register with email and password")
async def register(payload: UserCreate, db: DB) -> UserRead:
    user = await AuthService(db).register(payload)
    return UserRead.model_validate(user)


@router.post("/login", response_model=Token, summary="Login with email and password")
async def login(payload: LoginRequest, db: DB) -> Token:
    return await AuthService(db).authenticate(payload.email, payload.password)


@router.post("/refresh", response_model=Token, summary="Exchange a refresh token")
async def refresh(payload: RefreshRequest, db: DB) -> Token:
    return await AuthService(db).refresh(payload.refresh_token)


@router.post("/oauth", response_model=Token, summary="Login via Google/GitHub authorization code")
async def oauth_login(payload: OAuthLoginRequest, db: DB) -> Token:
    return await AuthService(db).oauth_login(payload)


@router.get("/me", response_model=UserRead, summary="Current user profile")
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead, summary="Update current user profile")
async def update_me(payload: UserUpdate, user: CurrentUser, db: DB) -> UserRead:
    fields: dict = {}
    if payload.full_name is not None:
        fields["full_name"] = payload.full_name
    if payload.avatar_url is not None:
        fields["avatar_url"] = payload.avatar_url
    if payload.password:
        fields["hashed_password"] = hash_password(payload.password)
    if fields:
        user = await UserRepository(db).update(user, **fields)
    return UserRead.model_validate(user)
