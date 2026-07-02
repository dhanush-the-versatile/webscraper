"""Respectful async HTTP client for public-page collection.

Centralizes: configurable user agent, timeouts, bounded global concurrency,
per-host minimum delay (pacing), retry with exponential backoff, optional
forward proxy, and the robots.txt gate. All page fetches in the scraping
module go through this client.
"""

from __future__ import annotations

import asyncio
import time

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import get_logger
from app.scraping.robots import robots_gate

logger = get_logger("scraping.http")


class FetchError(Exception):
    """Raised when a page could not be fetched after retries."""


class RobotsDisallowed(FetchError):
    """Raised when robots.txt forbids fetching the URL."""


class _HostPacer:
    """Enforces a minimum delay between requests to the same host."""

    def __init__(self, min_delay: float) -> None:
        self._min_delay = min_delay
        self._last: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def wait(self, host: str) -> None:
        async with self._guard:
            lock = self._locks.setdefault(host, asyncio.Lock())
        async with lock:
            elapsed = time.monotonic() - self._last.get(host, 0.0)
            if elapsed < self._min_delay:
                await asyncio.sleep(self._min_delay - elapsed)
            self._last[host] = time.monotonic()


class RespectfulHTTPClient:
    """Shared, lazily-initialized async client for all collectors."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(settings.SCRAPER_MAX_CONCURRENCY)
        self._pacer = _HostPacer(settings.SCRAPER_MIN_DELAY_SECONDS)
        self._init_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        async with self._init_lock:
            if self._client is None or self._client.is_closed:
                self._client = httpx.AsyncClient(
                    timeout=httpx.Timeout(settings.SCRAPER_REQUEST_TIMEOUT),
                    follow_redirects=True,
                    headers={
                        "User-Agent": settings.SCRAPER_USER_AGENT,
                        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en",
                    },
                    proxy=settings.SCRAPER_HTTP_PROXY or None,
                    limits=httpx.Limits(
                        max_connections=settings.SCRAPER_MAX_CONCURRENCY * 2,
                        max_keepalive_connections=settings.SCRAPER_MAX_CONCURRENCY,
                    ),
                )
            return self._client

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    @retry(
        stop=stop_after_attempt(settings.SCRAPER_MAX_RETRIES),
        wait=wait_exponential(multiplier=0.75, min=0.5, max=8),
        retry=retry_if_exception_type((httpx.TransportError, httpx.ReadTimeout)),
        reraise=True,
    )
    async def _do_get(self, url: str, **kwargs) -> httpx.Response:
        client = await self._get_client()
        return await client.get(url, **kwargs)

    async def get(
        self,
        url: str,
        *,
        respect_robots: bool = True,
        accept_statuses: tuple[int, ...] = (200,),
        **kwargs,
    ) -> httpx.Response:
        """Fetch a URL respecting robots.txt, pacing, and concurrency limits."""
        if respect_robots and not await robots_gate.is_allowed(url):
            raise RobotsDisallowed(f"robots.txt disallows fetching {url}")

        host = httpx.URL(url).host or ""
        async with self._semaphore:
            await self._pacer.wait(host)
            started = time.perf_counter()
            try:
                response = await self._do_get(url, **kwargs)
            except httpx.HTTPError as exc:
                logger.warning("fetch_failed", url=url, error=str(exc))
                raise FetchError(f"Failed to fetch {url}: {exc}") from exc
        elapsed = round((time.perf_counter() - started) * 1000)
        logger.debug("fetched", url=url, status=response.status_code, ms=elapsed)

        if response.status_code not in accept_statuses:
            raise FetchError(f"Unexpected status {response.status_code} for {url}")
        return response

    async def get_text(self, url: str, **kwargs) -> str:
        response = await self.get(url, **kwargs)
        return response.text

    async def get_json(self, url: str, **kwargs):
        response = await self.get(url, **kwargs)
        return response.json()


http_client = RespectfulHTTPClient()
