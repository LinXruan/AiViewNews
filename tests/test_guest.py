from __future__ import annotations


def test_anonymous_visitor_is_guest(client):
    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["username"] == "guest"
    assert me.json()["role"] == "user"
    assert client.get("/api/documents").status_code == 200


def test_guest_cannot_reach_admin(client):
    assert client.get("/api/admin/users").status_code == 403
    assert client.get("/api/admin/settings").status_code == 403


def test_api_responses_are_not_cached(client):
    response = client.get("/api/documents")
    assert response.headers["cache-control"] == "no-store"


def test_logout_returns_to_guest(admin_client):
    assert admin_client.get("/api/me").json()["role"] == "admin"
    response = admin_client.post("/api/logout")
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "guest"
    assert admin_client.get("/api/me").json()["username"] == "guest"
