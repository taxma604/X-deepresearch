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
| Authenticated-session search for a public post and user profile | Search and profile returned in local test |
| JST daily count (3 days), background job status | Passed |
| Job summary, query comparison, CSV, JSON and Markdown exports | Passed |
| Optional SQLite checkpoint and interrupted-job recovery | Passed |
| Cookies absent from recorded settings and logs | No leaks observed in tested paths |

**Local exceptions, not necessarily product defects:** non-interactive `codex exec` tool use was denied by the test environment's Codex approval policy `never`. An auxiliary identity-lookup endpoint returned HTTP 404. No product source change was needed as a result of this test.

**Not yet validated:** ordinary Codex desktop GUI AI-use flow and restart, a full 90-day job, the maintainer's own posts, high-volume collection and rate-limit recovery, upgrades across different product versions, other MCP clients, native-Windows cookie storage and ACLs.

The validation used an individual local X session; credentials, identifiable account details and private logs are **not** included. No live X calls are performed in CI, and no guarantee of ongoing availability, completeness, or terms compliance is made.

## 日本語概要

2026年10月9日、メンテナーからWindows／WSL環境での動作確認結果が報告されました。GitHubからの `uvx` によるインストール、対話式の初期設定、CodexへのMCP登録、10種類のツールの認識と呼び出しが成功しています。Xの公開投稿の検索、プロフィール取得、3日間の日別集計、ジョブの進捗確認、比較・要約、CSV・JSON・Markdownへの出力、SQLiteによる中断後の復元も確認されています。

一方、通常のCodexデスクトップGUIからのAI操作、90日間の全期間を対象にした調査、大量取得やレート制限後の復旧、異なる製品バージョン間の更新、Codex以外のMCPクライアント、WSLを使わないWindows環境でのCookie保存とアクセス権の確認は未実施です。

この内容は**メンテナーによる実機検証の報告**です。Xからのアクセス許可、取得対象となる全投稿の収集、今後の継続動作を保証するものではありません。

## Release decision

The repository stays **Private** pending explicit legal/permissions review of the Twikit/X access method and a release decision. See [Release checklist](RELEASE_CHECKLIST.md) and [Platform disclaimer](../DISCLAIMER.md).
