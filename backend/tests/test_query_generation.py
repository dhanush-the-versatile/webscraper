"""Unit tests: deterministic search-query generation."""

from __future__ import annotations

from app.ai.query_generation import generate_queries_deterministic
from app.models import SourceType
from app.schemas import ParsedRequirement


def test_generates_site_scoped_queries():
    req = ParsedRequirement(
        job_titles=["React Developer"],
        frameworks=["react"],
        programming_languages=["typescript"],
        countries=["Germany"],
    )
    queries = generate_queries_deterministic(req)
    joined = [q.query for q in queries]
    assert any(q.startswith("site:linkedin.com/in") for q in joined)
    assert any(q.startswith("site:github.com") for q in joined)
    assert any("portfolio" in q for q in joined)
    assert any('"our team"' in q for q in joined)
    assert all("react" in q for q in joined)


def test_design_sources_only_for_design_roles():
    dev = generate_queries_deterministic(ParsedRequirement(job_titles=["Backend Developer"]))
    assert not any(q.source in (SourceType.BEHANCE, SourceType.DRIBBBLE) for q in dev)

    designer = generate_queries_deterministic(
        ParsedRequirement(job_titles=["UI Designer"], skills=["ui design"])
    )
    assert any(q.source == SourceType.BEHANCE for q in designer)
    assert any(q.source == SourceType.DRIBBBLE for q in designer)


def test_data_sources_only_for_data_roles():
    ds = generate_queries_deterministic(
        ParsedRequirement(job_titles=["Data Scientist"], skills=["machine learning"])
    )
    assert any(q.source == SourceType.KAGGLE for q in ds)


def test_city_preferred_over_country_in_location():
    req = ParsedRequirement(frameworks=["react"], countries=["Germany"], cities=["Berlin"])
    queries = generate_queries_deterministic(req)
    assert all('"Berlin"' in q.query for q in queries)


def test_max_queries_respected():
    req = ParsedRequirement(
        job_titles=["Data Scientist"], skills=["machine learning", "ui design"]
    )
    assert len(generate_queries_deterministic(req, max_queries=5)) <= 5
