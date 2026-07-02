"""robots.txt compliance gate.

Fetches and caches each host's robots.txt (1h TTL) and answers whether our
configured user agent may fetch a URL. Failure modes are conservative-friendly:
an unreachable robots.txt (site has none / network error) is treated as
allow-all, matching the standard's default; a fetched file is honored strictly.
"""

from __future__ import annotations

import asyncio
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("scraping.robots")

_TTL_SECONDS = 3600


class RobotsGate:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, RobotFileParser | None]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def _lock_for(self, host: str) -> asyncio.Lock:
        async with self._global_lock:
            if host not in self._locks:
                self._locks[host] = asyncio.Lock()
            return self._locks[host]

    async def _fetch_parser(self, scheme: str, host: str) -> RobotFileParser | None:
        robots_url = f"{scheme}://{host}/robots.txt"
        try:
            async with httpx.AsyncClient(
                timeout=10,
                follow_redirects=True,
                headers={"User-Agent": settings.SCRAPER_USER_AGENT},
                proxy=settings.SCRAPER_HTTP_PROXY or None,
            ) as client:
                response = await client.get(robots_url)
            if response.status_code >= 400:
                return None  # no robots.txt → allow by default
            parser = RobotFileParser()
            parser.parse(response.text.splitlines())
            return parser
        except Exception as exc:
            logger.debug("robots_fetch_failed", host=host, error=str(exc))
            return None

    async def is_allowed(self, url: str) -> bool:
        if not settings.SCRAPER_RESPECT_ROBOTS:
            return True
        parts = urlsplit(url)
        host = parts.netloc.lower()
        if not host:
            return False

        lock = await self._lock_for(host)
        async with lock:
            cached = self._cache.get(host)
            if cached is None or time.time() - cached[0] > _TTL_SECONDS:
                parser = await self._fetch_parser(parts.scheme or "https", host)
                self._cache[host] = (time.time(), parser)
            else:
                parser = cached[1]

        if parser is None:
            return True
        allowed = parser.can_fetch(settings.SCRAPER_USER_AGENT, url)
        if not allowed:
            logger.info("robots_disallowed", url=url)
        return allowed


robots_gate = RobotsGate()
