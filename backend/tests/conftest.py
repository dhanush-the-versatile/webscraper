"""Shared test fixtures.

The test database is a per-session temp-file SQLite (async) so that the API's
inline background tasks — which open their own sessions via the global engine —
see the same data as the test client.
"""

from __future__ import annotations

import os
import tempfile

_TMPDIR = tempfile.mkdtemp(prefix="tdp-tests-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMPDIR}/test.db"
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import asyncio  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models import Base  # noqa: E402


# --------------------------------------------------------------------------- #
# Isolated in-memory DB for repository/service unit tests
# --------------------------------------------------------------------------- #
@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


# --------------------------------------------------------------------------- #
# Full-app client backed by the shared temp-file DB
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def app_client() -> TestClient:
    from app.db.session import engine
    from app.main import app

    async def _prepare() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_prepare())
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def auth_headers(app_client: TestClient) -> dict[str, str]:
    """A registered + logged-in recruiter."""
    response = app_client.post(
        "/api/v1/auth/register",
        json={"email": "tester@example.com", "password": "testpass123", "full_name": "Test User"},
    )
    assert response.status_code == 201, response.text
    login = app_client.post(
        "/api/v1/auth/login",
        json={"email": "tester@example.com", "password": "testpass123"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
