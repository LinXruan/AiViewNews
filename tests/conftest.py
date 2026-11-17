"""Test fixtures. Never touch the real data directory."""
from __future__ import annotations

import os
import shutil
import tempfile

import pytest

TEST_DATA_DIR = tempfile.mkdtemp(prefix="pdfai-tests-")
os.environ["DATA_DIR"] = TEST_DATA_DIR
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin-test-pass"
os.environ["DEMO_PASSWORD"] = "demo-test-pass"
os.environ["SESSION_SECRET"] = "test-session-secret"
os.environ["DEEPSEEK_API_KEY"] = "sk-test-not-real"
os.environ["DEEPSEEK_BASE_URL"] = "https://api.example.invalid"
os.environ["MINERU_CMD"] = "D:/nonexistent/mineru.exe"
os.environ["MINERU_TIER"] = "flash"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_client():
    context = TestClient(app)
    test_client = context.__enter__()
    response = test_client.post(
        "/api/login", json={"username": "admin", "password": "admin-test-pass"}
    )
    assert response.status_code == 200, response.text
    yield test_client
    context.__exit__(None, None, None)


@pytest.fixture()
def guest_client():
    context = TestClient(app)
    test_client = context.__enter__()
    response = test_client.post("/api/guest")
    assert response.status_code == 200, response.text
    yield test_client
    context.__exit__(None, None, None)


@pytest.fixture()
def demo_client():
    context = TestClient(app)
    test_client = context.__enter__()
    response = test_client.post(
        "/api/login", json={"username": "demo", "password": "demo-test-pass"}
    )
    assert response.status_code == 200, response.text
    yield test_client
    context.__exit__(None, None, None)


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
