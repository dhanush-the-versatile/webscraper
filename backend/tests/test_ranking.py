"""Unit tests: deterministic ranking engine."""

from __future__ import annotations

from app.models import Candidate, Seniority
from app.schemas import ParsedRequirement
from app.services.ranking_service import WEIGHTS, RankingInput, RankingService


def make_candidate(**overrides) -> Candidate:
    defaults = dict(
        full_name="Test Person",
        seniority=Seniority.SENIOR,
        years_experience=6,
        country="Germany",
        city="Berlin",
        technologies=["react", "typescript"],
        social_links={},
        github_stats={},
        dedup_hash="x" * 64,
    )
    defaults.update(overrides)
    return Candidate(**defaults)


def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


def test_perfect_match_scores_high():
    req = ParsedRequirement(
        skills=["react"], programming_languages=["typescript"],
        min_years_experience=5, countries=["Germany"], cities=["Berlin"],
        seniority="senior",
    )
    candidate = make_candidate(
        portfolio_url="https://x.dev",
        bio="long bio " * 30,
        github_url="https://github.com/x",
        github_stats={"public_repos": 50, "followers": 500, "total_stars": 1000},
    )
    breakdown, matched, missing = RankingService().score(
        req, RankingInput(candidate=candidate, candidate_skills=["react", "typescript"])
    )
    assert breakdown.overall_score >= 85
    assert breakdown.skill_match == 100.0
    assert breakdown.location_match == 100.0
    assert "react" in matched and not missing


def test_mismatch_scores_low():
    req = ParsedRequirement(
        skills=["rust", "embedded"], countries=["Japan"], min_years_experience=10
    )
    candidate = make_candidate(years_experience=1, seniority=Seniority.JUNIOR)
    breakdown, matched, missing = RankingService().score(
        req, RankingInput(candidate=candidate, candidate_skills=["php"])
    )
    assert breakdown.overall_score < 40
    assert breakdown.skill_match == 0.0
    assert set(missing) == {"rust", "embedded"}


def test_semantic_score_folds_into_relevance():
    req = ParsedRequirement(skills=["react"])
    candidate = make_candidate()
    service = RankingService()
    low, _, _ = service.score(
        req, RankingInput(candidate=candidate, candidate_skills=["react"], semantic_score=0.1)
    )
    high, _, _ = service.score(
        req, RankingInput(candidate=candidate, candidate_skills=["react"], semantic_score=0.9)
    )
    assert high.relevance_score > low.relevance_score
    assert high.overall_score > low.overall_score


def test_unknown_location_neutral_when_unconstrained():
    req = ParsedRequirement(skills=["react"])
    candidate = make_candidate(country=None, city=None)
    breakdown, _, _ = RankingService().score(
        req, RankingInput(candidate=candidate, candidate_skills=["react"])
    )
    assert breakdown.location_match == 75.0


def test_scores_bounded_0_100():
    req = ParsedRequirement(
        skills=["a", "b", "c"], min_years_experience=20, countries=["Nowhere"]
    )
    candidate = make_candidate(
        years_experience=None, country="Elsewhere", city=None, technologies=[]
    )
    breakdown, _, _ = RankingService().score(
        req, RankingInput(candidate=candidate, candidate_skills=[])
    )
    for value in breakdown.model_dump().values():
        assert 0.0 <= value <= 100.0
