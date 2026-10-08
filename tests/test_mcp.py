from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

_TEST_TOKEN = "test-bearer-token-with-at-least-32-characters"


@pytest.fixture(autouse=True)
def _http_access_token(monkeypatch):
    monkeypatch.setenv("X_RESEARCH_ACCESS_TOKEN", _TEST_TOKEN)


def _client():
    return TestClient(app, headers={"Authorization": f"Bearer {_TEST_TOKEN}"})

from mcp import Client

from app import mcp_server
from app.main import app
from app.mcp_server import mcp


async def test_mcp_exposes_read_only_x_tools() -> None:
    async with Client(mcp) as client:
        result = await client.list_tools()

    assert {tool.name for tool in result.tools} == {
        "search_x_posts",
        "get_x_user_posts",
        "get_x_user_profile",
        "get_x_post",
        "search_x_posts_daily_stats",
        "start_x_posts_daily_stats",
        "get_x_posts_daily_stats_job",
        "summarize_x_research_job",
        "compare_x_research_jobs",
        "export_x_research_job",
    }
    start_tool = next(tool for tool in result.tools if tool.name == "start_x_posts_daily_stats")
    assert "complete_range" in start_tool.input_schema["properties"]
    assert start_tool.input_schema["properties"]["complete_range"]["default"] is True


async def test_daily_stats_job_tool_defaults_to_complete_range(monkeypatch) -> None:
    calls = []

    def start_job(service, **kwargs):
        calls.append(kwargs)
        return {"job_id": "job-1", "status": "queued"}

    monkeypatch.setattr(mcp_server, "get_x_service", object)
    monkeypatch.setattr(mcp_server.daily_stats_jobs, "start", start_job)

    result = await mcp_server.start_x_posts_daily_stats(
        query="Qwen",
        start_date="2026-09-01",
        end_date="2026-09-30",
    )

    assert result["status"] == "queued"
    assert calls[0]["complete_range"] is True


def test_mcp_http_endpoint_initializes() -> None:
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "clientInfo": {"name": "test", "version": "1.0"},
            "capabilities": {},
        },
    }
    with _client() as client:
        response = client.post(
            "/mcp",
            json=request,
            headers={"Accept": "application/json, text/event-stream"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["serverInfo"]["name"] == "x-deepresearch"
    assert payload["result"]["serverInfo"]["version"] == "0.3.0"
    assert payload["result"]["capabilities"]["tools"] == {"listChanged": False}


async def test_search_tool_reports_more_when_limit_is_reached_with_cursor(monkeypatch) -> None:
    class StubSearchService:
        settings = SimpleNamespace(max_results=2000, page_size=20)

        async def search_pages(self, **kwargs):
            assert kwargs["pages"] is None
            assert kwargs["limit"] == 100
            return [object() for _ in range(100)], "CURSOR-NEXT", 5, None

    monkeypatch.setattr(mcp_server, "get_x_service", lambda: StubSearchService())
    monkeypatch.setattr(
        mcp_server,
        "_serialize_research_tweets",
        lambda items: [{"id": str(index)} for index, _ in enumerate(items)],
    )

    result = await mcp_server.search_x_posts(query="AI", limit=100)

    assert result["requested_limit"] == 100
    assert result["applied_limit"] == 100
    assert result["result_count"] == 100
    assert result["pages_fetched"] == 5
    assert result["has_more"] is True
    assert result["next_cursor"] == "CURSOR-NEXT"
    assert result["pagination_complete"] is False
    assert result["pagination_issue"] is None


async def test_search_tool_reports_terminal_page_without_cursor(monkeypatch) -> None:
    class StubSearchService:
        settings = SimpleNamespace(max_results=2000, page_size=20)

        async def search_pages(self, **kwargs):
            return [object() for _ in range(40)], None, 2, None

    monkeypatch.setattr(mcp_server, "get_x_service", lambda: StubSearchService())
    monkeypatch.setattr(
        mcp_server,
        "_serialize_research_tweets",
        lambda items: [{"id": str(index)} for index, _ in enumerate(items)],
    )

    result = await mcp_server.search_x_posts(query="AI", limit=100)

    assert result["result_count"] == 40
    assert result["pages_fetched"] == 2
    assert result["has_more"] is False
    assert result["next_cursor"] is None
    assert result["pagination_complete"] is True
