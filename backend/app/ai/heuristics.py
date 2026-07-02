"""Deterministic (no-LLM) implementations of the AI capabilities.

These power the platform when no API key is configured and act as the safety
net when an LLM call fails or returns malformed output. They are pure
functions — fast, testable, and side-effect free.
"""

from __future__ import annotations

import re

from app.ai.taxonomy import (
    COUNTRIES,
    EMPLOYMENT_TYPES,
    INDUSTRIES,
    JOB_TITLES,
    SENIORITY_KEYWORDS,
    TECH_TAXONOMY,
)
from app.schemas import ParsedRequirement

# Pre-sorted longest-first so multi-word entries win over substrings.
_TECH_KEYS = sorted(TECH_TAXONOMY, key=len, reverse=True)
_TITLES = sorted(JOB_TITLES, key=len, reverse=True)
_INDUSTRIES = sorted(INDUSTRIES, key=len, reverse=True)

_CITY_TO_COUNTRY: dict[str, str] = {
    alias: country for country, aliases in COUNTRIES.items() for alias in aliases
}

_YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE)
_RANGE_RE = re.compile(r"(\d{1,2})\s*[-–to]+\s*(\d{1,2})\s*(?:years?|yrs?)", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")


def _find_terms(
    text_lower: str, vocabulary: list[str], *, allow_plural: bool = False
) -> list[str]:
    """Find vocabulary terms present in text using word boundaries."""
    found: list[str] = []
    suffix = r"s?(?![a-z0-9])" if allow_plural else r"(?![a-z0-9])"
    for term in vocabulary:
        pattern = r"(?<![a-z0-9])" + re.escape(term) + suffix
        if re.search(pattern, text_lower):
            found.append(term)
    return found


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return list(seen)


def parse_requirement(text: str) -> ParsedRequirement:
    """Extract a structured requirement from natural language, offline."""
    lower = f" {text.lower().strip()} "

    # ---- Technologies / skills ----
    tech_found = _find_terms(lower, _TECH_KEYS)
    skills, technologies, frameworks, languages = [], [], [], []
    for term in tech_found:
        category = TECH_TAXONOMY[term]
        if category == "language":
            languages.append(term)
        elif category == "framework":
            frameworks.append(term)
        elif category in ("technology", "tool"):
            technologies.append(term)
        else:
            skills.append(term)

    # ---- Titles ----
    titles = _find_terms(lower, _TITLES, allow_plural=True)
    # keep the most specific (longest) titles only, drop ones contained in another match
    titles = [t for t in titles if not any(t != o and t in o for o in titles)]

    # ---- Seniority ----
    seniority = None
    for keyword, level in SENIORITY_KEYWORDS.items():
        if keyword in lower:
            seniority = level
            break

    # ---- Years of experience ----
    min_years = max_years = None
    if m := _RANGE_RE.search(text):
        min_years, max_years = int(m.group(1)), int(m.group(2))
    elif m := _YEARS_RE.search(text):
        min_years = int(m.group(1))
    if min_years and not seniority:
        seniority = (
            "junior" if min_years <= 2 else "mid" if min_years <= 4
            else "senior" if min_years <= 7 else "principal"
        )

    # ---- Location ----
    countries, cities = [], []
    for country in COUNTRIES:
        if re.search(r"(?<![a-z])" + re.escape(country) + r"(?![a-z])", lower):
            countries.append(country)
    for alias, country in _CITY_TO_COUNTRY.items():
        if len(alias) < 3:
            continue
        if re.search(r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])", lower):
            if alias in ("usa", "us", "uk", "uae"):
                countries.append(country)
            else:
                cities.append(alias)
                countries.append(country)
    countries = _dedupe_keep_order(countries)
    cities = _dedupe_keep_order(cities)

    # ---- Industry ----
    industries = _dedupe_keep_order(_find_terms(lower, _INDUSTRIES))
    # drop bare "ai" if a more specific industry ("healthcare ai") matched
    if len(industries) > 1:
        industries = [i for i in industries if not any(i != o and i in o for o in industries)]

    # ---- Employment type / remote ----
    employment_type = next((v for k, v in EMPLOYMENT_TYPES.items() if k in lower), None)
    remote = True if re.search(r"(?<![a-z])remote(?![a-z])", lower) else None

    # ---- Keywords: salient leftover tokens ----
    keywords = _dedupe_keep_order(
        [t for t in titles]
        + [i for i in industries]
    )

    return ParsedRequirement(
        job_titles=[t.title() for t in titles],
        skills=_dedupe_keep_order(skills),
        technologies=_dedupe_keep_order(technologies),
        frameworks=_dedupe_keep_order(frameworks),
        programming_languages=_dedupe_keep_order(languages),
        seniority=seniority,
        min_years_experience=min_years,
        max_years_experience=max_years,
        countries=[c.title() for c in countries],
        cities=[c.title() for c in cities],
        industries=industries,
        companies=[],
        education=[],
        keywords=keywords,
        employment_type=employment_type,
        remote=remote,
    )


