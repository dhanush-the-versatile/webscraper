"""Search-engine providers.

Preference order (all official APIs, per the compliance constraints):

1. SerpAPI  — Google results via a licensed API
2. Bing Web Search API
3. SampleDataProvider — deterministic synthetic profiles, clearly flagged,
   so the platform stays fully demoable with zero external keys.
"""

from __future__ import annotations

import hashlib
import random

from app.core.config import settings
from app.core.logging import get_logger
from app.models import SourceType
from app.schemas import GeneratedQuery
from app.scraping.cache import fetch_cache
from app.scraping.http_client import FetchError, http_client
from app.scraping.models import SearchHit
from app.scraping.sources.base import SearchProvider

logger = get_logger("scraping.search")


def _infer_source(url: str, default: SourceType) -> SourceType:
    lowered = url.lower()
    mapping = {
        "linkedin.com/in": SourceType.LINKEDIN,
        "github.com": SourceType.GITHUB,
        "stackoverflow.com": SourceType.STACKOVERFLOW,
        "kaggle.com": SourceType.KAGGLE,
        "medium.com": SourceType.MEDIUM,
        "dev.to": SourceType.DEVTO,
        "behance.net": SourceType.BEHANCE,
        "dribbble.com": SourceType.DRIBBBLE,
        "scholar.google": SourceType.RESEARCH,
    }
    for fragment, source in mapping.items():
        if fragment in lowered:
            return source
    return default


class SerpAPIProvider(SearchProvider):
    name = "serpapi"

    def available(self) -> bool:
        return bool(settings.SERPAPI_API_KEY)

    async def search(self, query: GeneratedQuery, *, limit: int = 10) -> list[SearchHit]:
        cache_key = f"serpapi:{query.query}:{limit}"
        if cached := await fetch_cache.get("search", cache_key):
            return [SearchHit(**hit) for hit in cached]
        try:
            data = await http_client.get_json(
                "https://serpapi.com/search.json",
                respect_robots=False,  # licensed API endpoint, not a crawl
                params={
                    "engine": "google",
                    "q": query.query,
                    "num": min(limit, 20),
                    "api_key": settings.SERPAPI_API_KEY,
                },
            )
        except FetchError as exc:
            logger.warning("serpapi_failed", error=str(exc))
            return []
        hits = [
            SearchHit(
                url=item.get("link", ""),
                title=item.get("title", ""),
                snippet=item.get("snippet", ""),
                source=_infer_source(item.get("link", ""), query.source),
                provider=self.name,
            )
            for item in data.get("organic_results", [])
            if item.get("link")
        ][:limit]
        await fetch_cache.set(
            "search", cache_key, [hit.__dict__ for hit in hits], ttl=3600
        )
        return hits


class BingSearchProvider(SearchProvider):
    name = "bing"

    def available(self) -> bool:
        return bool(settings.BING_SEARCH_API_KEY)

    async def search(self, query: GeneratedQuery, *, limit: int = 10) -> list[SearchHit]:
        cache_key = f"bing:{query.query}:{limit}"
        if cached := await fetch_cache.get("search", cache_key):
            return [SearchHit(**hit) for hit in cached]
        try:
            response = await http_client.get(
                "https://api.bing.microsoft.com/v7.0/search",
                respect_robots=False,  # licensed API endpoint
                params={"q": query.query, "count": min(limit, 20)},
                headers={"Ocp-Apim-Subscription-Key": settings.BING_SEARCH_API_KEY},
            )
            data = response.json()
        except FetchError as exc:
            logger.warning("bing_failed", error=str(exc))
            return []
        hits = [
            SearchHit(
                url=item.get("url", ""),
                title=item.get("name", ""),
                snippet=item.get("snippet", ""),
                source=_infer_source(item.get("url", ""), query.source),
                provider=self.name,
            )
            for item in (data.get("webPages", {}) or {}).get("value", [])
            if item.get("url")
        ][:limit]
        await fetch_cache.set(
            "search", cache_key, [hit.__dict__ for hit in hits], ttl=3600
        )
        return hits


