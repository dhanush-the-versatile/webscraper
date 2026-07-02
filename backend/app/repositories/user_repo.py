"""User repository."""

from __future__ import annotations

from app.models import AuthProvider, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        return await self.get_by(email=email.lower().strip())

    async def get_by_oauth(self, provider: AuthProvider, subject: str) -> User | None:
        return await self.get_by(auth_provider=provider, oauth_subject=subject)
