"""GitHub enrichment via the official REST API (preferred over page scraping)."""

from __future__ import annotations

import re

from app.core.config import settings
from app.core.logging import get_logger
from app.models import SourceType
from app.schemas import ParsedRequirement
from app.scraping.cache import fetch_cache
from app.scraping.http_client import FetchError, http_client
from app.scraping.models import CollectedProfile, SearchHit
from app.scraping.sources.base import ProfileEnricher

logger = get_logger("scraping.github")

_LOGIN_RE = re.compile(r"github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))(?:/|$|\?)")
_RESERVED = {
    "features", "topics", "collections", "trending", "marketplace", "sponsors",
    "about", "pricing", "search", "login", "join", "orgs", "apps", "settings",
    "explore", "contact", "site", "blog", "enterprise", "customer-stories",
}


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    return headers


def parse_login(url: str) -> str | None:
    match = _LOGIN_RE.search(url)
    if not match:
        return None
    login = match.group(1)
    return None if login.lower() in _RESERVED else login


class GitHubEnricher(ProfileEnricher):
    name = "github"

    def matches(self, hit: SearchHit) -> bool:
        return (
            hit.source == SourceType.GITHUB
            or "github.com/" in hit.url
        ) and parse_login(hit.url) is not None

    async def _api(self, path: str):
        cache_key = f"gh:{path}"
        if cached := await fetch_cache.get("github", cache_key):
            return cached
        data = await http_client.get_json(
            f"https://api.github.com{path}",
            respect_robots=False,  # official API, authenticated when possible
            headers=_headers(),
        )
        await fetch_cache.set("github", cache_key, data, ttl=6 * 3600)
        return data

    async def enrich(
        self, hit: SearchHit, requirement: ParsedRequirement
    ) -> CollectedProfile | None:
        login = parse_login(hit.url)
        if not login:
            return None
        try:
            user = await self._api(f"/users/{login}")
            repos = await self._api(f"/users/{login}/repos?sort=updated&per_page=30")
        except FetchError as exc:
            logger.warning("github_enrich_failed", login=login, error=str(exc))
            return None
        if not isinstance(user, dict) or user.get("type") == "Organization":
            return None

        languages: dict[str, int] = {}
        total_stars = 0
        top_repos: list[dict] = []
        for repo in repos if isinstance(repos, list) else []:
            if repo.get("fork"):
                continue
            if lang := repo.get("language"):
                languages[lang.lower()] = languages.get(lang.lower(), 0) + 1
            stars = int(repo.get("stargazers_count") or 0)
            total_stars += stars
            top_repos.append(
                {
                    "name": repo.get("name"),
                    "url": repo.get("html_url"),
                    "stars": stars,
                    "language": repo.get("language"),
                    "description": (repo.get("description") or "")[:200],
                }
            )
        top_repos.sort(key=lambda r: r["stars"], reverse=True)

        location = (user.get("location") or "").strip()
        city = country = None
        if location:
            pieces = [p.strip() for p in location.split(",") if p.strip()]
            if len(pieces) >= 2:
                city, country = pieces[0], pieces[-1]
            else:
                city = pieces[0]

        technologies = sorted(languages, key=languages.get, reverse=True)  # type: ignore[arg-type]
        data = {
            "full_name": user.get("name") or user.get("login"),
            "headline": (user.get("bio") or "")[:200] or None,
            "company": (user.get("company") or "").lstrip("@").strip() or None,
            "city": city,
            "country": country,
            "bio": user.get("bio"),
            "public_email": user.get("email"),  # only set if the user made it public
            "github_url": user.get("html_url"),
            "website_url": user.get("blog") or None,
            "avatar_url": user.get("avatar_url"),
            "skills": [],
            "technologies": technologies[:10],
            "social_links": {"github": user.get("html_url")},
            "github_stats": {
                "public_repos": user.get("public_repos", 0),
                "followers": user.get("followers", 0),
                "total_stars": total_stars,
                "top_repos": top_repos[:5],
            },
            "experiences": [],
            "extraction_confidence": 0.9,
        }
        return CollectedProfile(
            data=data,
            source_url=hit.url,
            source_type=SourceType.GITHUB,
            source_title=hit.title or f"GitHub — {login}",
            source_snippet=hit.snippet,
            content_excerpt=(user.get("bio") or "")[:500],
            meta={"api": "github", "login": login},
        )
