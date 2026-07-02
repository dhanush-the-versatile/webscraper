"""API tests: the full search → results → export flow (sample-data mode)."""

from __future__ import annotations

import time

import pytest


@pytest.fixture(scope="module")
def completed_search(app_client, auth_headers) -> dict:
    created = app_client.post(
        "/api/v1/searches",
        headers=auth_headers,
        json={
            "query": "Find senior React developers with TypeScript in Berlin, Germany",
            "max_results": 6,
        },
    )
    assert created.status_code == 202, created.text
    search = created.json()
    assert search["status"] == "pending"

    for _ in range(120):
        current = app_client.get(
            f"/api/v1/searches/{search['id']}", headers=auth_headers
        ).json()
        if current["status"] in ("completed", "failed"):
            return current
        time.sleep(0.25)
    pytest.fail("search did not finish in time")


def test_search_completes_with_parsed_requirement(completed_search):
    assert completed_search["status"] == "completed"
    assert completed_search["result_count"] > 0
    requirement = completed_search["parsed_requirement"]
    assert "react" in requirement["frameworks"]
    assert requirement["seniority"] == "senior"
    assert completed_search["generated_queries"]


def test_results_are_ranked_and_scored(app_client, auth_headers, completed_search):
    response = app_client.get(
        f"/api/v1/searches/{completed_search['id']}/results", headers=auth_headers
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert results

    ranks = [r["rank"] for r in results]
    scores = [r["scores"]["overall_score"] for r in results]
    assert ranks == sorted(ranks)
    assert scores == sorted(scores, reverse=True)
    for result in results:
        assert 0 <= result["scores"]["overall_score"] <= 100
        assert result["summary"]
        assert result["explanation"]
        assert result["candidate"]["full_name"]


def test_min_score_filter(app_client, auth_headers, completed_search):
    unfiltered = app_client.get(
        f"/api/v1/searches/{completed_search['id']}/results", headers=auth_headers
    ).json()["results"]
    threshold = unfiltered[0]["scores"]["overall_score"]
    filtered = app_client.get(
        f"/api/v1/searches/{completed_search['id']}/results",
        headers=auth_headers,
        params={"min_score": threshold},
    ).json()["results"]
    assert all(r["scores"]["overall_score"] >= threshold for r in filtered)
    assert len(filtered) <= len(unfiltered)


def test_search_not_found_for_other_users(app_client, completed_search):
    app_client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "password123"},
    )
    login = app_client.post(
        "/api/v1/auth/login",
        json={"email": "other@example.com", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = app_client.get(
        f"/api/v1/searches/{completed_search['id']}", headers=other_headers
    )
    assert response.status_code == 404


@pytest.mark.parametrize("fmt,content_type", [
    ("csv", "text/csv"),
    ("json", "application/json"),
    ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ("pdf", "application/pdf"),
])
def test_exports_all_formats(app_client, auth_headers, completed_search, fmt, content_type):
    response = app_client.post(
        "/api/v1/exports",
        headers=auth_headers,
        json={"search_id": completed_search["id"], "format": fmt},
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith(content_type)
    assert "attachment" in response.headers["content-disposition"]
    assert len(response.content) > 100


def test_search_validation(app_client, auth_headers):
    too_short = app_client.post(
        "/api/v1/searches", headers=auth_headers, json={"query": "ab"}
    )
    assert too_short.status_code == 422
