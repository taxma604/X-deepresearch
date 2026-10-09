# Validation status / 検証状況

This document distinguishes **CI-tested capabilities** from **maintainer-reported local manual tests**. Local observations are not an independently reproducible public benchmark, and do not provide authorization to access X.

## Automated CI

On the `main` branch, GitHub Actions runs Ruff, offline pytest with dummy data, compilation, sdist/wheel build, clean wheel installation, and a security audit. CI outcomes are visible under the repository's **Actions** tab.

## Local manual test report — 2026-10-09

The maintainer reported the following results from a Windows + WSL installation:

| Test area | Maintainer-reported result |
| --- | --- |
| `uvx` install directly from GitHub | Passed |
| Interactive setup, hidden X cookie input, private local storage | Passed |
| Automatic registration with an isolated Codex CLI | Passed |
| Reinstall and upgrade in a local setup | Passed |
| MCP tool discovery and invocation via Windows/WSL Codex app-server | 10 tools discovered and callable |
| Reconnect after MCP process restart | Passed |
| Authorized-session search for a public post and user profile | Search and profile returned in local test |
| JST daily count (3 days), background job status | Passed |
| Job summary, query comparison, CSV, JSON and Markdown exports | Passed |
| Optional SQLite checkpoint and interrupted-job recovery | Passed |
| Cookies absent from recorded settings and logs | No leaks observed in tested paths |

**Local exceptions, not necessarily product defects:** non-interactive `codex exec` tool use was denied by the test environment's Codex approval policy `never`. An auxiliary identity-lookup endpoint returned HTTP 404. No product source change was needed as a result of this test.

**Not yet validated:** ordinary Codex desktop GUI AI-use flow and restart, a full 90-day job, the maintainer's own posts, high-volume collection and rate-limit recovery, upgrades across different product versions, other MCP clients, native-Windows cookie storage and ACLs.

The validation used an individual local X session; credentials, identifiable account details and private logs are **not** included. No live X calls are performed in CI, and no guarantee of ongoing availability, completeness, or terms compliance is made.

## 日本語概要

2026年10月9日にWindows／WSL上で、GitHubからの`uvx`導入、対話式セットアップ、CodexへのMCP登録、10ツールの認識・呼び出し、読み取り専用の検索・プロフィール取得、3日分集計、比較・要約・各形式への出力、SQLite復元を実機検証したとメンテナーから報告されています。

一方、通常のCodexデスクトップGUI操作、90日間の全期間、高負荷・レート制限時の復旧、ほかのMCPクライアント、Windows単独での認証情報保存は未検証です。これは**実機テストの報告**であり、Xによるアクセス許可や全件取得を保証するものではありません。

## Release decision

The repository stays **Private** pending explicit legal/permissions review of the Twikit/X access method and a release decision. See [Release checklist](RELEASE_CHECKLIST.md) and [Platform disclaimer](../DISCLAIMER.md).
