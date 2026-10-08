# Contributing to X-deepresearch

Thanks for helping improve a **read-only, evidence-aware X research** MCP server.

## Scope

We welcome improvements to search reliability, honest coverage reporting, job progress and recovery, exports, tests, documentation, localization and stdio client compatibility.

We do **not** aim to support automated posting, account engagement, credential sharing, access-control bypasses, or evading platform rate limits.

## Development

Install Python 3.12+, Git and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/taxma604/X-deepresearch.git
cd X-deepresearch
uv sync --extra dev --locked
uv run --locked ruff check .
uv run --locked pytest -q
```

Tests **must be offline** and use synthetic tweets, fake X clients and dummy session values. Never require contributors to perform live scraping for the CI suite.

For bug fixes, add a regression test. For features, document tool inputs, expected results, pagination/coverage implications, and unsupported cases.

## Documentation

`README.md` is the canonical English introduction; `README.ja.md` mirrors the same capabilities and limitations in Japanese. Update both when changing behavior or release status. Put longer client instructions in `docs/clients.md` and prompts/output examples in `docs/examples.md`.

Do not claim an integration is tested simply because its JSON shape is documented.

## Security and privacy

Never submit session cookies, auth tokens, secret-bearing HAR files, account databases, personal research data, or a public endpoint backed by another person's session. Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md). Read [DISCLAIMER.md](DISCLAIMER.md) before distributing modifications.

## Pull requests

Keep PRs focused, explain how to reproduce and verify the change, and complete the template. Avoid modifying unrelated deployed services or private project history.

Please also follow our [Code of Conduct](CODE_OF_CONDUCT.md).
