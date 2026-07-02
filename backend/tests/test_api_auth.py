"""API tests: authentication and account endpoints."""

from __future__ import annotations


def test_register_login_me(app_client):
    register = app_client.post(
        "/api/v1/auth/register",
        json={"email": "flow@example.com", "password": "password123", "full_name": "Flow"},
    )
    assert register.status_code == 201
    assert register.json()["email"] == "flow@example.com"

    duplicate = app_client.post(
        "/api/v1/auth/register",
        json={"email": "flow@example.com", "password": "password123"},
    )
    assert duplicate.status_code == 409

    login = app_client.post(
        "/api/v1/auth/login",
        json={"email": "flow@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["token_type"] == "bearer"

    me = app_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["role"] == "recruiter"


def test_login_wrong_password(app_client):
    app_client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpw@example.com", "password": "password123"},
    )
    bad = app_client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@example.com", "password": "nope-nope"},
    )
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "authentication_error"


def test_refresh_flow(app_client, auth_headers):
    login = app_client.post(
        "/api/v1/auth/login",
        json={"email": "tester@example.com", "password": "testpass123"},
    )
    refresh_token = login.json()["refresh_token"]

    refreshed = app_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]

    # an access token is not a valid refresh token
    wrong_kind = app_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login.json()["access_token"]}
    )
    assert wrong_kind.status_code == 401


def test_protected_routes_require_token(app_client):
    for path in ("/api/v1/searches", "/api/v1/saved", "/api/v1/analytics", "/api/v1/history"):
        assert app_client.get(path).status_code == 401

    garbage = app_client.get(
        "/api/v1/searches", headers={"Authorization": "Bearer garbage.token.here"}
    )
    assert garbage.status_code == 401


def test_update_profile(app_client, auth_headers):
    updated = app_client.patch(
        "/api/v1/auth/me", headers=auth_headers, json={"full_name": "Renamed User"}
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Renamed User"
