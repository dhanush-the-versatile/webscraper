"""Requirement understanding: natural language → ``ParsedRequirement``."""

from __future__ import annotations

from app.ai import heuristics
from app.ai.provider import get_llm_provider
from app.core.logging import get_logger
from app.schemas import ParsedRequirement

logger = get_logger("ai.understanding")

_SYSTEM_PROMPT = """You are a recruiting requirement parser. Extract structured hiring \
requirements from a recruiter's natural-language query.

Return a JSON object with exactly these keys (use [] / null when absent):
  job_titles: string[]              — normalized role titles
  skills: string[]                  — general skills
  technologies: string[]            — tools/platforms (e.g. docker, aws, graphql)
  frameworks: string[]              — frameworks/libraries (e.g. react, fastapi)
  programming_languages: string[]   — languages (e.g. python, typescript)
  seniority: string|null            — one of intern|junior|mid|senior|lead|principal|executive
  min_years_experience: int|null
  max_years_experience: int|null
  countries: string[]
  cities: string[]
  industries: string[]
  companies: string[]               — target/previous companies if named
  education: string[]
  keywords: string[]                — other salient search terms
  employment_type: string|null      — full-time|part-time|freelance|contract
  remote: bool|null

Lowercase all list values except countries/cities (Title Case). Be precise; do
not invent constraints that are not stated or strongly implied."""


async def parse_requirement(query: str) -> ParsedRequirement:
    """Parse with the configured LLM; fall back to deterministic heuristics."""
    provider = get_llm_provider()
    if provider is not None:
        data = await provider.acomplete_json(
            system=_SYSTEM_PROMPT, user=f"Recruiter query:\n{query}"
        )
        if isinstance(data, dict):
            try:
                parsed = ParsedRequirement(**{
                    k: v for k, v in data.items() if k in ParsedRequirement.model_fields
                })
                logger.info("requirement_parsed", provider=provider.name)
                return parsed
            except Exception as exc:
                logger.warning("requirement_parse_invalid", error=str(exc))

    parsed = heuristics.parse_requirement(query)
    logger.info("requirement_parsed", provider="heuristic")
    return parsed
