# Changelog

The source package is currently version `0.3.0`. Its initial GitHub Release has been prepared; consult the GitHub **Releases** page for whether it has actually been published. This project is not distributed through PyPI.

## 0.3.0 — Initial open-source package

- Prepare a new clean-history OSS repository under `X-deepresearch`.
- Align local distribution, CLI commands, server identity, and setup documentation.
- Add read-only X search, profiles and timelines, daily observed counts, background research jobs, summary, comparison, and CSV/JSON/Markdown export.
- Add explicit coverage diagnostics for known pagination gaps and partial collection.
- Add optional SQLite checkpoint recovery; default storage remains in-memory.
- Support interactive local-session configuration and Codex MCP registration without disclosing cookies in command arguments.
- Document local stdio usage with Claude Code, Claude Desktop, Cursor, VS Code and generic compatible MCP clients.
- Provide English and Japanese README files and community contribution guidance.

A maintainer reported local authenticated Windows/WSL validation on 2026-10-09. See [Validation status](docs/VALIDATION.md). This does not establish platform permission or complete cross-client coverage.
