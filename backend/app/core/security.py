"""Security primitives: password hashing and JWT creation/verification."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        # Malformed hash on record — treat as non-match rather than crashing.
        return False


def create_token(
    subject: str | int,
    token_type: TokenType = "access",
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT for ``subject`` (typically the user id)."""
    now = datetime.now(UTC)
    if expires_delta is None:
        minutes = (
            settings.ACCESS_TOKEN_EXPIRE_MINUTES
            if token_type == "access"
            else settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )
        expires_delta = timedelta(minutes=minutes)

    claims: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises ``JWTError`` on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def create_token_pair(subject: str | int, extra_claims: dict[str, Any] | None = None) -> dict:
    return {
        "access_token": create_token(subject, "access", extra_claims=extra_claims),
        "refresh_token": create_token(subject, "refresh", extra_claims=extra_claims),
        "token_type": "bearer",
    }


__all__ = [
    "hash_password",
    "verify_password",
    "create_token",
    "decode_token",
    "create_token_pair",
    "JWTError",
]
