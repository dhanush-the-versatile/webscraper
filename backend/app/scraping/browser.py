"""Optional Playwright-based fetcher for JavaScript-rendered public pages.

Disabled by default (``SCRAPER_ENABLE_BROWSER=false``). When enabled it is
used only as a *second attempt* after static extraction yields too little
content — and only for URLs that already passed the robots.txt gate. It never
logs in, never solves challenges, and never evades access controls: it simply
renders the same public page a regular browser visitor would see.

Enabling requires browsers to be present (``playwright install chromium``) or
``SCRAPER_BROWSER_EXECUTABLE`` pointing at a Chromium binary.
"""

from __future__ import annotations

import asyncio

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("scraping.browser")

_launch_lock = asyncio.Lock()
_unavailable = False  # sticky: don't retry a broken install on every URL


async def fetch_rendered_html(url: str, *, timeout_ms: int = 20000) -> str | None:
    """Return rendered HTML for ``url``, or ``None`` when disabled/unavailable.

    Callers must have consulted the robots gate already (the generic enricher
    does this via ``http_client.get`` before ever escalating to the browser).
    """
    global _unavailable
    if not settings.SCRAPER_ENABLE_BROWSER or _unavailable:
        return None

    try:
        from playwright.async_api import async_playwright
    except ImportError:  # playwright not installed in this deployment
        logger.warning("browser_fetch_unavailable", reason="playwright_not_installed")
        _unavailable = True
        return None

    async with _launch_lock:  # one browser launch at a time keeps memory sane
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    executable_path=settings.SCRAPER_BROWSER_EXECUTABLE or None,
                )
                try:
                    context = await browser.new_context(
                        user_agent=settings.SCRAPER_USER_AGENT,
                        java_script_enabled=True,
                    )
                    page = await context.new_page()
                    await page.goto(url, timeout=timeout_ms, wait_until="networkidle")
                    html = await page.content()
                    logger.debug("browser_fetched", url=url, size=len(html))
                    return html
                finally:
                    await browser.close()
        except Exception as exc:
            message = str(exc)
            if "Executable doesn't exist" in message or "install" in message.lower():
                logger.warning("browser_fetch_unavailable", reason="browsers_not_installed")
                _unavailable = True
            else:
                logger.warning("browser_fetch_failed", url=url, error=message[:300])
            return None
