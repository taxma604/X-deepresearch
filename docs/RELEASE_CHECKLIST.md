# Before making this repository Public

The repository remains Private. Passing CI does not authorize changing visibility.

- Confirm tests, Ruff, compilation, sdist/wheel builds and clean installation succeed for the release revision.
- Confirm dependency audit and independent full-history secret scanning; manually review private notes and data.
- [x] Maintainer reports GitHub uvx setup, Codex app-server MCP discovery/calls and credential-path checks on Windows/WSL (2026-10-09). See [validation record](VALIDATION.md). The actual tests were conducted outside the GitHub CI.
- [ ] Validate native Windows cookie ACLs, non-Codex MCP clients, and standard Codex GUI AI usage.
- Review and pin third-party action/container references to immutable revisions before public release.
- Review third-party licenses and dependency provenance, including Js2Py-3.13.
- [ ] **Publication blocker:** Determine whether distributing and using this Twikit implementation is permitted by X's current Terms or get appropriate written permission / switch to an authorized source. X's Terms prohibit unconsented scraping and facilitating violations; own cookies, disclaimers, and MIT do not grant access rights.
- [x] Maintainer reports authenticated read-only X searches, profiles, 3-day counts, progress, comparison, summaries, exports and SQLite recovery in the local environment. This report does not establish X's permission for the access method.
- [ ] Validate longer research (including 90 days), partial/rate-limit behavior and cross-version upgrades **if permitted**.
- Review branding, release tag/version, public installation access and Codex for Open Source application requirements/evidence.
- Review English and Japanese README parity, real CI badge links, client-specific MCP configuration examples, community templates and actual vs illustrative research samples.
- Confirm the GitHub repository description/topics and other public metadata reflect the current read-only research scope.
- Confirm all packaged readme, license and referenced documentation files are included in source/wheel artifacts.

The source development repository and existing production service are outside scope. Never publish their history, credentials, operational settings or research data.
