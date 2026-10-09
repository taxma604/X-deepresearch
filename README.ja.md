<div align="center">

# X-deepresearch

**Xの投稿をAIで検索・集計・比較。話題の変化を調べるMCPサーバー。**

[English](README.md) · [日本語](README.ja.md)

[![CI](https://github.com/taxma604/X-deepresearch/actions/workflows/ci.yml/badge.svg)](https://github.com/taxma604/X-deepresearch/actions/workflows/ci.yml)
[![Security](https://github.com/taxma604/X-deepresearch/actions/workflows/security.yml/badge.svg)](https://github.com/taxma604/X-deepresearch/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](pyproject.toml)
[![MCP](https://img.shields.io/badge/MCP-stdio-purple)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**投稿検索 · 最大90日間の推移 · 話題の比較 · レポート出力**

</div>

## インストールと初期設定

**必要なもの：** Python 3.12以降、[uv](https://docs.astral.sh/uv/getting-started/installation/)、Git、自分のXセッション。入力文字を非表示にできるターミナルを使います。Codexへの自動登録には[Codex CLI](https://developers.openai.com/codex/cli)も必要です。

```bash
uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch-setup
```

初期設定では `auth_token` と `ct0` を非表示で入力します（[取得方法](docs/INSTALL.ja.md#cookieの取得方法)）。CookieをPC内に保存し、検索範囲を設定してCodexにMCPサーバーを登録します。Cookieの値を開発者へ送信したり、起動コマンドに記録したりすることはありません。

**Claude Code・Claude Desktop・Cursor・VS Codeで使う場合：** `--client none` を付けて初期設定し、[クライアント別の手順](docs/clients.ja.md)からMCPを登録してください。

**配布方法：** 現在はGitHubからインストールします。PyPIには未登録です。[動作検証の結果](docs/VALIDATION.md)。

[詳しいインストール手順](docs/INSTALL.ja.md) · [クライアント別の設定手順](docs/clients.ja.md)

## まず試してほしい3つの調査

### 1. その話題、もうピークを過ぎた？

> 「○○」について過去30日間のX投稿を調べて。最も投稿が多かった日、最初の7日間と直近7日間の件数、代表的な投稿をURL付きでまとめて。取得できたデータから、話題が盛り上がっているのか、落ち着いてきたのかを判断して。

### 2. 発表前から話題になっていた？

> 「○○」の新製品発表日の前後7日間を調べて。発表前にどんな投稿があったのか、時系列で並べて。発表前後の日別投稿数も比較し、元の投稿URLを付けて。

### 3. 株価が急騰する前、Xでは何が起きていた？

> 「○○」の株価が急騰した日の前後7日間のX投稿を調べて。話題が増え始めた時期、日別の投稿数、関連する投稿をURL付きでまとめて。Xの投稿が株価を動かしたと断定せず、時系列で整理して。

「○○」を調べたい話題・製品・銘柄に置き換えてください。検索・日別集計・比較には既存のツールを使い、結果の整理はAIが行います。[詳しい調査例](docs/examples.ja.md)（[English](docs/examples.md)）。

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

**配布状況：** ソースコードのバージョンは `0.3.0` です。PyPIへの登録や、複数人で使う公開クラウドサービスの提供は行っていません。元の非公開開発リポジトリのGit履歴は引き継いでいません。[公開前の確認事項](docs/RELEASE_CHECKLIST.md)を参照してください。

> [!IMPORTANT]
> X-deepresearchは、Xへのアクセスに[Twikit](https://github.com/d60/twikit)と利用者自身のXセッションを使用しています。X公式のツールではありません。[補足情報](DISCLAIMER.md)。
