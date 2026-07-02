"""API tests: candidates browse, saved, notes, history, analytics."""

from __future__ import annotations

import time

import pytest


@pytest.fixture(scope="module")
def candidate_id(app_client, auth_headers) -> str:
    """Ensure at least one candidate exists via a quick sample-mode search."""
    created = app_client.post(
        "/api/v1/searches",
        headers=auth_headers,
        json={"query": "Need Python backend developers in Amsterdam", "max_results": 4},
    )
    search_id = created.json()["id"]
    for _ in range(120):
        status = app_client.get(f"/api/v1/searches/{search_id}", headers=auth_headers).json()
        if status["status"] in ("completed", "failed"):
            break
        time.sleep(0.25)
    results = app_client.get(
        f"/api/v1/searches/{search_id}/results", headers=auth_headers
    ).json()["results"]
    assert results
    return results[0]["candidate"]["id"]


def test_candidate_detail(app_client, auth_headers, candidate_id):
    response = app_client.get(f"/api/v1/candidates/{candidate_id}", headers=auth_headers)
    assert response.status_code == 200
    detail = response.json()
    assert detail["full_name"]
    assert isinstance(detail["skills"], list)
    assert detail["sources"] and detail["sources"][0]["url"]

    missing = app_client.get("/api/v1/candidates/nonexistent", headers=auth_headers)
    assert missing.status_code == 404


def test_candidate_browse_and_filters(app_client, auth_headers, candidate_id):
    everyone = app_client.get("/api/v1/candidates", headers=auth_headers).json()
    assert everyone["total"] >= 1

    by_skill = app_client.get(
        "/api/v1/candidates", headers=auth_headers, params={"skills": ["python"]}
    ).json()
    assert by_skill["total"] >= 1

    nobody = app_client.get(
        "/api/v1/candidates", headers=auth_headers, params={"countries": ["Atlantis"]}
    ).json()
    assert nobody["total"] == 0


def test_saved_lifecycle(app_client, auth_headers, candidate_id):
    saved = app_client.post(
        "/api/v1/saved", headers=auth_headers,
        json={"candidate_id": candidate_id, "tags": ["python", "priority"]},
    )
    assert saved.status_code == 201
    assert saved.json()["tags"] == ["python", "priority"]

    again = app_client.post(
        "/api/v1/saved", headers=auth_headers, json={"candidate_id": candidate_id}
    )
    assert again.status_code == 409

    listing = app_client.get("/api/v1/saved", headers=auth_headers).json()
    assert any(item["candidate"]["id"] == candidate_id for item in listing["items"])

    removed = app_client.delete(f"/api/v1/saved/{candidate_id}", headers=auth_headers)
    assert removed.status_code == 200
    assert app_client.delete(
        f"/api/v1/saved/{candidate_id}", headers=auth_headers
    ).status_code == 404


def test_notes_lifecycle(app_client, auth_headers, candidate_id):
    created = app_client.post(
        "/api/v1/notes", headers=auth_headers,
        json={"candidate_id": candidate_id, "body": "Call on Monday."},
    )
    assert created.status_code == 201
    note_id = created.json()["id"]

    updated = app_client.patch(
        f"/api/v1/notes/{note_id}", headers=auth_headers, json={"body": "Called — positive."}
    )
    assert updated.json()["body"] == "Called — positive."

    notes = app_client.get(
        f"/api/v1/notes/candidate/{candidate_id}", headers=auth_headers
    ).json()
    assert len(notes) == 1

    assert app_client.delete(f"/api/v1/notes/{note_id}", headers=auth_headers).status_code == 200
    assert app_client.get(
        f"/api/v1/notes/candidate/{candidate_id}", headers=auth_headers
    ).json() == []


def test_history_records_actions(app_client, auth_headers):
    history = app_client.get("/api/v1/history", headers=auth_headers).json()
    actions = {item["action"] for item in history["items"]}
    assert "search.created" in actions
    assert "candidate.saved" in actions


def test_analytics_overview_shape(app_client, auth_headers):
    analytics = app_client.get("/api/v1/analytics", headers=auth_headers).json()
    assert analytics["total_searches"] >= 1
    assert analytics["total_candidates"] >= 1
    assert isinstance(analytics["top_skills"], list)
    assert isinstance(analytics["searches_over_time"], list)
    assert {p["label"] for p in analytics["score_distribution"]} == {
        "0-20", "20-40", "40-60", "60-80", "80-100",
    }


def test_pagination_envelope(app_client, auth_headers):
    page = app_client.get(
        "/api/v1/candidates", headers=auth_headers, params={"page": 1, "page_size": 2}
    ).json()
    assert page["page"] == 1 and page["page_size"] == 2
    assert len(page["items"]) <= 2
