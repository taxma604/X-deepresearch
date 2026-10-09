# Connect an MCP client

[English](clients.md) · [日本語](clients.ja.md)

X-deepresearch is a **local stdio MCP server**, not a hosted API or a ChatGPT plugin. The client starts `uvx` on **the same machine and operating environment** that contains your X session.

## First: prepare your local session

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), Git, and Python 3.12+. Run in a terminal supporting secret/hidden input:

```bash
uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch-setup --client none
```

The setup prompts for your own `auth_token` and `ct0`, stores them outside Git in `~/.config/x-deepresearch/cookies.json`, and saves search permission choices alongside them. **Never paste session cookies into an MCP JSON, issue, chat, pull request, or command line.**

For a private GitHub repository, Git authentication is required. Browser cookies may be subject to X terms; use only with permission.

## Codex CLI

If you only use Codex, omit `--client none` in the command above. It automatically registers the MCP. Verify:

```bash
codex mcp list
```

For manual registration after setup:

```bash
codex mcp add x-deepresearch -- uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch
```

## Claude Code

After `--client none` setup, register a user-scoped server:

```bash
claude mcp add --scope user x-deepresearch -- uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch
claude mcp list
```

The `claude` command and its MCP syntax depend on your installed Claude Code version. This is a **documented configuration example**, not a verified end-to-end test with Claude Code.

## Claude Desktop

Use Claude Desktop's **local MCP configuration** (`claude_desktop_config.json`). Its location is typically:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Merge this entry under your existing `mcpServers` object (do not replace other servers):

```json
{
  "mcpServers": {
    "x-deepresearch": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/taxma604/X-deepresearch", "x-deepresearch"]
    }
  }
}
```

Restart the desktop app. Local stdio integrations are **not** automatically available inside claude.ai or Claude mobile. On Windows, if your session was saved inside WSL, configure the server to launch **inside WSL**, or run the setup in the same native Windows environment where Claude Desktop runs.

## Cursor

Create or merge `~/.cursor/mcp.json` for your user, or `.cursor/mcp.json` for a specific project:

```json
{
  "mcpServers": {
    "x-deepresearch": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/taxma604/X-deepresearch", "x-deepresearch"]
    }
  }
}
```

Keep your **session files** in your user configuration folder, never in a committed project folder. Reload Cursor and verify the server appears in Tools & MCP.

## Visual Studio Code / GitHub Copilot

Use the VS Code workspace's `.vscode/mcp.json` (or the applicable user MCP configuration):

```json
{
  "servers": {
    "x-deepresearch": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/taxma604/X-deepresearch", "x-deepresearch"]
    }
  }
}
```

VS Code uses **`servers`**, not `mcpServers`. Verify that your VS Code version and chat mode support local MCP tools.

## Other compatible clients

Point the client's stdio command at:

```bash
uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch
```

Do **not** run this stdio command directly and expect a readable human interface: it waits for an MCP host to communicate over standard input and output.

## Troubleshooting

- **`uvx: command not found`** — install uv, then restart the shell/client so the updated PATH is visible. A GUI app may need a full path to `uvx`.
- **Cannot clone the Git repository** — check the repository URL, network access and Git permissions. A private repository requires authenticated access.
- **`codex` missing** — rerun setup with `--client none` for a different MCP host.
- **Hidden input unavailable** — perform setup in an actual terminal; there is deliberately no visible-input fallback.
- **Server launches but cannot find credentials** — run setup in the **same environment/user account** as the MCP host. If you customized `X_DEEPRESEARCH_CONFIG_DIR` or `TWIKIT_COOKIES_FILE`, pass those *paths* via the client's environment configuration.
- **Search denied** — setup may have saved an author allowlist. To search across X, rerun setup and choose unrestricted local search, subject to upstream permission. Changing `ALLOW_ARBITRARY_SEARCH` or `ALLOWED_USERS` environment variables overrides saved settings.
- **No results, authentication errors, or rate limits** — X access can change, the session may expire, or requests may be disallowed. Do not attempt to bypass access controls or evade rate limits.
- **Jobs vanish after restart** — SQLite persistence is intentionally off by default. For local single-process recovery, set `X_RESEARCH_JOB_DB` to a private durable SQLite path before starting the server.

The JSON and CLI samples match documented client formats; cross-client real-session end-to-end verification is still outstanding. [Installation details](INSTALL.md).

### Official client documentation

- [Codex CLI MCP](https://developers.openai.com/codex/mcp)
- [Claude Code MCP](https://code.claude.com/docs/en/mcp)
- [Claude Desktop local MCP](https://modelcontextprotocol.io/docs/develop/connect-local-servers)
- [Cursor MCP](https://cursor.com/docs/mcp)
- [VS Code MCP](https://code.visualstudio.com/docs/copilot/customization/mcp-servers)
