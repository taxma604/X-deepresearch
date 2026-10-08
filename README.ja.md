<div align="center">

# X-deepresearch

**Xの投稿をAIエージェントで調査する、取得範囲を明示したリサーチ用MCPサーバー。**

[English](README.md) · [日本語](README.ja.md)

[![CI](https://github.com/taxma604/X-deepresearch/actions/workflows/ci.yml/badge.svg)](https://github.com/taxma604/X-deepresearch/actions/workflows/ci.yml)
[![Security](https://github.com/taxma604/X-deepresearch/actions/workflows/security.yml/badge.svg)](https://github.com/taxma604/X-deepresearch/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](pyproject.toml)
[![MCP](https://img.shields.io/badge/MCP-stdio-purple)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**読み取り専用検索 · 日本時間の日別集計 · 長時間調査 · 取得漏れの診断 · CSV/JSON/Markdown出力**

</div>

> [!IMPORTANT]
> **非公式なXアクセス方式を使用します。** 現時点のバックエンドはTwikitと利用者自身のXブラウザーセッションを使用します。この方式はXの規約に抵触する可能性があり、アカウントに制限が生じるリスクがあります。Cookieの自己保有やローカル実行は、アクセス許可を意味しません。必要な許諾がある場合に限って利用してください。X社とは無関係の独立プロジェクトです。[詳細](DISCLAIMER.md)

## X-deepresearchとは？

Xの自動化ツールには投稿・アカウント操作を重視するものや、個別投稿の取得に特化したMCPがあります。X-deepresearchは、**AIエージェントから調査を開始し、データを収集・集計・比較し、取得状況を確認する**ためのOSSです。

| 調査内容 | 提供機能 |
| --- | --- |
| 話題や投稿者を調べる | 読み取り専用検索、ページネーション、重複除去 |
| 期間の変化を調べる | **最大90暦日**、JSTの日別投稿件数 |
| 時間のかかる調査 | Job開始、進捗確認、集計結果の取得 |
| 2つのテーマを比べる | 同じ日付範囲で、取得された件数を比較 |
| データの信頼性を確認 | `coverage_complete`、`incomplete_ranges`、`pagination_issue` |
| 中断後に再開する | SQLiteチェックポイントを任意で有効化（初期設定はオフ） |

**投稿ボットではありません。** 投稿・いいね・フォロー・DM送信は行いません。感情分析機能もありません。またX全体の完全なアーカイブは保証しません。取得漏れの診断は、検出できた欠損を示すもので、全投稿の収集を証明するものではありません。

## 最短セットアップ

**必要なもの：** Python 3.12以上、[uv](https://docs.astral.sh/uv/getting-started/installation/)、Git、非表示入力に対応したターミナル、適切な利用権限のあるXセッション。Codexへ自動登録する場合は[Codex CLI](https://developers.openai.com/codex/cli)も必要です。

```bash
uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch-setup
```

セットアップでは、利用者自身のXの `auth_token` と `ct0` を非表示で入力します。Cookieはローカルに保存し、検索を全体に許可するか指定投稿者に限定するかを設定します。その後、**Codexのローカルstdio MCP**へ登録します。Cookie自体を開発者のサーバーやGit、ログ、MCPの起動コマンドに送信・記録しません。

**Claude Code・Claude Desktop・Cursor・VS Codeを使う場合：** 同じセットアップコマンドに `--client none` を付け、[クライアント別設定](docs/clients.md)に従って登録してください。MCP本体はCodex専用ではありません。

> リポジトリは現在**Private**です。Public化するまではGitHubへのアクセス権が必要です。PyPI公開もまだ行っていません。セットアップ・インストールのオフラインCIはありますが、Xへの認証付きE2E実行は未検証です。

[詳しい導入とCookieの扱い](docs/INSTALL.md) · [クライアント別設定](docs/clients.md)

## AIへの指示例

> 「physical AI」に関する最近のX投稿を調べて。原投稿のURLを付けて要点をまとめ、取得できなかった範囲があれば明記して。

> 過去30暦日の「AI agents」に関する取得投稿数を日本時間の日別で集計して。ピークの日付と取得の完全性も表示して。

> 2つの検索クエリを同じ期間で比較し、日別の件数推移を示して。どちらかの取得が不完全なら説明して。

上記は**操作例**であり、実際に取得した調査結果ではありません。Jobの流れや返却フィールドは[リサーチ例](docs/examples.md)を参照してください。

## 利用できるMCPツール

| ツール | できること |
| --- | --- |
| `search_x_posts` | 投稿の検索・複数ページの取得 |
| `get_x_user_posts` | ユーザーの投稿一覧 |
| `get_x_user_profile` | ユーザープロフィール |
| `get_x_post` | 投稿IDによる単一投稿の取得 |
| `search_x_posts_daily_stats` | JSTで日別件数をサンプル集計 |
| `start_x_posts_daily_stats` | 最大90日間の非同期調査を開始 |
| `get_x_posts_daily_stats_job` | Jobの進捗・結果を確認 |
| `summarize_x_research_job` | 投稿数・平均・ピーク・取得範囲を要約 |
| `compare_x_research_jobs` | 同じ日付範囲の2つの調査を比較 |
| `export_x_research_job` | CSV・JSON・Markdownに出力 |

件数はサーバー設定やX側の制限に影響されます。長期調査は非同期Jobを使い、返された `job_id` で進捗確認してください。同期の日別集計は**件数制限のあるサンプル**で、完全な長期集計ではありません。

## 対応環境

- **Codex CLI：** 1コマンドの対話式セットアップ・登録。
- **Claude Code / Claude Desktop / Cursor / VS Code：** ローカルstdio MCPの設定例を用意。**全環境でのE2Eテストが完了したわけではありません。**
- **その他：** stdio方式のMCPに対応するクライアントなら設定可能です。

セッション情報は通常 `~/.config/x-deepresearch/` に保存します。再起動後のJob復元は `X_RESEARCH_JOB_DB` を設定した場合のみ有効です。[セキュリティ](SECURITY.md) · [トラブルシューティング](docs/clients.md#troubleshooting)

## 開発

```bash
git clone https://github.com/taxma604/X-deepresearch.git
cd X-deepresearch
uv sync --extra dev --locked
uv run --locked pytest -q
uv run --locked ruff check .
```

テストには模擬Xクライアントを使用しています。CI成功は、Xから実際に取得できることやXのアクセス許諾を保証しません。

## ライセンスとプロジェクト状況

機能追加よりも、正しい集計、取得漏れの明示、安全なセットアップ、テスト、ドキュメント改善への貢献を歓迎します。[貢献方法](CONTRIBUTING.md) · [変更履歴](CHANGELOG.md) · [セキュリティ](SECURITY.md) · [MITライセンス](LICENSE)。

**公開状況：** バージョン `0.3.0` の公開準備段階。PyPIおよび公開クラウドサービスは未提供です。開発用PrivateリポジトリのGit履歴は継承していません。[公開前チェックリスト](docs/RELEASE_CHECKLIST.md)。
