"""Stack Overflow enrichment via the official StackExchange API."""

from __future__ import annotations

import html
import re

from app.core.logging import get_logger
from app.models import SourceType
from app.schemas import ParsedRequirement
from app.scraping.cache import fetch_cache
from app.scraping.http_client import FetchError, http_client
from app.scraping.models import CollectedProfile, SearchHit
from app.scraping.sources.base import ProfileEnricher

logger = get_logger("scraping.stackoverflow")

_USER_ID_RE = re.compile(r"stackoverflow\.com/users/(\d+)")


class StackOverflowEnricher(ProfileEnricher):
    name = "stackoverflow"

    def matches(self, hit: SearchHit) -> bool:
        return bool(_USER_ID_RE.search(hit.url))

    async def enrich(
        self, hit: SearchHit, requirement: ParsedRequirement
    ) -> CollectedProfile | None:
        match = _USER_ID_RE.search(hit.url)
        if not match:
            return None
        user_id = match.group(1)
        cache_key = f"so:{user_id}"
        data = await fetch_cache.get("stackoverflow", cache_key)
        if data is None:
            try:
                user_payload = await http_client.get_json(
                    f"https://api.stackexchange.com/2.3/users/{user_id}",
                    respect_robots=False,  # official API
                    params={"site": "stackoverflow", "filter": "default"},
                )
                tags_payload = await http_client.get_json(
                    f"https://api.stackexchange.com/2.3/users/{user_id}/top-tags",
                    respect_robots=False,
                    params={"site": "stackoverflow", "pagesize": 10},
                )
                data = {"user": user_payload, "tags": tags_payload}
                await fetch_cache.set("stackoverflow", cache_key, data, ttl=12 * 3600)
            except FetchError as exc:
                logger.warning("stackoverflow_enrich_failed", user=user_id, error=str(exc))
                return None

        users = (data.get("user") or {}).get("items") or []
        if not users:
            return None
        user = users[0]
        tags = [
            item.get("tag_name", "").lower()
            for item in (data.get("tags") or {}).get("items", [])
            if item.get("tag_name")
        ]

        location = (user.get("location") or "").strip()
        city = country = None
        if location:
            pieces = [p.strip() for p in location.split(",") if p.strip()]
            if len(pieces) >= 2:
                city, country = pieces[0], pieces[-1]
            else:
                city = pieces[0]

        display_name = html.unescape(user.get("display_name") or f"SO user {user_id}")
        profile_data = {
            "full_name": display_name,
            "headline": None,
            "city": city,
            "country": country,
            "website_url": user.get("website_url") or None,
            "avatar_url": user.get("profile_image"),
            "skills": [],
            "technologies": tags,
            "social_links": {"stackoverflow": user.get("link")},
            "github_stats": {},
            "experiences": [],
            "extraction_confidence": 0.7,
        }
        return CollectedProfile(
            data=profile_data,
            source_url=hit.url,
            source_type=SourceType.STACKOVERFLOW,
            source_title=hit.title or f"Stack Overflow — {display_name}",
            source_snippet=hit.snippet,
            content_excerpt=f"Reputation {user.get('reputation', 0)}; top tags: {', '.join(tags[:6])}",
            meta={"api": "stackexchange", "reputation": user.get("reputation", 0)},
        )
