"""Async database engine and session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ``pool_pre_ping`` guards against stale connections; pool sizing is tuned for
# an async workload. SQLite (used by the test suite) uses NullPool and does not
# accept pool sizing arguments, so we only apply them for real server engines.
_engine_kwargs: dict = {"echo": False, "pool_pre_ping": True, "future": True}
if not settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs.update(pool_size=10, max_overflow=20, pool_recycle=1800)

engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a transactional session.

    Commits on success, rolls back on error, and always closes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
