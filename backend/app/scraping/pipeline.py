"""Collection pipeline: queries → URLs → pages → profiles → dedupe.

Implements the modular flow required by the platform:

    Search Engine → Collect URLs → Visit Public Pages → Extract →
    Clean → Normalize → Deduplicate

Parallelism is bounded by the HTTP client's semaphore; failures in any single
source are isolated and logged, never fatal to the run.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from app.core.logging import get_logger
from app.repositories.candidate_repo import compute_dedup_hash
from app.schemas import GeneratedQuery, ParsedRequirement
from app.scraping.models import CollectedProfile, SearchHit
from app.scraping.sources.base import EnricherRegistry
from app.scraping.sources.github import GitHubEnricher
from app.scraping.sources.search_engines import get_search_providers
from app.scraping.sources.stackoverflow import StackOverflowEnricher
from app.scraping.sources.webpage import (
    GenericWebEnricher,
    LinkedInSnippetEnricher,
    SampleEnricher,
)

logger = get_logger("scraping.pipeline")

_WS_RE = re.compile(r"\s+")


def build_default_registry() -> EnricherRegistry:
    """Assemble the enricher chain — order matters (most specific first)."""
    registry = EnricherRegistry()
    registry.register(SampleEnricher())
    registry.register(GitHubEnricher())
    registry.register(StackOverflowEnricher())
    registry.register(LinkedInSnippetEnricher())
    registry.register(GenericWebEnricher())
    return registry


def _clean_str(value: Any, limit: int = 500) -> str | None:
    if not value:
        return None
    text = _WS_RE.sub(" ", str(value)).strip()
    return text[:limit] or None


def _canonical_url(url: Any) -> str | None:
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return None
    return url.split("#")[0].rstrip("/")[:1024]


def normalize_profile(profile: CollectedProfile) -> CollectedProfile:
    """Clean and normalize extracted fields in place."""
    d = profile.data
    d["full_name"] = _clean_str(d.get("full_name"), 255)
    d["headline"] = _clean_str(d.get("headline"), 512)
    d["company"] = _clean_str(d.get("company"), 255)
    d["city"] = _clean_str(d.get("city"), 120)
    d["country"] = _clean_str(d.get("country"), 120)
    d["bio"] = _clean_str(d.get("bio"), 2000)
    email = _clean_str(d.get("public_email"), 320)
    d["public_email"] = email.lower() if email and "@" in email else None

    for url_key in ("linkedin_url", "github_url", "portfolio_url", "website_url", "avatar_url"):
        d[url_key] = _canonical_url(d.get(url_key))

    d["skills"] = sorted(
        {s.strip().lower() for s in d.get("skills") or [] if s and s.strip()}
    )[:30]
    d["technologies"] = sorted(
        {t.strip().lower() for t in d.get("technologies") or [] if t and t.strip()}
    )[:30]
    d["social_links"] = {
        k: v for k, v in (d.get("social_links") or {}).items()
        if isinstance(v, str) and v.startswith("http")
    }
    return profile


def dedup_key(profile: CollectedProfile) -> str:
    return compute_dedup_hash(
        full_name=profile.data.get("full_name") or "",
        linkedin_url=profile.data.get("linkedin_url"),
        github_url=profile.data.get("github_url"),
        public_email=profile.data.get("public_email"),
        company=profile.data.get("company"),
    )


class CollectionPipeline:
    def __init__(self, registry: EnricherRegistry | None = None) -> None:
        self.registry = registry or build_default_registry()

    # ------------------------------------------------------------------ #
    async def run_searches(
        self, queries: list[GeneratedQuery], *, per_query_limit: int = 8
    ) -> list[SearchHit]:
        """Run all queries across available providers in parallel."""
        providers = get_search_providers()

        async def run_one(provider, query) -> list[SearchHit]:
            try:
                return await provider.search(query, limit=per_query_limit)
            except Exception as exc:
                logger.warning(
                    "search_failed", provider=provider.name, query=query.query, error=str(exc)
                )
                return []

        tasks = [run_one(provider, query) for provider in providers for query in queries]
        results = await asyncio.gather(*tasks)

        seen: set[str] = set()
        hits: list[SearchHit] = []
        for batch in results:
            for hit in batch:
                key = hit.url.split("#")[0].rstrip("/")
                if key and key not in seen:
                    seen.add(key)
                    hits.append(hit)
        logger.info("urls_collected", count=len(hits), queries=len(queries))
        return hits

    # ------------------------------------------------------------------ #
    async def enrich_hits(
        self,
        hits: list[SearchHit],
        requirement: ParsedRequirement,
        *,
        max_profiles: int = 30,
    ) -> list[CollectedProfile]:
        """Visit/enrich hits in parallel and keep successful extractions."""

        async def enrich_one(hit: SearchHit) -> CollectedProfile | None:
            enricher = self.registry.resolve(hit)
            if enricher is None:
                return None
            try:
                return await enricher.enrich(hit, requirement)
            except Exception as exc:
                logger.warning(
                    "enrich_failed", enricher=enricher.name, url=hit.url, error=str(exc)
                )
                return None

        # over-fetch modestly since some hits won't yield a usable profile
        candidates = hits[: max_profiles * 3]
        results = await asyncio.gather(*(enrich_one(hit) for hit in candidates))
        profiles = [p for p in results if p is not None and p.full_name]
        logger.info("profiles_extracted", count=len(profiles), hits=len(candidates))
        return profiles

    # ------------------------------------------------------------------ #
    def deduplicate(self, profiles: list[CollectedProfile]) -> list[CollectedProfile]:
        """Merge profiles that resolve to the same person (first-seen wins base)."""
        merged: dict[str, CollectedProfile] = {}
        for profile in profiles:
            key = dedup_key(profile)
            if key not in merged:
                merged[key] = profile
                continue
            base = merged[key].data
            extra = profile.data
            for field, value in extra.items():
                if value in (None, "", [], {}):
                    continue
                if base.get(field) in (None, "", [], {}):
                    base[field] = value
                elif field in ("skills", "technologies"):
                    base[field] = sorted(set(base[field]) | set(value))[:30]
            merged[key].meta.setdefault("merged_sources", []).append(profile.source_url)
        deduped = list(merged.values())
        logger.info("profiles_deduplicated", before=len(profiles), after=len(deduped))
        return deduped

    # ------------------------------------------------------------------ #
    async def collect(
        self,
        queries: list[GeneratedQuery],
        requirement: ParsedRequirement,
        max_results: int = 30,
    ) -> list[dict[str, Any]]:
        """Full pipeline; returns plain dicts ready for persistence."""
        hits = await self.run_searches(queries)
        profiles = await self.enrich_hits(hits, requirement, max_profiles=max_results)
        profiles = [normalize_profile(p) for p in profiles]
        profiles = self.deduplicate(profiles)[:max_results]
        return [
            {
                **p.data,
                "_source": {
                    "url": p.source_url,
                    "type": p.source_type.value,
                    "title": p.source_title,
                    "snippet": p.source_snippet,
                    "content": p.content_excerpt,
                    "meta": p.meta,
                },
            }
            for p in profiles
        ]


collection_pipeline = CollectionPipeline()
