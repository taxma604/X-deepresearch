"""Local read-only MCP server.

SQLite state is opt-in via X_RESEARCH_JOB_DB. No files are created by default.
"""
from app.mcp_server import mcp


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
