"""Integration tests: collection pipeline (sample mode) and normalization."""

from __future__ import annotations

from app.models import SourceType
from app.schemas import GeneratedQuery, ParsedRequirement
from app.scraping import collection_pipeline
from app.scraping.models import CollectedProfile, SearchHit
from app.scraping.pipeline import dedup_key, normalize_profile
from app.scraping.sources.webpage import LinkedInSnippetEnricher


def make_profile(**data) -> CollectedProfile:
    base = {"full_name": "X Y", "skills": [], "technologies": [], "social_links": {}}
    base.update(data)
    return CollectedProfile(
        data=base, source_url="https://example.org/p", source_type=SourceType.PORTFOLIO
    )


def test_normalize_cleans_fields():
    profile = make_profile(
        full_name="  Jane   Doe  ",
        public_email=" JANE@X.IO ",
        skills=["React ", "react", ""],
        github_url="https://github.com/jane/#tab",
        social_links={"github": "https://github.com/jane", "bad": "not-a-url"},
    )
    normalized = normalize_profile(profile).data
    assert normalized["full_name"] == "Jane Doe"
    assert normalized["public_email"] == "jane@x.io"
    assert normalized["skills"] == ["react"]
    assert normalized["github_url"] == "https://github.com/jane"
    assert "bad" not in normalized["social_links"]


def test_dedup_merges_same_person():
    p1 = make_profile(full_name="Jane Doe", github_url="https://github.com/jane")
    p2 = make_profile(
        full_name="Jane Doe", github_url="https://github.com/jane",
        company="Acme", technologies=["react"],
    )
    assert dedup_key(p1) == dedup_key(p2)
    merged = collection_pipeline.deduplicate([p1, p2])
    assert len(merged) == 1
    assert merged[0].data["company"] == "Acme"          # gap filled from second
    assert "react" in merged[0].data["technologies"]


async def test_sample_mode_end_to_end():
    req = ParsedRequirement(frameworks=["react"], countries=["Germany"])
    queries = [GeneratedQuery(query="site:github.com react Germany", source=SourceType.GITHUB)]
    profiles = await collection_pipeline.collect(queries, req, max_results=5)
    assert profiles
    assert len(profiles) <= 5
    for profile in profiles:
        assert profile["full_name"]
        assert profile["_source"]["meta"]["is_sample"] is True
        assert profile["_source"]["url"].startswith("https://example.com/")


async def test_linkedin_enricher_never_fetches():
    """The LinkedIn path must be snippet-only — no HTTP request happens."""
    enricher = LinkedInSnippetEnricher()
    hit = SearchHit(
        url="https://www.linkedin.com/in/sample?utm=x",
        title="Ada Example - Staff Engineer - Amsterdam, Netherlands | LinkedIn",
        snippet="Staff engineer working with python and kubernetes.",
        source=SourceType.LINKEDIN,
    )
    profile = await enricher.enrich(hit, ParsedRequirement(skills=["python"]))
    assert profile is not None
    assert profile.meta["mode"] == "search_snippet_only"
    assert profile.data["full_name"] == "Ada Example"
    assert profile.data["linkedin_url"] == "https://www.linkedin.com/in/sample"
    assert profile.data["country"] == "Netherlands"


async def test_linkedin_enricher_rejects_junk_titles():
    enricher = LinkedInSnippetEnricher()
    hit = SearchHit(
        url="https://www.linkedin.com/in/x",
        title="10 Best React Developers to Follow in 2026 | LinkedIn",
        source=SourceType.LINKEDIN,
    )
    assert await enricher.enrich(hit, ParsedRequirement()) is None
