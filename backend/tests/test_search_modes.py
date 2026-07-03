"""Integration tests: keyword vs semantic vs hybrid candidate search."""

from __future__ import annotations

from app.ai import embedding_service
from app.repositories import CandidateRepository
from app.schemas import PaginationParams
from app.scraping.browser import fetch_rendered_html
from app.services import CandidateService


async def seed(db_session) -> None:
    repo = CandidateRepository(db_session)
    people = [
        ("Frontend Fran", "react typescript next.js frontend engineer berlin",
         ["react", "typescript"]),
        ("Backend Bora", "python fastapi postgresql backend developer amsterdam",
         ["python", "fastapi"]),
        ("Data Dev", "machine learning pytorch data scientist llm",
         ["machine learning", "pytorch"]),
    ]
    for index, (name, doc, techs) in enumerate(people):
        candidate, _ = await repo.upsert_by_hash(
            f"{index}" * 64, full_name=name, technologies=techs, bio=doc
        )
        candidate.embedding = await embedding_service.embed(doc)
    await db_session.commit()


async def test_semantic_search_orders_by_similarity(db_session):
    await seed(db_session)
    repo = CandidateRepository(db_session)
    query_vec = await embedding_service.embed("react frontend developer typescript")
    ranked = await repo.vector_search(query_vec, limit=3)
    assert ranked[0][0].full_name == "Frontend Fran"
    similarities = [similarity for _, similarity in ranked]
    assert similarities == sorted(similarities, reverse=True)


async def test_hybrid_includes_keyword_and_semantic_hits(db_session):
    await seed(db_session)
    repo = CandidateRepository(db_session)
    # "fastapi" matches Backend Bora by keyword; the embedding also points there
    query_vec = await embedding_service.embed("fastapi python api")
    pairs, total = await repo.hybrid_search(keyword="fastapi", embedding=query_vec)
    assert total >= 1
    assert pairs[0][0].full_name == "Backend Bora"
    scores = [score for _, score in pairs]
    assert scores == sorted(scores, reverse=True)


async def test_service_mode_dispatch(db_session):
    await seed(db_session)
    service = CandidateService(db_session)
    params = PaginationParams(page=1, page_size=10)

    keyword_page = await service.list_candidates(
        keyword="fastapi", params=params, mode="keyword"
    )
    assert keyword_page.total == 1

    semantic_page = await service.list_candidates(
        keyword="frontend react engineer", params=params, mode="semantic"
    )
    assert semantic_page.items[0].full_name == "Frontend Fran"

    hybrid_page = await service.list_candidates(
        keyword="machine learning", params=params, mode="hybrid"
    )
    assert hybrid_page.items[0].full_name == "Data Dev"

    # semantic/hybrid without a query degrade to keyword browse
    fallback = await service.list_candidates(keyword=None, params=params, mode="semantic")
    assert fallback.total == 3


async def test_api_mode_parameter(app_client, auth_headers):
    ok = app_client.get(
        "/api/v1/candidates",
        headers=auth_headers,
        params={"q": "developer", "mode": "hybrid"},
    )
    assert ok.status_code == 200
    assert {"items", "total"} <= set(ok.json())

    bad = app_client.get(
        "/api/v1/candidates", headers=auth_headers, params={"mode": "psychic"}
    )
    assert bad.status_code == 422


async def test_browser_fetch_disabled_by_default():
    assert await fetch_rendered_html("https://example.org/") is None
