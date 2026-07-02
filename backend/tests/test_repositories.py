"""Integration tests: repository layer on an isolated database."""

from __future__ import annotations

from app.models import SourceType
from app.repositories import (
    CandidateRepository,
    UserRepository,
    compute_dedup_hash,
    slugify,
)


def test_slugify():
    assert slugify("Next.js") == "next-js"
    assert slugify("  C++ ") == "c"
    assert slugify("Machine Learning") == "machine-learning"


def test_dedup_hash_prefers_unique_anchors():
    by_github = compute_dedup_hash(full_name="A", github_url="https://github.com/a")
    by_github_case = compute_dedup_hash(full_name="Other", github_url="https://GITHUB.com/a/")
    assert by_github == by_github_case  # anchor normalized, name ignored

    by_name = compute_dedup_hash(full_name="Jane Doe", company="Acme")
    by_name2 = compute_dedup_hash(full_name="jane doe", company="ACME")
    assert by_name == by_name2
    assert by_name != by_github


async def test_upsert_merges_without_overwriting(db_session):
    repo = CandidateRepository(db_session)
    key = compute_dedup_hash(full_name="Jo Smith", github_url="https://github.com/jo")

    first, created = await repo.upsert_by_hash(
        key, full_name="Jo Smith", github_url="https://github.com/jo",
        extraction_confidence=0.4,
    )
    assert created

    second, created2 = await repo.upsert_by_hash(
        key, full_name="Joanna Smith", company="Acme", extraction_confidence=0.9
    )
    assert not created2
    assert second.id == first.id
    assert second.full_name == "Jo Smith"        # existing value kept
    assert second.company == "Acme"              # gap filled
    assert second.extraction_confidence == 0.9   # max wins


async def test_skills_are_slug_deduplicated(db_session):
    repo = CandidateRepository(db_session)
    candidate, _ = await repo.upsert_by_hash("h" * 64, full_name="Skill Person")
    await repo.set_skills(candidate, ["React", "react", "REACT", "TypeScript"])
    detail = await repo.get_detail(candidate.id)
    names = sorted(link.skill.name for link in detail.skills)
    assert names == ["React", "TypeScript"]


async def test_source_duplicates_ignored(db_session):
    repo = CandidateRepository(db_session)
    candidate, _ = await repo.upsert_by_hash("s" * 64, full_name="Source Person")
    first = await repo.add_source(
        candidate, url="https://github.com/sp", source_type=SourceType.GITHUB
    )
    duplicate = await repo.add_source(
        candidate, url="https://github.com/sp", source_type=SourceType.GITHUB
    )
    assert first is not None and duplicate is None


async def test_search_filters(db_session):
    repo = CandidateRepository(db_session)
    a, _ = await repo.upsert_by_hash(
        "a" * 64, full_name="Anna Berlin", country="Germany", city="Berlin",
        years_experience=7, technologies=["react"],
    )
    await repo.set_skills(a, ["React"])
    b, _ = await repo.upsert_by_hash(
        "b" * 64, full_name="Bob Lisbon", country="Portugal", city="Lisbon",
        years_experience=2, technologies=["vue"],
    )
    await repo.set_skills(b, ["Vue"])
    await db_session.commit()

    items, total = await repo.search(filters={"countries": ["germany"]})
    assert total == 1 and items[0].full_name == "Anna Berlin"

    items, total = await repo.search(filters={"skills": ["react"]})
    assert total == 1 and items[0].full_name == "Anna Berlin"

    items, total = await repo.search(filters={"min_years_experience": 5})
    assert total == 1

    items, total = await repo.search(keyword="Lisbon")
    assert total == 1 and items[0].full_name == "Bob Lisbon"


async def test_user_lookup_case_insensitive_email(db_session):
    users = UserRepository(db_session)
    await users.create(email="mixed@case.io", hashed_password="x")
    found = await users.get_by_email("  MIXED@case.io ")
    assert found is not None
