# Local installation

Install Python 3.12+, Git, uv and Codex CLI. While the repository is Private, Git must be authenticated for taxma604/X-deepresearch. Run in a terminal supporting hidden input:

```bash
uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch-setup
```

Enter your own auth_token and ct0 at the hidden prompts, then choose unrestricted search or an allowlist such as `alice,bob_2`. Handles contain 1–15 ASCII letters, digits or underscores; empty elements are rejected. Setup refuses plaintext fallback. The server uses the session only when you request X data, subject to X permissions and terms.

Session and search settings are saved outside Git under `~/.config/x-deepresearch/`. POSIX files use 0600 and new configuration directories 0700; existing parents are not chmodded. Native Windows requires owner-only NTFS ACLs or WSL. Setup registers `x-deepresearch` with `codex mcp add`. Restart Codex and check `codex mcp list`.

`X_DEEPRESEARCH_CONFIG_DIR` changes both default file locations. `TWIKIT_COOKIES_FILE` changes only the cookie path. Setup records these paths in Codex so later launches find the files; no cookie values enter Codex settings. `ALLOW_ARBITRARY_SEARCH` and `ALLOWED_USERS` override saved policy; explicit `ALLOW_ARBITRARY_SEARCH=false` overrides saved unrestricted mode. With `--client none`, files and search permissions are still saved; provide custom path variables in your chosen client.

Alternatively install with `uv tool install git+https://github.com/taxma604/X-deepresearch`. Use `x-deepresearch` for stdio and `x-deepresearch-doctor` for offline checks. Setup's `--source` can select a reviewed tag or local Git source for subsequent launches.

SQLite is off by default. Explicitly set `X_RESEARCH_JOB_DB` to a private durable path for restart recovery. See README for examples and limitations. A local session does not grant platform access permission.
