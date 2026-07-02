"""Candidate summaries and ranking explanations."""

from __future__ import annotations

from app.ai.provider import get_llm_provider
from app.models import Candidate
from app.schemas import ParsedRequirement, ScoreBreakdown


def _fallback_summary(candidate: Candidate) -> str:
    parts: list[str] = []
    if candidate.headline:
        parts.append(candidate.headline)
    elif candidate.seniority and candidate.seniority.value != "unknown":
        parts.append(f"{candidate.seniority.value.title()} professional")
    if candidate.company:
        parts.append(f"at {candidate.company}")
    location = ", ".join(p for p in (candidate.city, candidate.country) if p)
    if location:
        parts.append(f"based in {location}")
    if candidate.years_experience:
        parts.append(f"with {candidate.years_experience}+ years of experience")
    techs = list(candidate.technologies or [])[:5]
    if techs:
        parts.append(f"Key technologies: {', '.join(techs)}.")
    return " ".join(parts) or "Public professional profile."


def _fallback_explanation(
    breakdown: ScoreBreakdown, matched: list[str], missing: list[str]
) -> str:
    lines = [f"Overall relevance score: {breakdown.overall_score:.0f}/100."]
    if matched:
        lines.append(f"Matches required skills: {', '.join(matched[:6])}.")
    if missing:
        lines.append(f"Not evidenced publicly: {', '.join(missing[:4])}.")
    strongest = max(
        (
            ("skill match", breakdown.skill_match),
            ("experience", breakdown.experience_match),
            ("technology fit", breakdown.technology_match),
            ("location", breakdown.location_match),
            ("GitHub activity", breakdown.github_activity_score),
            ("portfolio", breakdown.portfolio_score),
        ),
        key=lambda item: item[1],
    )
    lines.append(f"Strongest signal: {strongest[0]} ({strongest[1]:.0f}/100).")
    return " ".join(lines)


async def generate_narratives(
    req: ParsedRequirement,
    candidate: Candidate,
    breakdown: ScoreBreakdown,
    matched: list[str],
    missing: list[str],
) -> tuple[str, str]:
    """Return ``(summary, explanation)`` for a ranked candidate.

    Deterministic templates always work; the LLM upgrades wording when present.
    """
    summary = _fallback_summary(candidate)
    explanation = _fallback_explanation(breakdown, matched, missing)

    provider = get_llm_provider()
    if provider is None:
        return summary, explanation

    data = await provider.acomplete_json(
        system=(
            "You write concise recruiter-facing candidate briefs based ONLY on the "
            "provided public data. Return JSON: {\"summary\": str (<=60 words, third "
            "person), \"explanation\": str (<=60 words, why they rank as they do "
            "against the requirement)}. Never invent facts."
        ),
        user=(
            f"Requirement: {req.model_dump_json()}\n"
            f"Candidate: name={candidate.full_name!r}, headline={candidate.headline!r}, "
            f"company={candidate.company!r}, location={candidate.city}/{candidate.country}, "
            f"years={candidate.years_experience}, technologies={list(candidate.technologies or [])[:10]}\n"
            f"Scores: {breakdown.model_dump()}\nMatched: {matched[:8]}\nMissing: {missing[:8]}"
        ),
        max_tokens=512,
    )
    if isinstance(data, dict):
        summary = str(data.get("summary") or summary)[:600]
        explanation = str(data.get("explanation") or explanation)[:600]
    return summary, explanation
