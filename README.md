# X-deepresearch

Read-only X research for local AI assistants: search, user timelines, 90-day JST daily counts, restart checkpoints, comparisons and CSV/JSON/Markdown reports. Python, FastAPI and MCP; MIT licensed.

Independent third-party project. Unofficial Twikit access may violate X's Terms and lead to account enforcement. Your own cookies, local execution and the MIT license do not grant permission to access X. Use only with the required permissions. See [DISCLAIMER.md](DISCLAIMER.md).

## Requirements and installation

Python 3.12+, [uv](https://docs.astral.sh/uv/getting-started/installation/), Git, Codex CLI and a terminal supporting hidden input are required. This repository is currently **Private**; authenticated GitHub access is required. PyPI publication has not occurred.

```bash
uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch-setup
```

Setup prompts privately for your own X `auth_token` and `ct0`, then asks whether to allow unrestricted search or restrict authors to an ASCII X-handle allowlist. A terminal that cannot hide input is rejected; there is no plaintext fallback. Cookie values never enter command arguments, Git, logs, Codex configuration or another operator's service.

The session is stored outside Git in `~/.config/x-deepresearch/cookies.json`. Search permissions are saved in `~/.config/x-deepresearch/settings.json`, including with `--client none`. POSIX files use 0600 and new configuration directories use 0700. Set `X_DEEPRESEARCH_CONFIG_DIR` to change the directory, or `TWIKIT_COOKIES_FILE` for a custom cookie file. Setup passes these paths to Codex, not cookie values. Environment variables take precedence over saved settings. Native Windows users must separately restrict NTFS ACLs or use WSL.

Codex registers the server as `x-deepresearch`. Start a new Codex session and check `codex mcp list`. For another local MCP client, append `--client none` to setup, then use:

```json
{"mcpServers":{"x-deepresearch":{"command":"uvx","args":["--from","git+https://github.com/taxma604/X-deepresearch","x-deepresearch"]}}}
```

See [installation details](docs/INSTALL.md) for custom paths and local development.

## Usage and tools

Ask your assistant to search `from:example_user AI since:2026-07-01 until:2026-10-01`, or start a daily-count study for `AI` from `2026-07-01` through `2026-09-28`. An allowlist requires one permitted `from:handle` author; unrestricted mode permits broader queries. Boolean author-policy bypasses are rejected.

| MCP tool | Purpose |
| --- | --- |
| `search_x_posts` | Search and paginate posts |
| `get_x_user_posts` | User timeline |
| `get_x_user_profile` | User profile |
| `get_x_post` | Single post |
| `search_x_posts_daily_stats` | Bounded JST daily sample |
| `start_x_posts_daily_stats` | Start asynchronous research, up to 90 days |
| `get_x_posts_daily_stats_job` | Poll progress and results |
| `summarize_x_research_job` | Counts, peaks and coverage summary |
| `compare_x_research_jobs` | Compare completed jobs over the same range |
| `export_x_research_job` | Export CSV, JSON or Markdown |

Poll the returned `job_id`, inspect `coverage_complete`, `incomplete_ranges` and `pagination_issue`, then summarize, compare or export completed jobs. Searches support pagination, deduplication, cursor-cycle detection and bounded retry/backoff. Coverage flags describe known gaps in upstream results, not an exhaustive archive or guaranteed access.

## Optional restart recovery

SQLite is **disabled by default**; ordinary jobs stay in memory. Set `X_RESEARCH_JOB_DB=~/.local/share/x-deepresearch/jobs.sqlite3` to persist finished date-window checkpoints and completed results. Interrupted jobs resume when the server starts or a job is requested; unfinished windows are fetched again. Keep the database private because it contains queries and results. Persistence is for one local process and requires durable storage.

## Development

```bash
git clone https://github.com/taxma604/X-deepresearch.git
cd X-deepresearch
uv sync --extra dev --locked
uv run pytest -q
uv run ruff check .
```

The distribution and primary command are `x-deepresearch`; setup is `x-deepresearch-setup`. Auxiliary offline commands are `x-deepresearch-auth init` and `x-deepresearch-doctor`. The authenticated REST/HTTP implementation is retained for private local use; its data endpoints require a strong `X_RESEARCH_ACCESS_TOKEN`. A plugin directory listing or shared multi-user cloud service is outside this project's scope.

Tests use fake sessions and clients; successful tests do not establish live X access or permission. See [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md) and [public release checklist](docs/RELEASE_CHECKLIST.md). No development-repository history is included. Do not change visibility solely because CI passes.
