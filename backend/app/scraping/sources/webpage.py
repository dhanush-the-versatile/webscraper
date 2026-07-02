"""Generic and special-cased page enrichers.

* ``SampleEnricher``   — materializes profiles from the sample provider's meta.
* ``LinkedInSnippetEnricher`` — LinkedIn pages are auth-walled and their ToS
  prohibit scraping, so we NEVER fetch linkedin.com. We only use the public
  search-engine snippet (title/summary) of a publicly indexed profile.
* ``GenericWebEnricher``  — fetches any other public page (robots-gated),
  extracts readable text, and runs AI profile extraction. Handles portfolios,
  company team pages, Medium/Dev.to/Kaggle/Behance/Dribbble profiles, etc.
"""

from __future__ import annotations

import re

from app.ai.extraction import extract_profile
from app.core.logging import get_logger
from app.models import SourceType
from app.schemas import ParsedRequirement
from app.scraping.cache import fetch_cache
from app.scraping.extractor import extract_page
from app.scraping.http_client import FetchError, RobotsDisallowed, http_client
from app.scraping.models import CollectedProfile, SearchHit
from app.scraping.sources.base import ProfileEnricher

logger = get_logger("scraping.webpage")

_LI_TITLE_RE = re.compile(
    r"^(?P<name>[^-|–]{2,60}?)\s*[-–]\s*(?P<headline>[^|–-]{2,120}?)"
    r"(?:\s*[-|–]\s*(?P<location>[^|]{2,60}?))?\s*(?:\|\s*LinkedIn)?$",
    re.IGNORECASE,
)


class SampleEnricher(ProfileEnricher):
    name = "sample"

    def matches(self, hit: SearchHit) -> bool:
        return bool(hit.meta.get("is_sample"))

    async def enrich(
        self, hit: SearchHit, requirement: ParsedRequirement
    ) -> CollectedProfile | None:
        profile = dict(hit.meta.get("profile") or {})
        if not profile.get("full_name"):
            return None
        profile.setdefault("skills", [])
        profile.setdefault("experiences", [])
        profile.setdefault("social_links", {})
        # bias sample data toward the requirement so demos look coherent
        if requirement.countries and not profile.get("country"):
            profile["country"] = requirement.countries[0]
        return CollectedProfile(
            data=profile,
            source_url=hit.url,
            source_type=hit.source,
            source_title=hit.title,
            source_snippet=hit.snippet,
            content_excerpt=hit.snippet,
            meta={"is_sample": True, "disclaimer": hit.meta.get("disclaimer", "")},
        )


class LinkedInSnippetEnricher(ProfileEnricher):
    """Snippet-only handling of publicly indexed LinkedIn profiles."""

    name = "linkedin_snippet"

    def matches(self, hit: SearchHit) -> bool:
        return "linkedin.com/in" in hit.url.lower()

    async def enrich(
        self, hit: SearchHit, requirement: ParsedRequirement
    ) -> CollectedProfile | None:
        title = (hit.title or "").strip()
        match = _LI_TITLE_RE.match(title)
        full_name = headline = location = None
        if match:
            full_name = match.group("name").strip()
            headline = (match.group("headline") or "").strip() or None
            location = (match.group("location") or "").strip() or None
        if not full_name or len(full_name.split()) > 5:
            return None

        city = country = None
        if location:
            pieces = [p.strip() for p in location.split(",") if p.strip()]
            if len(pieces) >= 2:
                city, country = pieces[0], pieces[-1]
            else:
                city = pieces[0]

        # pull skills mentioned in the public snippet text
        snippet_l = f" {hit.snippet.lower()} "
        skills = [s for s in requirement.all_skills() if s in snippet_l]

        data = {
            "full_name": full_name,
            "headline": headline,
            "city": city,
            "country": country,
            "linkedin_url": hit.url.split("?")[0],
            "skills": skills,
            "technologies": skills,
            "social_links": {"linkedin": hit.url.split("?")[0]},
            "bio": hit.snippet[:500] or None,
            "experiences": [],
            "github_stats": {},
            "extraction_confidence": 0.55,  # snippet-only → moderate confidence
        }
        return CollectedProfile(
            data=data,
            source_url=hit.url.split("?")[0],
            source_type=SourceType.LINKEDIN,
            source_title=title,
            source_snippet=hit.snippet,
            content_excerpt=hit.snippet,
            meta={"mode": "search_snippet_only"},
        )


class GenericWebEnricher(ProfileEnricher):
    """Fetch + extract any other public page (robots.txt-gated)."""

    name = "webpage"

    _SKIP_HOST_FRAGMENTS = ("linkedin.com", "facebook.com", "instagram.com", "x.com",
                            "twitter.com", "example.com")

    def matches(self, hit: SearchHit) -> bool:
        lowered = hit.url.lower()
        return lowered.startswith("http") and not any(
            fragment in lowered for fragment in self._SKIP_HOST_FRAGMENTS
        )

    async def enrich(
        self, hit: SearchHit, requirement: ParsedRequirement
    ) -> CollectedProfile | None:
        cached = await fetch_cache.get("page", hit.url)
        if cached is not None:
            html, title = cached.get("html", ""), cached.get("title", "")
        else:
            try:
                response = await http_client.get(hit.url)
            except RobotsDisallowed:
                return None
            except FetchError as exc:
                logger.debug("page_fetch_failed", url=hit.url, error=str(exc))
                return None
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type and "text" not in content_type:
                return None
            html, title = response.text, ""
            await fetch_cache.set(
                "page", hit.url, {"html": html[:400000], "title": title}, ttl=6 * 3600
            )

        page = extract_page(html, url=hit.url)
        if len(page.text) < 120:  # not enough public content to extract from
            return None

        profile = await extract_profile(
            page.text, url=hit.url, title=page.title or hit.title
        )
        if not profile.get("full_name"):
            return None

        return CollectedProfile(
            data=profile,
            source_url=hit.url,
            source_type=hit.source if hit.source != SourceType.SEARCH_ENGINE else SourceType.PORTFOLIO,
            source_title=page.title or hit.title,
            source_snippet=hit.snippet or page.description,
            content_excerpt=page.text[:1500],
            meta={"links_found": len(page.links)},
        )
