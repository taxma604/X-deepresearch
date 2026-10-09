<div align="center">

# X-deepresearch

**Turn X conversations into research you can track and compare.**

[English](README.md) · [日本語](README.ja.md)

[![CI](https://github.com/taxma604/X-deepresearch/actions/workflows/ci.yml/badge.svg)](https://github.com/taxma604/X-deepresearch/actions/workflows/ci.yml)
[![Security](https://github.com/taxma604/X-deepresearch/actions/workflows/security.yml/badge.svg)](https://github.com/taxma604/X-deepresearch/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](pyproject.toml)
[![MCP](https://img.shields.io/badge/MCP-stdio-purple)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Search posts · Track 90 days · Compare topics · Export reports**

</div>

## Quick start

**What you need:** Python 3.12+, [uv](https://docs.astral.sh/uv/getting-started/installation/), Git and your own X session. Use a terminal with hidden input; [Codex CLI](https://developers.openai.com/codex/cli) is needed for automatic Codex registration.

```bash
uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch-setup
```

The setup securely collects your **own** `auth_token` and `ct0` ([where to find them](docs/INSTALL.md#how-to-find-your-x-cookies)), saves them locally, sets search permissions, and registers the MCP server in Codex. Credentials are never included in command arguments or shared with the project author.

**Claude Code, Claude Desktop, Cursor or VS Code?** Run setup with `--client none`, then follow the [MCP client instructions](docs/clients.md).

**Distribution:** Install from GitHub; PyPI is not yet supported. [Validation results](docs/VALIDATION.md).

[Full installation and privacy notes](docs/INSTALL.md) · [Client setup](docs/clients.md) · [日本語の導入手順](docs/INSTALL.ja.md)

## Research ideas to try

### 1. Has the buzz already peaked?

> Investigate X posts about "[topic]" over the past 30 days. Find the peak day, compare the first and last seven days, and show representative posts with their URLs. Is the observed conversation growing or fading?

### 2. Was it already being discussed before launch?

> Look at X posts about "[product]" from seven days before to seven days after its announcement. Put the early discussions in chronological order and compare daily post counts before and after the announcement. Include original post links.

### 3. What was X discussing before a stock surged?

> Research posts about "[company or ticker]" from seven days before to seven days after its sharp price rise. Show when discussions began to increase, observed daily post counts, and relevant post links. Distinguish the timeline from any unproven claim that X activity caused the price move.

Replace the bracketed placeholders with your subject. These prompts use existing search, daily-count and comparison tools; the AI assistant organizes the findings. [More research workflows](docs/examples.md) ([日本語](docs/examples.ja.md)).

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

**Package status:** source version `0.3.0`; not published on PyPI, with no hosted multi-user service. Source history has been separated from the original private development repository. [Public release checklist](docs/RELEASE_CHECKLIST.md).

> [!IMPORTANT]
> X-deepresearch uses [Twikit](https://github.com/d60/twikit) and the user's own X browser session to access X. It is not an official X product. [Additional information](DISCLAIMER.md).
