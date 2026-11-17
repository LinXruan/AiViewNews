from __future__ import annotations


def test_anonymous_visitor_must_log_in(client):
    assert client.get("/api/me").status_code == 401


def test_guest_entry_works(guest_client):
    me = guest_client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["username"] == "guest"
    assert me.json()["role"] == "user"
    assert guest_client.get("/api/documents").status_code == 200


def test_guest_cannot_reach_admin(guest_client):
    assert guest_client.get("/api/admin/users").status_code == 403
    assert guest_client.get("/api/admin/settings").status_code == 403


def test_api_responses_are_not_cached(client):
    response = client.get("/api/health")
    assert response.headers["cache-control"] == "no-store"


def test_logout_returns_to_login(admin_client):
    assert admin_client.get("/api/me").json()["role"] == "admin"
    assert admin_client.post("/api/logout").status_code == 200
    assert admin_client.get("/api/me").status_code == 401
