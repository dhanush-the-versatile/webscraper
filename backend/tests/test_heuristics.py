"""Unit tests: deterministic requirement parsing and profile extraction."""

from __future__ import annotations

import pytest

from app.ai.heuristics import extract_profile_from_text, parse_requirement


@pytest.mark.parametrize(
    ("query", "expectations"),
    [
        (
            "Find React developers with 5+ years experience in Germany",
            {"frameworks": ["react"], "min_years_experience": 5, "countries": ["Germany"]},
        ),
        (
            "Looking for AI Engineers with LangGraph and RAG experience",
            {"frameworks": ["langgraph"], "job_titles": ["Ai Engineer"]},
        ),
        (
            "Need Python freelancers experienced in FastAPI",
            {"programming_languages": ["python"], "employment_type": "freelance"},
        ),
        (
            "Looking for UI Designers specializing in FinTech",
            {"industries": ["fintech"]},
        ),
    ],
)
def test_parse_requirement_examples(query, expectations):
    parsed = parse_requirement(query).model_dump()
    for key, expected in expectations.items():
        if isinstance(expected, list):
            for item in expected:
                assert item in parsed[key], f"{item!r} missing from {key}: {parsed[key]}"
        else:
            assert parsed[key] == expected


def test_parse_requirement_range_and_remote():
    parsed = parse_requirement("Backend dev, 3-6 years, remote, in Amsterdam")
    assert parsed.min_years_experience == 3
    assert parsed.max_years_experience == 6
    assert parsed.remote is True
    assert "Amsterdam" in parsed.cities
    assert "Netherlands" in parsed.countries


def test_parse_requirement_seniority_from_years():
    assert parse_requirement("engineer with 6+ years").seniority == "senior"
    assert parse_requirement("engineer with 1 year").seniority == "junior"


def test_extract_profile_from_page_text():
    text = (
        "Sam Carter - Lead DevOps Engineer\n\n"
        "I'm Sam Carter, a lead devops engineer in Toronto with 9 years of experience "
        "working with kubernetes, terraform and aws.\n\n"
        "Contact: sam@samcarter.io — https://github.com/samcarter"
    )
    profile = extract_profile_from_text(
        text, url="https://samcarter.io", title="Sam Carter - Lead DevOps Engineer"
    )
    assert profile["full_name"] == "Sam Carter"
    assert profile["seniority"] == "lead"
    assert profile["years_experience"] == 9
    assert profile["public_email"] == "sam@samcarter.io"
    assert "kubernetes" in profile["technologies"]
    assert profile["extraction_confidence"] >= 0.5


def test_extract_profile_ignores_absurd_years():
    profile = extract_profile_from_text("A page mentioning 99 years of history")
    assert profile["years_experience"] is None
