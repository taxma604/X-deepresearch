from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

_TEST_TOKEN = "test-bearer-token-with-at-least-32-characters"


@pytest.fixture(autouse=True)
def _http_access_token(monkeypatch):
    monkeypatch.setenv("X_RESEARCH_ACCESS_TOKEN", _TEST_TOKEN)


def _client():
    return TestClient(app, headers={"Authorization": f"Bearer {_TEST_TOKEN}"})


from app.api.dependencies import get_x_service
from app.config import Settings
from app.main import app
from app.services.x_service import XService
from app.x.client import XClient


def test_health_response() -> None:
    response = _client().get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_service_info_does_not_require_cookies() -> None:
    response = _client().get("/")
    assert response.status_code == 200
    assert response.json()["read_only"] is True


def test_search_without_cookies_returns_safe_503() -> None:
    settings = Settings(_env_file=None, ALLOWED_USERS="alice")
    app.dependency_overrides[get_x_service] = lambda: XService(XClient(settings), settings)
    try:
        response = _client().get("/search", params={"q": "from:alice", "pages": 1})
    finally:
        app.dependency_overrides.pop(get_x_service, None)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "auth_not_configured"
    assert "auth_token" not in response.text
    assert "ct0" not in response.text


def test_search_rejects_a_user_outside_the_allowlist() -> None:
    settings = Settings(_env_file=None, ALLOWED_USERS="alice")
    app.dependency_overrides[get_x_service] = lambda: XService(XClient(settings), settings)
    try:
        response = _client().get("/search", params={"q": "from:bob"})
    finally:
        app.dependency_overrides.pop(get_x_service, None)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "search_not_allowed"


def test_search_validates_an_empty_query() -> None:
    response = _client().get("/search", params={"q": ""})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_compatibility_search_emits_research_tweet_shape() -> None:
    class FakeService:
        settings = Settings(_env_file=None, ALLOWED_USERS="alice")

        async def search_pages(self, **_kwargs):
            return [
                SimpleNamespace(
                    id="123",
                    url="https://x.com/alice/status/123",
                    created_at="2026-09-13T00:00:00Z",
                    text="hello",
                    lang="en",
                    user=SimpleNamespace(id="7", name="Alice", screen_name="alice"),
                    favorite_count=3,
                    retweet_count=2,
                    reply_count=1,
                    quote_count=4,
                    view_count=5,
                    bookmark_count=6,
                )
            ], None, 1, None

    app.dependency_overrides[get_x_service] = FakeService
    try:
        response = _client().get("/search", params={"q": "from:alice"})
    finally:
        app.dependency_overrides.pop(get_x_service, None)

    assert response.status_code == 200
    assert response.json()["data"]["items"] == [
        {
            "id": "123",
            "url": "https://x.com/alice/status/123",
            "created_at": "2026-09-13T00:00:00Z",
            "text": "hello",
            "lang": "en",
            "author": {"id": "7", "name": "Alice", "screen_name": "alice"},
            "metrics": {
                "likes": 3,
                "reposts": 2,
                "replies": 1,
                "quotes": 4,
                "views": 5,
                "bookmarks": 6,
            },
            "is_reply": False,
            "is_quote": False,
            "is_repost": False,
        }
    ]


def test_x_routes_are_get_only() -> None:
    paths = app.openapi()["paths"]
    methods = {
        method
        for path, operations in paths.items()
        if path.startswith("/api/v1/x")
        for method in operations
    }
    assert methods == {"get"}
