<div align="center">

# X-deepresearch

**Research X conversations with AI agents — with transparent coverage and repeatable workflows.**

[English](README.md) · [日本語](README.ja.md)

[![CI](https://github.com/taxma604/X-deepresearch/actions/workflows/ci.yml/badge.svg)](https://github.com/taxma604/X-deepresearch/actions/workflows/ci.yml)
[![Security](https://github.com/taxma604/X-deepresearch/actions/workflows/security.yml/badge.svg)](https://github.com/taxma604/X-deepresearch/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](pyproject.toml)
[![MCP](https://img.shields.io/badge/MCP-stdio-purple)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Read-only search · 90-day daily trends (JST) · Research jobs · Coverage diagnostics · CSV/JSON/Markdown**

</div>

## Why X-deepresearch?

Most X automation tools focus on posting or managing accounts, and many MCP wrappers focus on fetching individual posts. X-deepresearch focuses on a different workflow: **ask an AI agent to collect, count, compare, and audit the coverage of research results**.

| Research task | What X-deepresearch provides |
| --- | --- |
| Search a subject or author | Read-only post search, bounded pagination and deduplication |
| Study a period | JST daily observed post counts, up to **90 calendar days** per job |
| Run a long investigation | Start a job, poll progress, then summarize or export |
| Compare two topics | Compare observed daily counts for matching date ranges |
| Check reliability | `coverage_complete`, `incomplete_ranges`, `pagination_issue` |
| Resume after interruption | **Optional** SQLite checkpoints; off by default |

**Research-first, not a posting bot.** It does not publish posts, like, follow, send messages, perform sentiment analysis, or promise a complete archive of X. Coverage diagnostics indicate known retrieval gaps, **not** a guarantee that X returned all matching posts.

## Quick start

**Requirements:** Python 3.12+, [uv](https://docs.astral.sh/uv/getting-started/installation/), Git, a terminal supporting hidden input, and your own X browser session. For automatic Codex registration, the [Codex CLI](https://developers.openai.com/codex/cli) must also be installed.

```bash
uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch-setup
```

The interactive setup asks for your **own** X `auth_token` and `ct0` using hidden prompts ([where to find them](docs/INSTALL.md#how-to-find-your-x-cookies)), saves them privately on your computer, asks whether to enable global searches or restrict searches to selected authors, and registers a **local stdio MCP server in Codex**. No session values are sent to this project's author or written to Git, logs, or MCP command arguments.

**Using Claude Code, Claude Desktop, Cursor, VS Code, or another stdio MCP client?** Run the same setup with `--client none`, then register the server using the [client-specific examples](docs/clients.md). The MCP server is **not** Codex-specific.

> This repository is currently **Private**, so GitHub access is required for installation. It has not yet been published to PyPI. [Validation results](docs/VALIDATION.md).

[Full installation and privacy notes](docs/INSTALL.md) · [Client setup](docs/clients.md) · [日本語の導入手順](docs/INSTALL.ja.md)

## Ask your AI assistant

> Search recent posts discussing "physical AI". Return a concise synthesis with original post URLs and identify any incomplete search pages.

> Count observed X mentions of "AI agents" for the previous 30 calendar days, grouped by **JST date**. Show the daily series, peak day, and coverage warnings.

> Compare observed daily volumes for two X search queries across the same dates. Clearly state if either result is incomplete.

These are **example prompts**, not claims about data retrieved during testing. You can see the actual job sequence and output fields in [Research examples](docs/examples.md) ([日本語](docs/examples.ja.md)).

## Available MCP tools

| Tool | Purpose |
| --- | --- |
| `search_x_posts` | Search and paginate read-only posts |
| `get_x_user_posts` | Read a user's timeline |
| `get_x_user_profile` | Read user profile metadata |
| `get_x_post` | Read a post by ID |
| `search_x_posts_daily_stats` | Sample observed post counts by JST day |
| `start_x_posts_daily_stats` | Start an asynchronous research job (up to 90 days) |
| `get_x_posts_daily_stats_job` | Poll status and fetch the result |
| `summarize_x_research_job` | Summarize peaks, averages, total, and coverage |
| `compare_x_research_jobs` | Compare two completed jobs on identical dates |
| `export_x_research_job` | Produce CSV, JSON, or Markdown output |

Results are bounded by configured limits and upstream availability. Start long studies asynchronously and poll their `job_id`. The synchronous daily-stats tool returns a **bounded sample**, not an exhaustive multi-week total.

## Supported environments

- **Codex CLI:** interactive one-command onboarding and registration.
- **Claude Code / Claude Desktop / Cursor / VS Code:** local stdio MCP configuration guides.
- **Other MCP hosts:** any client implementing a compatible local stdio transport can attempt the documented configuration.

Local session files reside under `~/.config/x-deepresearch/` by default. SQLite restart recovery is **opt-in** via `X_RESEARCH_JOB_DB`. [Security](SECURITY.md) · [Validation status](docs/VALIDATION.md) · [Troubleshooting](docs/clients.md#troubleshooting).

## Develop

```bash
git clone https://github.com/taxma604/X-deepresearch.git
cd X-deepresearch
uv sync --extra dev --locked
uv run --locked pytest -q
uv run --locked ruff check .
```

Automated tests use mock X clients and do not require an X account.

## Contributing and project status

Documentation, client configuration fixes, robust aggregation, reproducible tests, and honest coverage reporting are welcome. [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [Security](SECURITY.md) · [MIT License](LICENSE).

**Release status:** pre-publication, version `0.3.0`; no public package release or hosted multi-user service. Source history has been separated from the original private development repository. [Public release checklist](docs/RELEASE_CHECKLIST.md).

> [!IMPORTANT]
> X-deepresearch uses [Twikit](https://github.com/d60/twikit) and the user's own X browser session to access X. It is not an official X product. [Additional information](DISCLAIMER.md).