# --------------------------------------------------------------------------- #
# Sample data provider (no external keys required)
# --------------------------------------------------------------------------- #
_FIRST = ["Alex", "Maria", "Jonas", "Priya", "Chen", "Sofia", "Liam", "Aisha",
          "Felix", "Nina", "Diego", "Yuki", "Emma", "Omar", "Lena", "Ravi",
          "Clara", "Tomás", "Ingrid", "Kwame"]
_LAST = ["Schmidt", "García", "Novak", "Patel", "Wang", "Rossi", "Müller",
         "Okafor", "Johansson", "Kim", "Silva", "Tanaka", "Dubois", "Haddad",
         "Kowalski", "Iyer", "Berg", "Costa", "Nilsen", "Mensah"]
_COMPANIES = ["Nebula Labs", "Brightpath", "Cloudforge", "DataHive", "Pixelwise",
              "Quantify", "Greenline Tech", "Vertex Studio", "Atlas Systems", "Nordwind"]

_SAMPLE_DISCLAIMER = (
    "Sample profile generated locally because no search API key "
    "(SERPAPI_API_KEY / BING_SEARCH_API_KEY) is configured."
)


class SampleDataProvider(SearchProvider):
    """Deterministic synthetic results for keyless development/demo mode.

    Every hit is explicitly flagged ``is_sample`` in its metadata and rendered
    as such downstream — sample data is never passed off as real collection.
    """

    name = "sample"

    def available(self) -> bool:
        return True

    async def search(self, query: GeneratedQuery, *, limit: int = 10) -> list[SearchHit]:
        from app.ai.taxonomy import COUNTRIES, TECH_TAXONOMY

        seed = int(hashlib.sha256(query.query.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        terms = [t.strip('"') for t in query.query.split() if not t.startswith("site:")]
        # Only real tech-taxonomy terms become skills — query template words
        # ("portfolio", "resume", "our team", …) must not pollute sample data.
        skills = list(dict.fromkeys(t.lower() for t in terms if t.lower() in TECH_TAXONOMY))[
            :4
        ] or ["python"]
        # Only a term that is a known city may become the location — job-title
        # words are capitalized too and must not be mistaken for one.
        known_cities = {alias for aliases in COUNTRIES.values() for alias in aliases}
        city = next(
            (t.title() for t in terms if t.lower() in known_cities), "Berlin"
        )

        hits: list[SearchHit] = []
        count = min(limit, 3 + rng.randint(0, 2))
        for index in range(count):
            first, last = rng.choice(_FIRST), rng.choice(_LAST)
            years = rng.randint(2, 12)
            company = rng.choice(_COMPANIES)
            handle = f"{first.lower()}{last.lower()}{index}"
            skill_text = ", ".join(skills)
            hits.append(
                SearchHit(
                    url=f"https://example.com/profiles/{handle}",
                    title=f"{first} {last} - {skills[0].title()} Developer",
                    snippet=(
                        f"{first} {last} is a developer at {company} in {city} with "
                        f"{years} years of experience in {skill_text}."
                    ),
                    source=query.source,
                    provider=self.name,
                    meta={
                        "is_sample": True,
                        "disclaimer": _SAMPLE_DISCLAIMER,
                        "profile": {
                            "full_name": f"{first} {last}",
                            "headline": f"{skills[0].title()} Developer",
                            "company": company,
                            "city": city,
                            "years_experience": years,
                            "technologies": skills,
                            "github_url": f"https://github.com/{handle}",
                            "bio": (
                                f"{first} {last} builds software at {company}. "
                                f"Focus areas: {skill_text}. ({_SAMPLE_DISCLAIMER})"
                            ),
                            "github_stats": {
                                "public_repos": rng.randint(3, 80),
                                "followers": rng.randint(0, 900),
                                "total_stars": rng.randint(0, 2500),
                            },
                            "extraction_confidence": 0.9,
                        },
                    },
                )
            )
        return hits


def get_search_providers() -> list[SearchProvider]:
    """Return usable providers in preference order (sample last, only if needed)."""
    real = [p for p in (SerpAPIProvider(), BingSearchProvider()) if p.available()]
    if real:
        return real
    logger.info("search_provider_sample_mode")
    return [SampleDataProvider()]
