from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_register_then_delete_account():
    with TestClient(app) as client:
        response = client.post(
            "/api/register", json={"username": "tempuser", "password": "temp-pass"}
        )
        assert response.status_code == 200
        assert response.json()["role"] == "user"
        assert client.get("/api/me").status_code == 200
        assert client.delete("/api/me").status_code == 200
        assert client.get("/api/me").status_code == 401
        assert client.post(
            "/api/login", json={"username": "tempuser", "password": "temp-pass"}
        ).status_code == 401


def test_guest_cannot_delete_account(guest_client):
    response = guest_client.delete("/api/me")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "guest_delete"


def test_change_avatar_color(demo_client):
    response = demo_client.patch("/api/me/avatar-color", json={"avatar_color": "#1D4ED8"})
    assert response.status_code == 200
    assert response.json()["avatar_color"] == "#1d4ed8"
    assert demo_client.get("/api/me").json()["avatar_color"] == "#1d4ed8"


def test_reject_invalid_avatar_color(demo_client):
    for value in ("red", "#12345", "#gggggg", "javascript:alert(1)"):
        response = demo_client.patch("/api/me/avatar-color", json={"avatar_color": value})
        assert response.status_code == 400, value
        assert response.json()["error"]["code"] == "invalid_color", value


def test_guest_cannot_change_avatar_color(guest_client):
    response = guest_client.patch("/api/me/avatar-color", json={"avatar_color": "#1d4ed8"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "guest_color"
