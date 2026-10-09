# Changelog

This project follows semantic versioning when stable releases are published. The repository currently uses `0.3.0` as an internal package version; **a public package release has not been published**.

## Unreleased

- Prepare a new clean-history OSS repository under `X-deepresearch`.
- Align local distribution, CLI commands, server identity, and setup documentation.
- Add read-only X search, profiles and timelines, daily observed counts, background research jobs, summary, comparison, and CSV/JSON/Markdown export.
- Add explicit coverage diagnostics for known pagination gaps and partial collection.
- Add optional SQLite checkpoint recovery; default storage remains in-memory.
- Support interactive local-session configuration and Codex MCP registration without disclosing cookies in command arguments.
- Document local stdio usage with Claude Code, Claude Desktop, Cursor, VS Code and generic compatible MCP clients.
- Provide English and Japanese README files and community contribution guidance.

A maintainer reported local authenticated Windows/WSL validation on 2026-10-09. See [Validation status](docs/VALIDATION.md). This does not establish platform permission or complete cross-client coverage.
