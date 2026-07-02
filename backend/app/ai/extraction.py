"""Profile extraction: public page text → structured candidate profile."""

from __future__ import annotations

from typing import Any

from app.ai import heuristics
from app.ai.provider import get_llm_provider
from app.core.logging import get_logger

logger = get_logger("ai.extraction")

_SYSTEM_PROMPT = """You extract publicly available professional profile data from web \
page text. Only report information explicitly present in the text — never guess or \
fabricate. Return JSON with these keys (null / [] / {} when absent):
  full_name: string|null
  headline: string|null            — professional title/role line
  company: string|null             — current company
  seniority: string|null           — intern|junior|mid|senior|lead|principal|executive
  years_experience: int|null
  country: string|null
  city: string|null
  skills: string[]                 — professional skills mentioned
  technologies: string[]           — tools/languages/frameworks mentioned
  public_email: string|null        — ONLY if explicitly published on the page
  linkedin_url: string|null
  github_url: string|null
  portfolio_url: string|null
  website_url: string|null
  social_links: object             — map of platform → url found on the page
  bio: string|null                 — short professional summary (max 500 chars)
  experiences: [{company, title, start_date, end_date, is_current, description}]
  extraction_confidence: float     — 0..1, your confidence this is one person's profile
"""

_PROFILE_KEYS = {
    "full_name", "headline", "company", "seniority", "years_experience",
    "country", "city", "skills", "technologies", "public_email",
    "linkedin_url", "github_url", "portfolio_url", "website_url",
    "social_links", "bio", "experiences", "extraction_confidence",
}


def _sanitize(data: dict[str, Any]) -> dict[str, Any]:
    """Keep known keys only and coerce obvious type issues."""
    clean: dict[str, Any] = {k: v for k, v in data.items() if k in _PROFILE_KEYS}
    for list_key in ("skills", "technologies", "experiences"):
        if not isinstance(clean.get(list_key), list):
            clean[list_key] = []
    if not isinstance(clean.get("social_links"), dict):
        clean["social_links"] = {}
    try:
        clean["extraction_confidence"] = max(
            0.0, min(1.0, float(clean.get("extraction_confidence") or 0.5))
        )
    except (TypeError, ValueError):
        clean["extraction_confidence"] = 0.5
    years = clean.get("years_experience")
    if years is not None:
        try:
            clean["years_experience"] = max(0, min(60, int(years)))
        except (TypeError, ValueError):
            clean["years_experience"] = None
    if bio := clean.get("bio"):
        clean["bio"] = str(bio)[:2000]
    return clean


async def extract_profile(
    text: str, *, url: str = "", title: str = ""
) -> dict[str, Any]:
    """Extract a structured profile from page text (LLM first, heuristics after).

    The returned dict matches the keys consumed by the collection pipeline.
    """
    text = (text or "").strip()
    if not text:
        return {"extraction_confidence": 0.0}

    provider = get_llm_provider()
    if provider is not None:
        data = await provider.acomplete_json(
            system=_SYSTEM_PROMPT,
            user=f"Source URL: {url}\nPage title: {title}\n\nPage text:\n{text[:12000]}",
        )
        if isinstance(data, dict) and data.get("full_name"):
            logger.debug("profile_extracted", provider=provider.name, url=url)
            return _sanitize(data)

    result = heuristics.extract_profile_from_text(text, url=url, title=title)
    result.setdefault("experiences", [])
    logger.debug("profile_extracted", provider="heuristic", url=url)
    return result
