from __future__ import annotations


def test_health_and_login_logout(client):
    assert client.get("/api/health").json() == {"status": "ok"}

    wrong = client.post(
        "/api/login", json={"username": "admin", "password": "wrong-pass"}
    )
    assert wrong.status_code == 401
    assert wrong.json()["error"]["code"] == "invalid_credentials"

    ok = client.post(
        "/api/login", json={"username": "admin", "password": "admin-test-pass"}
    )
    assert ok.status_code == 200
    assert ok.json()["role"] == "admin"
    assert client.get("/api/me").status_code == 200

    assert client.post("/api/logout").status_code == 200
    assert client.get("/api/me").status_code == 401


def test_role_guard(admin_client, demo_client):
    assert admin_client.get("/api/admin/users").status_code == 200
    denied = demo_client.get("/api/admin/users")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "forbidden"
    assert demo_client.get("/api/admin/settings").status_code == 403


def test_settings_mask_and_setup_status(admin_client):
    response = admin_client.get("/api/admin/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["llm"]["api_key_set"] is True
    assert body["llm"]["api_key"].startswith("sk-****")
    assert "sk-test-not-real" not in response.text

    status = admin_client.get("/api/setup/status")
    assert status.status_code == 200
    assert status.json()["llm_ok"] is True


def test_first_admin_channel_closed(client):
    assert client.get("/api/setup/admin").json()["available"] is False
    response = client.post(
        "/api/setup/admin",
        json={
            "username": "intruder",
            "password": "intruder-pass",
            "password_confirm": "intruder-pass",
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "setup_closed"
