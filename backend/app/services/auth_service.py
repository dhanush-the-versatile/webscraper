"""Authentication service: registration, login, token refresh, OAuth."""

from __future__ import annotations

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ConflictError, ExternalServiceError
from app.core.logging import get_logger
from app.core.security import (
    JWTError,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import AuthProvider, User
from app.repositories import AuditRepository, UserRepository
from app.schemas import OAuthLoginRequest, Token, UserCreate

logger = get_logger("auth")


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.audit = AuditRepository(db)

    # ------------------------------------------------------------------ #
    # Email / password
    # ------------------------------------------------------------------ #
    async def register(self, payload: UserCreate) -> User:
        email = payload.email.lower().strip()
        if await self.users.get_by_email(email):
            raise ConflictError("An account with this email already exists.")
        user = await self.users.create(
            email=email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            auth_provider=AuthProvider.LOCAL,
        )
        await self.audit.record("user.register", actor_user_id=user.id)
        logger.info("user_registered", user_id=user.id)
        return user

    async def authenticate(self, email: str, password: str) -> Token:
        user = await self.users.get_by_email(email)
        if user is None or not user.hashed_password:
            raise AuthenticationError("Invalid email or password.")
        if not verify_password(password, user.hashed_password):
            await self.audit.record("user.login_failed", meta={"email": email})
            raise AuthenticationError("Invalid email or password.")
        if not user.is_active:
            raise AuthenticationError("This account is disabled.")
        await self.audit.record("user.login", actor_user_id=user.id)
        return Token(**create_token_pair(user.id, extra_claims={"role": user.role.value}))

    async def refresh(self, refresh_token: str) -> Token:
        try:
            claims = decode_token(refresh_token)
        except JWTError as exc:
            raise AuthenticationError("Invalid refresh token.") from exc
        if claims.get("type") != "refresh":
            raise AuthenticationError("Token is not a refresh token.")
        user = await self.users.get(claims.get("sub", ""))
        if user is None or not user.is_active:
            raise AuthenticationError("User not found or inactive.")
        return Token(**create_token_pair(user.id, extra_claims={"role": user.role.value}))

    # ------------------------------------------------------------------ #
    # OAuth (Google / GitHub) — authorization-code exchange
    # ------------------------------------------------------------------ #
    async def oauth_login(self, payload: OAuthLoginRequest) -> Token:
        if payload.provider == AuthProvider.GOOGLE:
            profile = await self._exchange_google(payload)
        elif payload.provider == AuthProvider.GITHUB:
            profile = await self._exchange_github(payload)
        else:
            raise AuthenticationError("Unsupported OAuth provider.")

        user = await self.users.get_by_oauth(payload.provider, profile["subject"])
        if user is None:
            # Link by verified email when possible, otherwise create.
            user = await self.users.get_by_email(profile["email"]) if profile.get("email") else None
            if user is None:
                user = await self.users.create(
                    email=profile.get("email") or f"{profile['subject']}@{payload.provider.value}.oauth.local",
                    full_name=profile.get("name"),
                    auth_provider=payload.provider,
                    oauth_subject=profile["subject"],
                    avatar_url=profile.get("avatar_url"),
                    is_verified=True,
                )
            else:
                await self.users.update(
                    user, auth_provider=payload.provider, oauth_subject=profile["subject"]
                )
        await self.audit.record("user.oauth_login", actor_user_id=user.id,
                                meta={"provider": payload.provider.value})
        return Token(**create_token_pair(user.id, extra_claims={"role": user.role.value}))

    async def _exchange_google(self, payload: OAuthLoginRequest) -> dict:
        if not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET):
            raise ExternalServiceError("Google OAuth is not configured on this server.")
        async with httpx.AsyncClient(timeout=15) as client:
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": payload.code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": payload.redirect_uri
                    or f"{settings.OAUTH_REDIRECT_BASE}/auth/callback/google",
                    "grant_type": "authorization_code",
                },
            )
            if token_res.status_code != 200:
                raise AuthenticationError("Google code exchange failed.")
            access = token_res.json().get("access_token")
            info = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access}"},
            )
            if info.status_code != 200:
                raise ExternalServiceError("Failed to fetch Google profile.")
            data = info.json()
        return {
            "subject": data["sub"],
            "email": data.get("email"),
            "name": data.get("name"),
            "avatar_url": data.get("picture"),
        }

    async def _exchange_github(self, payload: OAuthLoginRequest) -> dict:
        if not (settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET):
            raise ExternalServiceError("GitHub OAuth is not configured on this server.")
        async with httpx.AsyncClient(timeout=15) as client:
            token_res = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "code": payload.code,
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                },
            )
            access = token_res.json().get("access_token")
            if not access:
                raise AuthenticationError("GitHub code exchange failed.")
            info = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access}"},
            )
            if info.status_code != 200:
                raise ExternalServiceError("Failed to fetch GitHub profile.")
            data = info.json()
            emails = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access}"},
            )
            primary_email = None
            if emails.status_code == 200:
                primary_email = next(
                    (e["email"] for e in emails.json() if e.get("primary") and e.get("verified")),
                    None,
                )
        return {
            "subject": str(data["id"]),
            "email": primary_email or data.get("email"),
            "name": data.get("name") or data.get("login"),
            "avatar_url": data.get("avatar_url"),
        }
