"""HTML → clean text/metadata extraction.

Prefers ``trafilatura`` (strong boilerplate removal); falls back to a
BeautifulSoup text strategy. Also pulls the page title and social/meta hints.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from app.core.logging import get_logger

logger = get_logger("scraping.extractor")

try:  # trafilatura is heavy; degrade quietly if unavailable
    import trafilatura

    _HAS_TRAFILATURA = True
except Exception:  # pragma: no cover
    trafilatura = None  # type: ignore[assignment]
    _HAS_TRAFILATURA = False


@dataclass(slots=True)
class ExtractedPage:
    text: str = ""
    title: str = ""
    description: str = ""
    links: list[str] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)


def _soup_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "template", "svg", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # collapse whitespace but keep paragraph structure
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_page(html: str, url: str = "") -> ExtractedPage:
    """Extract readable text + metadata from raw HTML."""
    if not html:
        return ExtractedPage()

    page = ExtractedPage()

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:  # lxml missing or catastrophically bad markup
        soup = BeautifulSoup(html, "html.parser")

    if soup.title and soup.title.string:
        page.title = soup.title.string.strip()[:512]

    for meta_name in ("description", "og:description"):
        tag = soup.find("meta", attrs={"name": meta_name}) or soup.find(
            "meta", attrs={"property": meta_name}
        )
        if tag and tag.get("content"):
            page.description = tag["content"].strip()[:1000]
            break

    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        page.meta["og:title"] = og_title["content"].strip()[:512]

    page.links = list(
        {
            a["href"].strip()
            for a in soup.find_all("a", href=True)
            if a["href"].startswith("http")
        }
    )[:200]

    text = ""
    if _HAS_TRAFILATURA:
        try:
            text = trafilatura.extract(
                html, url=url or None, include_comments=False, include_tables=False
            ) or ""
        except Exception as exc:  # pragma: no cover
            logger.debug("trafilatura_failed", url=url, error=str(exc))
    if len(text) < 200:  # boilerplate-only or extraction failure → soup fallback
        text = _soup_text(soup)

    page.text = text[:40000]
    return page