# --------------------------------------------------------------------------- #
# Profile extraction fallback
# --------------------------------------------------------------------------- #
_NAME_PATTERNS = [
    re.compile(r"^([A-Z][a-zA-Z'’-]+(?:\s+[A-Z][a-zA-Z'’-]+){1,3})\s*[-–|•·]", re.MULTILINE),
    re.compile(r"(?:I am|I'm|My name is)\s+([A-Z][a-zA-Z'’-]+(?:\s+[A-Z][a-zA-Z'’-]+){0,2})"),
]

_SOCIAL_HOSTS = {
    "linkedin.com": "linkedin",
    "github.com": "github",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "medium.com": "medium",
    "dev.to": "devto",
    "stackoverflow.com": "stackoverflow",
    "kaggle.com": "kaggle",
    "behance.net": "behance",
    "dribbble.com": "dribbble",
    "scholar.google.com": "scholar",
}


def extract_profile_from_text(text: str, *, url: str = "", title: str = "") -> dict:
    """Best-effort structured profile from raw public page text."""
    lower = f" {text.lower()} "

    # Name: prefer the page title pattern "Jane Doe - Senior Engineer | Site"
    full_name = None
    title_head = re.split(r"[|\-–•·:]", title)[0].strip() if title else ""
    if 2 <= len(title_head.split()) <= 4 and re.fullmatch(r"[A-Za-z'’. -]+", title_head or " "):
        if title_head[:1].isupper():
            full_name = title_head
    if not full_name:
        for pat in _NAME_PATTERNS:
            if m := pat.search(text[:2000]):
                full_name = m.group(1).strip()
                break

    # Headline: text right after the name in the title, else first title-ish line
    headline = None
    if title and full_name and title.lower().startswith(full_name.lower()):
        rest = title[len(full_name):].strip(" -–|•·:")
        rest = re.split(r"[|•·]", rest)[0].strip(" -–:")
        headline = rest[:200] or None
    if not headline:
        found_titles = _find_terms(lower, _TITLES)
        headline = found_titles[0].title() if found_titles else None

    # Seniority / years
    seniority = next((lvl for kw, lvl in SENIORITY_KEYWORDS.items() if kw in lower), None)
    years = None
    if m := _YEARS_RE.search(text):
        candidate_years = int(m.group(1))
        if candidate_years <= 40:
            years = candidate_years

    # Skills
    tech_found = _find_terms(lower, _TECH_KEYS)

    # Location
    country = city = None
    for c in COUNTRIES:
        if re.search(r"(?<![a-z])" + re.escape(c) + r"(?![a-z])", lower):
            country = c.title()
            break
    for alias, c in _CITY_TO_COUNTRY.items():
        if len(alias) >= 4 and re.search(r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])", lower):
            city = alias.title()
            country = country or c.title()
            break

    # Public email & links
    emails = _EMAIL_RE.findall(text)
    public_email = emails[0] if emails else None
    links = _URL_RE.findall(text)
    social: dict[str, str] = {}
    linkedin_url = github_url = None
    for link in links:
        for host, key in _SOCIAL_HOSTS.items():
            if host in link:
                social.setdefault(key, link.rstrip(".,);"))
                break
    linkedin_url = social.get("linkedin")
    github_url = social.get("github")

    # Bio: first substantial paragraph
    bio = None
    for para in re.split(r"\n\s*\n", text):
        cleaned = para.strip()
        if 80 <= len(cleaned) <= 1200:
            bio = cleaned
            break

    confidence = 0.2
    if full_name:
        confidence += 0.3
    if tech_found:
        confidence += 0.2
    if headline:
        confidence += 0.15
    if country or city:
        confidence += 0.15

    return {
        "full_name": full_name,
        "headline": headline,
        "company": None,
        "seniority": seniority,
        "years_experience": years,
        "country": country,
        "city": city,
        "skills": [t for t in tech_found if TECH_TAXONOMY[t] == "skill"],
        "technologies": tech_found,
        "public_email": public_email,
        "linkedin_url": linkedin_url,
        "github_url": github_url,
        "social_links": social,
        "bio": bio,
        "extraction_confidence": round(min(confidence, 0.95), 2),
    }
