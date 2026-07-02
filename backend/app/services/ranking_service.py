"""Deterministic candidate scoring.

Produces the 0-100 score breakdown for a candidate against a parsed
requirement. The AI layer can additionally supply a semantic relevance signal
(embedding similarity or LLM judgement) which is folded into the overall
score; when absent, the deterministic components alone are used, so ranking
always works — with or without AI credentials.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.models import Candidate, Seniority
from app.schemas import ParsedRequirement, ScoreBreakdown

# Overall-score weights (must sum to 1.0)
WEIGHTS = {
    "skill_match": 0.28,
    "experience_match": 0.15,
    "technology_match": 0.15,
    "location_match": 0.12,
    "portfolio_score": 0.08,
    "github_activity_score": 0.10,
    "relevance_score": 0.12,
}

_SENIORITY_ORDER = [
    Seniority.INTERN,
    Seniority.JUNIOR,
    Seniority.MID,
    Seniority.SENIOR,
    Seniority.LEAD,
    Seniority.PRINCIPAL,
    Seniority.EXECUTIVE,
]

_SENIORITY_YEARS = {
    "intern": 0, "junior": 1, "mid": 3, "senior": 5,
    "lead": 7, "principal": 9, "executive": 10,
}


def _norm(items: list[str]) -> set[str]:
    return {i.strip().lower() for i in items if i and i.strip()}


def _overlap_score(required: set[str], present: set[str]) -> tuple[float, list[str], list[str]]:
    """Fraction of required items present, with fuzzy substring credit."""
    if not required:
        return 75.0, [], []  # nothing required → neutral-positive
    matched, missing = [], []
    for req in sorted(required):
        hit = req in present or any(req in p or p in req for p in present)
        (matched if hit else missing).append(req)
    return 100.0 * len(matched) / len(required), matched, missing


@dataclass
class RankingInput:
    candidate: Candidate
    candidate_skills: list[str]
    semantic_score: float | None = None  # 0..1 from embeddings / LLM


class RankingService:
    """Stateless scoring engine (pure functions over inputs)."""

    def score(self, req: ParsedRequirement, inp: RankingInput) -> tuple[ScoreBreakdown, list[str], list[str]]:
        cand = inp.candidate
        cand_skills = _norm(inp.candidate_skills) | _norm(list(cand.technologies or []))

        skill_score, matched, missing = _overlap_score(_norm(req.skills) | _norm(req.keywords), cand_skills)
        tech_required = _norm(req.technologies) | _norm(req.frameworks) | _norm(req.programming_languages)
        tech_score, tech_matched, tech_missing = _overlap_score(tech_required, cand_skills)

        breakdown = ScoreBreakdown(
            skill_match=round(skill_score, 1),
            technology_match=round(tech_score, 1),
            experience_match=round(self._experience_score(req, cand), 1),
            location_match=round(self._location_score(req, cand), 1),
            portfolio_score=round(self._portfolio_score(cand), 1),
            github_activity_score=round(self._github_score(cand), 1),
            relevance_score=round(self._relevance_score(inp, skill_score, tech_score), 1),
        )
        breakdown.overall_score = round(
            sum(getattr(breakdown, key) * w for key, w in WEIGHTS.items()), 1
        )
        all_matched = sorted(set(matched) | set(tech_matched))
        all_missing = sorted(set(missing) | set(tech_missing))
        return breakdown, all_matched, all_missing

    # ------------------------------------------------------------------ #
    # Components (each returns 0-100)
    # ------------------------------------------------------------------ #
    def _experience_score(self, req: ParsedRequirement, cand: Candidate) -> float:
        years = cand.years_experience
        if years is None and cand.seniority != Seniority.UNKNOWN:
            years = _SENIORITY_YEARS.get(cand.seniority.value)

        score = 50.0  # unknown → neutral
        if req.min_years_experience is not None and years is not None:
            if years >= req.min_years_experience:
                score = 100.0
                if req.max_years_experience and years > req.max_years_experience:
                    score = 80.0  # overqualified, still strong
            else:
                score = max(0.0, 100.0 * years / max(req.min_years_experience, 1))
        elif years is not None:
            score = min(100.0, 40.0 + years * 8.0)

        # Seniority alignment bonus/penalty
        if req.seniority and cand.seniority != Seniority.UNKNOWN:
            try:
                want = _SENIORITY_ORDER.index(Seniority(req.seniority.lower()))
                have = _SENIORITY_ORDER.index(cand.seniority)
                score = max(0.0, min(100.0, score - 12.0 * abs(want - have) + (6.0 if want == have else 0.0)))
            except ValueError:
                pass
        return score

    def _location_score(self, req: ParsedRequirement, cand: Candidate) -> float:
        if not req.countries and not req.cities:
            return 75.0  # location not constrained
        country = (cand.country or "").lower()
        city = (cand.city or "").lower()
        if req.cities and city and city in _norm(req.cities):
            return 100.0
        if req.countries and country and country in _norm(req.countries):
            return 90.0 if req.cities else 100.0
        if not country and not city:
            return 40.0  # unknown location under a constraint
        return 10.0

    def _portfolio_score(self, cand: Candidate) -> float:
        score = 0.0
        if cand.portfolio_url or cand.website_url:
            score += 45.0
        if cand.bio and len(cand.bio) > 120:
            score += 25.0
        elif cand.bio:
            score += 12.0
        links = cand.social_links or {}
        score += min(30.0, 10.0 * len([v for v in links.values() if v]))
        return min(100.0, score)

    def _github_score(self, cand: Candidate) -> float:
        stats = cand.github_stats or {}
        if not stats and not cand.github_url:
            return 30.0  # unknown, mild prior
        repos = float(stats.get("public_repos", 0) or 0)
        followers = float(stats.get("followers", 0) or 0)
        stars = float(stats.get("total_stars", 0) or 0)
        # log-scaled so mega-accounts don't dominate
        score = (
            25.0 * min(1.0, math.log1p(repos) / math.log1p(50))
            + 35.0 * min(1.0, math.log1p(followers) / math.log1p(500))
            + 30.0 * min(1.0, math.log1p(stars) / math.log1p(1000))
        )
        if cand.github_url:
            score += 10.0
        return min(100.0, score)

    def _relevance_score(self, inp: RankingInput, skill: float, tech: float) -> float:
        if inp.semantic_score is not None:
            return max(0.0, min(100.0, inp.semantic_score * 100.0))
        # Fallback: blend of the strongest deterministic signals
        return 0.6 * skill + 0.4 * tech
