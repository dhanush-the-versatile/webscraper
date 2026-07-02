"""Search-query generation: ``ParsedRequirement`` → optimized per-source queries.

Deterministic templates cover every supported public source; when an LLM is
configured it may add a few creative variants on top. Templates are kept
data-driven so new sources slot in with one line.
"""

from __future__ import annotations

from app.ai.provider import get_llm_provider
from app.core.logging import get_logger
from app.models import SourceType
from app.schemas import GeneratedQuery, ParsedRequirement

logger = get_logger("ai.querygen")

# (site restriction, source type, rationale)
_SITE_TEMPLATES: list[tuple[str, SourceType, str]] = [
    ("site:linkedin.com/in", SourceType.LINKEDIN, "Public LinkedIn profiles"),
    ("site:github.com", SourceType.GITHUB, "GitHub developer profiles"),
    ("site:stackoverflow.com/users", SourceType.STACKOVERFLOW, "Stack Overflow users"),
    ("site:kaggle.com", SourceType.KAGGLE, "Kaggle data-science profiles"),
    ("site:medium.com", SourceType.MEDIUM, "Technical authors on Medium"),
    ("site:dev.to", SourceType.DEVTO, "Dev.to community authors"),
    ("site:behance.net", SourceType.BEHANCE, "Behance design portfolios"),
    ("site:dribbble.com", SourceType.DRIBBBLE, "Dribbble design portfolios"),
    ("site:scholar.google.com", SourceType.RESEARCH, "Research profiles"),
]

_DESIGN_HINTS = {"ui design", "ux design", "ui/ux", "figma", "design systems",
                 "ui designer", "ux designer", "product designer", "graphic designer"}
_DATA_HINTS = {"machine learning", "data science", "data scientist", "kaggle", "llm",
               "deep learning", "nlp", "ai engineer", "data engineer"}


def _core_terms(req: ParsedRequirement) -> list[str]:
    """Assemble the highest-signal terms, most specific first."""
    terms: list[str] = []
    if req.job_titles:
        terms.append(f'"{req.job_titles[0]}"')
    terms.extend(req.frameworks[:2])
    terms.extend(req.programming_languages[:2])
    terms.extend(t for t in req.technologies[:2] if t not in terms)
    terms.extend(s for s in req.skills[:2] if s not in terms)
    if not terms and req.keywords:
        terms.extend(req.keywords[:3])
    return terms


def _location_terms(req: ParsedRequirement) -> list[str]:
    loc: list[str] = []
    if req.cities:
        loc.append(f'"{req.cities[0]}"')
    elif req.countries:
        loc.append(f'"{req.countries[0]}"')
    return loc


def _is_relevant(source: SourceType, req: ParsedRequirement) -> bool:
    """Skip source templates that clearly don't match the requirement domain."""
    haystack = " ".join(
        req.job_titles + req.skills + req.technologies + req.keywords
    ).lower()
    if source in (SourceType.BEHANCE, SourceType.DRIBBBLE):
        return any(h in haystack for h in _DESIGN_HINTS)
    if source in (SourceType.KAGGLE, SourceType.RESEARCH):
        return any(h in haystack for h in _DATA_HINTS)
    return True


def generate_queries_deterministic(
    req: ParsedRequirement, *, max_queries: int = 12
) -> list[GeneratedQuery]:
    core = _core_terms(req)
    location = _location_terms(req)
    extra: list[str] = []
    if req.industries:
        extra.append(req.industries[0])
    if req.employment_type:
        extra.append(req.employment_type)

    base = " ".join(core + location + extra).strip()
    queries: list[GeneratedQuery] = []

    for site, source, rationale in _SITE_TEMPLATES:
        if len(queries) >= max_queries - 2:
            break
        if not _is_relevant(source, req):
            continue
        queries.append(
            GeneratedQuery(query=f"{site} {base}".strip(), source=source, rationale=rationale)
        )

    # Open-web variants: personal portfolios and team pages
    queries.append(
        GeneratedQuery(
            query=f"{base} portfolio OR resume OR cv -jobs -hiring",
            source=SourceType.PORTFOLIO,
            rationale="Personal portfolio sites",
        )
    )
    queries.append(
        GeneratedQuery(
            query=f'{base} "our team" OR "meet the team"',
            source=SourceType.COMPANY,
            rationale="Company team pages",
        )
    )
    return queries[:max_queries]


async def generate_queries(
    req: ParsedRequirement, *, max_queries: int = 12
) -> list[GeneratedQuery]:
    """Deterministic templates, optionally enriched by the LLM."""
    queries = generate_queries_deterministic(req, max_queries=max_queries)

    provider = get_llm_provider()
    if provider is not None and len(queries) < max_queries:
        data = await provider.acomplete_json(
            system=(
                "You generate web-search queries for sourcing job candidates from "
                "public sites. Return JSON: {\"queries\": [{\"query\": str, "
                "\"source\": str, \"rationale\": str}]} — up to 3 additional queries "
                "that meaningfully differ from the provided ones. source must be one "
                "of: linkedin, github, stackoverflow, kaggle, medium, devto, behance, "
                "dribbble, portfolio, company, research, search_engine."
            ),
            user=(
                f"Requirement: {req.model_dump_json()}\n"
                f"Existing queries: {[q.query for q in queries]}"
            ),
        )
        if isinstance(data, dict):
            for item in data.get("queries", [])[: max_queries - len(queries)]:
                try:
                    queries.append(
                        GeneratedQuery(
                            query=str(item["query"])[:400],
                            source=SourceType(item.get("source", "search_engine")),
                            rationale=item.get("rationale"),
                        )
                    )
                except (KeyError, ValueError):
                    continue
    logger.info("queries_generated", count=len(queries))
    return queries
