"""Offline stdio MCP subprocess smoke test: tool discovery needs no X credentials."""
import sys

from mcp import Client, StdioServerParameters


async def test_stdio_transport_is_discoverable():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.stdio"],
        env={"TWIKIT_COOKIES_JSON": "", "TWIKIT_AUTH_TOKEN": "", "TWIKIT_CT0": ""},
    )
    async with Client(params) as client:
        tools = await client.list_tools()
    names = {tool.name for tool in tools.tools}
    assert "search_x_posts" in names
    assert "summarize_x_research_job" in names
    assert "export_x_research_job" in names


def test_stdio_keeps_sqlite_disabled_by_default(monkeypatch, tmp_path):
    """Starting the stdio command must not create a DB unless explicitly requested."""
    import app.stdio as entry

    recorded = []
    monkeypatch.delenv("X_RESEARCH_JOB_DB", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(entry.mcp, "run", lambda transport: recorded.append(transport))
    entry.main()
    assert recorded == ["stdio"]
    assert not list(tmp_path.rglob("*.sqlite3"))
