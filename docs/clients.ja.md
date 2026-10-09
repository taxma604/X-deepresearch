# MCPクライアントへの接続

[English](clients.md) · [日本語](clients.ja.md)

X-deepresearchは、PC上で動かす**stdio方式のMCPサーバー**です。公開APIやChatGPTのプラグインとして動作するものではありません。MCPクライアントは、Xのセッション情報が保存されている**同じPC・実行環境**で `uvx` を起動する必要があります。

## 最初にXセッションを設定する

[uv](https://docs.astral.sh/uv/getting-started/installation/)、Git、Python 3.12以降をインストールし、入力文字を隠せるターミナルで次を実行してください。

```bash
uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch-setup --client none
```

自分のXセッションの `auth_token` と `ct0` を入力すると、設定がGitリポジトリ外の `~/.config/x-deepresearch/cookies.json` に保存されます。検索範囲の設定も保存されます。

**CookieはMCPのJSON設定、GitHubのIssueやPR、チャット、コマンドラインに貼り付けないでください。**

リポジトリが非公開の間は、GitHubでの認証が必要です。XのCookieを使ったアクセスは利用規約上の制限を受ける場合があります。必要な許可を得たうえで利用してください。

## Codex CLI

Codexだけを使う場合は、最初のコマンドから `--client none` を省いてください。MCPサーバーが自動登録されます。

登録を確認するコマンド：

```bash
codex mcp list
```

初期設定後に手動登録する場合：

```bash
codex mcp add x-deepresearch -- uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch
```

## Claude Code

`--client none` で初期設定したあと、ユーザー単位でMCPサーバーを登録します。

```bash
claude mcp add --scope user x-deepresearch -- uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch
claude mcp list
```

`claude` コマンドの仕様は、インストール済みのClaude Codeのバージョンによって異なる場合があります。ここで示すのは**設定例**であり、Claude Codeでの実機テストが完了したことを意味しません。

## Claude Desktop

Claude DesktopのローカルMCP設定ファイル（`claude_desktop_config.json`）を編集します。通常の保存先は次のとおりです。

- macOS：`~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows：`%APPDATA%\Claude\claude_desktop_config.json`

既存の設定がある場合は、ほかのサーバーを消さずに `mcpServers` の中へ次の項目を追加してください。

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

設定後はClaude Desktopを再起動してください。ローカルMCPの設定が、そのままWeb版のclaude.aiやモバイル版Claudeに反映されるわけではありません。

WindowsのClaude Desktopから利用する場合、Xのセッション情報をWSL内に保存したなら、**MCPサーバーもWSL内で起動するように設定**してください。そうでなければ、Claude Desktopと同じWindows環境で初期設定を実行します。

## Cursor

ユーザー共通の設定は `~/.cursor/mcp.json`、プロジェクトごとの設定は `.cursor/mcp.json` に追加できます。

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

Cookieなどのセッション情報は、Gitにコミットされるプロジェクト内ではなく、各ユーザー用の設定ディレクトリに保存してください。Cursorを再読み込みし、Tools & MCPにサーバーが表示されるか確認します。

## Visual Studio Code / GitHub Copilot

VS Codeのワークスペースにある `.vscode/mcp.json`、または対応するユーザー設定に追加します。

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

VS Codeでは `mcpServers` ではなく `servers` を使います。利用中のVS CodeのバージョンとチャットモードがローカルMCPに対応しているか確認してください。

## その他のMCPクライアント

stdio方式に対応するクライアントでは、起動コマンドとして次を指定します。

```bash
uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch
```

このコマンドをターミナルで直接実行しても、人が読むための画面は表示されません。MCPクライアントとの標準入出力による通信を待ち受けます。

## トラブルシューティング

- **`uvx: command not found` と表示される**：uvをインストールし、ターミナルまたはアプリを再起動してPATHを反映してください。GUIアプリでは `uvx` のフルパスが必要な場合があります。
- **GitHubから取得できない**：公開前のためリポジトリは非公開です。アクセス権のあるGitHubアカウントで認証するか、アクセスを許可されたソースを使用してください。
- **`codex` コマンドが見つからない**：Codex以外のMCPクライアントで使うなら `--client none` で初期設定してください。
- **入力した文字を隠せない**：通常のターミナルで初期設定してください。文字を表示したまま入力する方法には自動で切り替わりません。
- **サーバーは起動するがCookieを読み込めない**：初期設定を行ったユーザー・実行環境と、MCPサーバーを動かす環境が同じか確認してください。保存先を `X_DEEPRESEARCH_CONFIG_DIR` または `TWIKIT_COOKIES_FILE` で変更している場合は、クライアント側にも**ファイルのパス**を設定してください。
- **検索が拒否される**：初期設定で許可する投稿者を限定している可能性があります。X全体を対象にした検索が必要なら、初期設定をやり直して全体検索を選択してください。ただし、Xへのアクセスには別途適切な許可が必要です。環境変数 `ALLOW_ARBITRARY_SEARCH`、`ALLOWED_USERS` を指定すると、保存済み設定より優先されます。
- **結果が返らない、認証エラーになる、レート制限がかかる**：Xの仕様変更、セッションの失効、アクセス制限などが原因になり得ます。アクセス制限を回避したり、レート制限をすり抜けたりしないでください。
- **再起動するとジョブが消える**：初期状態ではSQLite保存は無効です。1つのローカルプロセスでジョブを復元するには、`X_RESEARCH_JOB_DB` に永続的で安全なSQLiteの保存先を指定してください。

コマンドとJSONは各クライアントの設定形式に合わせた例です。Codex以外のクライアントを使った、実際のXセッションでの接続確認はまだ完了していません。[詳しいインストール手順](INSTALL.ja.md)。

### 各クライアントの公式資料

- [Codex CLI MCP](https://developers.openai.com/codex/mcp)
- [Claude Code MCP](https://code.claude.com/docs/en/mcp)
- [Claude DesktopのローカルMCP](https://modelcontextprotocol.io/docs/develop/connect-local-servers)
- [Cursor MCP](https://cursor.com/docs/mcp)
- [VS Code MCP](https://code.visualstudio.com/docs/copilot/customization/mcp-servers)
