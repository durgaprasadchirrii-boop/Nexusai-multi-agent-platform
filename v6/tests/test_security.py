
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.security import SecurityMiddleware


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("NEXUSAI_API_KEY", "test-secret")
    monkeypatch.setenv("NEXUSAI_RATE_LIMIT", "2")
    monkeypatch.setenv("NEXUSAI_RATE_WINDOW_SECONDS", "60")

    test_app = FastAPI()
    test_app.add_middleware(SecurityMiddleware)

    @test_app.get("/health")
    def health():
        return {"status": "healthy"}

    @test_app.post("/api/test")
    def protected_endpoint():
        return {"ok": True}

    with TestClient(test_app) as test_client:
        yield test_client


def test_health_is_public(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_api_rejects_missing_key(client):
    response = client.post("/api/test")
    assert response.status_code == 401


def test_api_accepts_valid_key(client):
    response = client.post(
        "/api/test",
        headers={"X-API-Key": "test-secret"},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_api_rejects_invalid_key(client):
    response = client.post(
        "/api/test",
        headers={"X-API-Key": "wrong-secret"},
    )
    assert response.status_code == 401


def test_rate_limit_is_enforced(client):
    headers = {"X-API-Key": "test-secret"}

    first = client.post("/api/test", headers=headers)
    second = client.post("/api/test", headers=headers)
    third = client.post("/api/test", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
