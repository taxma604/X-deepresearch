<div align="center">

# X-deepresearch

**AIでXの投稿を調査し、集計・比較の結果とデータの取得状況を確認できるMCPサーバー。**

[English](README.md) · [日本語](README.ja.md)

[![CI](https://github.com/taxma604/X-deepresearch/actions/workflows/ci.yml/badge.svg)](https://github.com/taxma604/X-deepresearch/actions/workflows/ci.yml)
[![Security](https://github.com/taxma604/X-deepresearch/actions/workflows/security.yml/badge.svg)](https://github.com/taxma604/X-deepresearch/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](pyproject.toml)
[![MCP](https://img.shields.io/badge/MCP-stdio-purple)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**投稿検索（読み取り専用） · 最大90日間の日別集計（日本時間） · 長期間の調査ジョブ · 取得漏れの確認 · CSV/JSON/Markdown出力**

</div>

## X-deepresearchとは

Xの自動化ツールには、投稿やアカウント管理が中心のものもあれば、個別の投稿を取得するMCPツールもあります。X-deepresearchは、**AIエージェントから調査を始め、投稿を集め、件数の集計や比較を行い、どこまで取得できたかを確認する**ためのオープンソースソフトウェアです。

| やりたいこと | 主な機能 |
| --- | --- |
| 話題や投稿者について調べる | 読み取り専用の投稿検索、ページ単位の取得、重複除去 |
| 期間ごとの投稿数を調べる | 1回のジョブで最大90日間、日本時間での日別件数を集計 |
| 時間のかかる調査を進める | ジョブを開始し、進捗を確認してから集計・出力 |
| 2つの話題を比較する | 同じ日付範囲で取得された投稿数を日別に比較 |
| 取得状況を確認する | `coverage_complete`、`incomplete_ranges`、`pagination_issue` |
| 中断した調査を再開する | SQLiteに進捗を保存する設定（初期状態では無効） |

**投稿やアカウント操作を自動化するツールではありません。** 投稿・いいね・フォロー・DM送信は行わず、感情分析にも対応していません。Xの全投稿を網羅したデータベースでもありません。取得漏れを示す情報は、検出できた問題を知らせるものです。**問題が表示されなくても、条件に一致する全投稿を取得できたとは限りません。**

## インストールと初期設定

必要なものは、Python 3.12以降、[uv](https://docs.astral.sh/uv/getting-started/installation/)、Git、入力した文字を非表示にできるターミナル、自分のXセッションです。Codexに自動登録する場合は、[Codex CLI](https://developers.openai.com/codex/cli)も必要です。

```bash
uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch-setup
```

実行すると、利用者自身のXの `auth_token` と `ct0` の入力を求められます（[取得方法](docs/INSTALL.ja.md#cookieの取得方法)）。入力した文字は表示されません。CookieはPC内に保存され、検索対象をX全体にするか、指定した投稿者に限定するかを設定します。その後、ローカルのMCPサーバーをCodexへ登録します。

Cookieの値は開発者のサーバーへ送られず、Git、ログ、MCPの起動コマンドにも記録されません。

**Claude Code、Claude Desktop、Cursor、VS Codeなどで使う場合**は、コマンドの末尾に `--client none` を追加してください。初期設定を済ませたあと、[クライアント別の設定手順](docs/clients.ja.md)に従ってMCPサーバーを登録します。MCPサーバー自体はCodex専用ではありません。

> 現在、リポジトリは**非公開（Private）**です。インストールにはGitHubでのアクセス権が必要です。PyPIにはまだ公開していません。[動作検証の結果](docs/VALIDATION.md)。

[詳しいインストール手順](docs/INSTALL.ja.md) · [クライアント別の設定手順](docs/clients.ja.md)

## AIへの指示例

> 「physical AI」について最近のX投稿を調べて。内容を要約して元の投稿URLを付けて。取得できなかったページがあれば、それも教えて。

> 過去30日間の「AI agents」に関する投稿を、日本時間の日別で集計して。日ごとの件数、最も多かった日、取得漏れの有無を示して。

> 2つの検索クエリについて、同じ期間の投稿件数を日別に比較して。どちらかの取得結果が不完全なら、その点も説明して。

いずれも**AIへの指示例**で、実際の調査結果ではありません。各ツールの呼び出し方や出力内容は[調査の使用例](docs/examples.ja.md)を参照してください。

## 利用できるMCPツール

| ツール名 | 機能 |
| --- | --- |
| `search_x_posts` | 投稿を検索し、複数ページから取得 |
| `get_x_user_posts` | ユーザーの投稿を取得 |
| `get_x_user_profile` | ユーザーのプロフィールを取得 |
| `get_x_post` | 投稿IDを指定して1件取得 |
| `search_x_posts_daily_stats` | 日本時間の日別投稿数を、上限付きでサンプル集計 |
| `start_x_posts_daily_stats` | 最大90日間の日別集計ジョブを開始 |
| `get_x_posts_daily_stats_job` | ジョブの進捗と結果を確認 |
| `summarize_x_research_job` | 合計・平均・最多の日・取得状況を要約 |
| `compare_x_research_jobs` | 同じ日付範囲の2つのジョブを比較 |
| `export_x_research_job` | CSV・JSON・Markdownで結果を出力 |

取得件数には設定上の上限があり、X側の制限にも左右されます。期間の長い調査はジョブを開始し、返された `job_id` を使って進捗を確認してください。`search_x_posts_daily_stats` は**上限付きのサンプル集計**であり、長期間の全件集計ではありません。

## 対応する環境

- **Codex CLI**：対話式の初期設定からMCP登録まで、1コマンドで実行できます。
- **Claude Code／Claude Desktop／Cursor／VS Code**：ローカルMCPの設定手順を用意しています。
- **その他のMCPクライアント**：ローカルのstdio方式に対応していれば、設定して利用できます。

Cookieなどの設定ファイルは、初期状態では `~/.config/x-deepresearch/` に保存されます。ジョブを再起動後も復元するには、`X_RESEARCH_JOB_DB` を明示的に設定してSQLite保存を有効にしてください。

[セキュリティ](SECURITY.md) · [検証状況](docs/VALIDATION.md) · [トラブルシューティング](docs/clients.ja.md#トラブルシューティング)

## 開発

```bash
git clone https://github.com/taxma604/X-deepresearch.git
cd X-deepresearch
uv sync --extra dev --locked
uv run --locked pytest -q
uv run --locked ruff check .
```

自動テストでは模擬Xクライアントを使うため、Xアカウントは必要ありません。

## 貢献・ライセンス・公開状況

正確な集計、取得漏れの表示、安全な初期設定、テスト、ドキュメントの改善を歓迎します。

[開発への参加方法](CONTRIBUTING.md) · [変更履歴](CHANGELOG.md) · [セキュリティ](SECURITY.md) · [MITライセンス](LICENSE)

**公開状況：** バージョン `0.3.0` の公開準備中です。PyPIへの登録や、複数人で使う公開クラウドサービスの提供は行っていません。元の非公開開発リポジトリのGit履歴は引き継いでいません。[公開前の確認事項](docs/RELEASE_CHECKLIST.md)を参照してください。

> [!IMPORTANT]
> X-deepresearchは、Xへのアクセスに[Twikit](https://github.com/d60/twikit)と利用者自身のXセッションを使用しています。X公式のツールではありません。[補足情報](DISCLAIMER.md)。
