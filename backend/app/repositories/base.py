"""Generic async repository implementing common CRUD operations.

Concrete repositories inherit from ``BaseRepository`` and add domain-specific
queries. Keeping persistence concerns here lets services stay free of
SQLAlchemy details (Repository Pattern).
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---- Reads ----
    async def get(self, id_: str) -> ModelT | None:
        return await self.db.get(self.model, id_)

    async def get_by(self, **filters: Any) -> ModelT | None:
        stmt = select(self.model).filter_by(**filters).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        order_by: Any | None = None,
        **filters: Any,
    ) -> list[ModelT]:
        stmt: Select = select(self.model).filter_by(**filters)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(offset).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())

    async def count(self, **filters: Any) -> int:
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        return int((await self.db.execute(stmt)).scalar_one())

    # ---- Writes ----
    async def add(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def create(self, **fields: Any) -> ModelT:
        return await self.add(self.model(**fields))

    async def update(self, obj: ModelT, **fields: Any) -> ModelT:
        for key, value in fields.items():
            setattr(obj, key, value)
        await self.db.flush()
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.db.delete(obj)
        await self.db.flush()
