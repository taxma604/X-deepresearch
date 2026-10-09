# Local installation

[English](INSTALL.md) · [日本語](INSTALL.ja.md)

Install Python 3.12+, Git, uv and Codex CLI. If the repository is private at installation time, Git must be authenticated for taxma604/X-deepresearch. Run in a terminal supporting hidden input:

```bash
uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch-setup
```

Enter your own auth_token and ct0 at the hidden prompts (see the instructions below), then choose unrestricted search or an allowlist such as `alice,bob_2`. Handles contain 1–15 ASCII letters, digits or underscores; empty elements are rejected. Setup refuses plaintext fallback. The server uses the session only when you request X data, subject to X permissions and terms.

## How to find your X cookies

1. On your **own computer**, sign in to [x.com](https://x.com) using a desktop browser.
2. In **Chrome or Edge**, press `F12` (or `Ctrl+Shift+I`), then open **Application → Cookies → https://x.com**. In **Firefox**, open **Storage → Cookies → https://x.com**.
3. Find `auth_token` and `ct0`; copy the **Value** of each cookie into its corresponding **hidden** `x-deepresearch-setup` prompt.

These cookies grant access to your X account. Treat them like passwords: **never post or send them to an AI chat, GitHub, or another person**. Do not add them to command-line arguments or MCP JSON settings. The setup tool handles local storage for you.

Session and search settings are saved outside Git under `~/.config/x-deepresearch/`. POSIX files use 0600 and new configuration directories 0700; existing parents are not chmodded. Native Windows requires owner-only NTFS ACLs or WSL. Setup registers `x-deepresearch` with `codex mcp add`. Restart Codex and check `codex mcp list`.

`X_DEEPRESEARCH_CONFIG_DIR` changes both default file locations. `TWIKIT_COOKIES_FILE` changes only the cookie path. Setup records these paths in Codex so later launches find the files; no cookie values enter Codex settings. `ALLOW_ARBITRARY_SEARCH` and `ALLOWED_USERS` override saved policy; explicit `ALLOW_ARBITRARY_SEARCH=false` overrides saved unrestricted mode. With `--client none`, files and search permissions are still saved; provide custom path variables in your chosen client.

Alternatively install with `uv tool install git+https://github.com/taxma604/X-deepresearch`. Use `x-deepresearch` for stdio and `x-deepresearch-doctor` for offline checks. Setup's `--source` can select a reviewed tag or local Git source for subsequent launches.

SQLite is off by default. Explicitly set `X_RESEARCH_JOB_DB` to a private durable path for restart recovery. See README for examples and limitations. A local session does not grant platform access permission.
