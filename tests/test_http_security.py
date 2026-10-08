import pytest
from fastapi.testclient import TestClient

from app.main import app

TEST_TOKEN = "test-bearer-token-with-at-least-32-characters"


@pytest.mark.parametrize("path", ["/search?q=from:alice", "/api/v1/x/user/alice", "/openapi.json", "/mcp"])
def test_no_token_returns_503_before_service_access(monkeypatch, path):
    monkeypatch.delenv("X_RESEARCH_ACCESS_TOKEN", raising=False)
    response = TestClient(app).get(path)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "http_auth_not_configured"


def test_invalid_token_returns_401_without_hitting_x(monkeypatch):
    monkeypatch.setenv("X_RESEARCH_ACCESS_TOKEN", TEST_TOKEN)
    response = TestClient(app).get("/api/v1/x/user/alice", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_service_health_remains_public_without_token(monkeypatch):
    monkeypatch.delenv("X_RESEARCH_ACCESS_TOKEN", raising=False)
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200


def test_short_token_is_rejected(monkeypatch):
    monkeypatch.setenv("X_RESEARCH_ACCESS_TOKEN", "short")
    assert TestClient(app).get("/openapi.json").status_code == 503


def test_post_root_is_not_a_public_auth_bypass(monkeypatch):
    monkeypatch.setenv("X_RESEARCH_ACCESS_TOKEN", TEST_TOKEN)
    response = TestClient(app).post("/", data="irrelevant")
    assert response.status_code == 401


def test_exact_bearer_header_required(monkeypatch):
    monkeypatch.setenv("X_RESEARCH_ACCESS_TOKEN", TEST_TOKEN)
    for authorization in (
        "Basic " + TEST_TOKEN,
        "Bearer " + TEST_TOKEN + "suffix",
        "bearer " + TEST_TOKEN,
        "Bearer",
    ):
        response = TestClient(app).get(
            "/openapi.json", headers={"Authorization": authorization}
        )
        assert response.status_code == 401
    response = TestClient(app).get(
        "/openapi.json", headers={"Authorization": "Bearer " + TEST_TOKEN}
    )
    assert response.status_code == 200
