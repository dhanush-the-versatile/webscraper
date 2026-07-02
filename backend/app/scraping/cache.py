"""Fetch cache: Redis-backed with a bounded in-memory fallback.

Caching collected pages/API responses avoids re-hitting public sites on
repeated searches (both a performance win and part of respectful crawling).
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("scraping.cache")

_DEFAULT_TTL = 6 * 3600
_MEMORY_MAX_ENTRIES = 2000


class FetchCache:
    def __init__(self) -> None:
        self._redis = None
        self._redis_checked = False
        self._memory: OrderedDict[str, tuple[float, str]] = OrderedDict()

    async def _get_redis(self):
        if self._redis_checked:
            return self._redis
        self._redis_checked = True
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(
                settings.redis_url, socket_connect_timeout=2, decode_responses=True
            )
            await client.ping()
            self._redis = client
            logger.info("fetch_cache_backend", backend="redis")
        except Exception:
            self._redis = None
            logger.info("fetch_cache_backend", backend="memory")
        return self._redis

    @staticmethod
    def _key(namespace: str, key: str) -> str:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        return f"talent:cache:{namespace}:{digest}"

    async def get(self, namespace: str, key: str) -> Any | None:
        cache_key = self._key(namespace, key)
        redis = await self._get_redis()
        if redis is not None:
            try:
                raw = await redis.get(cache_key)
                return json.loads(raw) if raw else None
            except Exception:
                pass
        entry = self._memory.get(cache_key)
        if entry and entry[0] > time.time():
            return json.loads(entry[1])
        return None

    async def set(
        self, namespace: str, key: str, value: Any, *, ttl: int = _DEFAULT_TTL
    ) -> None:
        cache_key = self._key(namespace, key)
        payload = json.dumps(value, ensure_ascii=False, default=str)
        redis = await self._get_redis()
        if redis is not None:
            try:
                await redis.set(cache_key, payload, ex=ttl)
                return
            except Exception:
                pass
        self._memory[cache_key] = (time.time() + ttl, payload)
        self._memory.move_to_end(cache_key)
        while len(self._memory) > _MEMORY_MAX_ENTRIES:
            self._memory.popitem(last=False)


fetch_cache = FetchCache()
