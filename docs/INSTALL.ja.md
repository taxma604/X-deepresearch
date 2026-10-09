# ローカル環境へのインストール

[English](INSTALL.md) · [日本語](INSTALL.ja.md)

Python 3.12以降、Git、[uv](https://docs.astral.sh/uv/getting-started/installation/) とCodex CLIをインストールしてください。リポジトリが非公開の間は、`taxma604/X-deepresearch` にアクセスできるGitHubアカウントが必要です。

入力文字を隠せるターミナルで、次のコマンドを実行します。

```bash
uvx --from git+https://github.com/taxma604/X-deepresearch x-deepresearch-setup
```

初期設定では、自分のXセッションの `auth_token` と `ct0` を、画面に表示されない形で入力します。その後、X全体の検索を許可するか、検索対象を指定した投稿者に限定するかを選びます。指定する場合は `alice,bob_2` のように入力します。ユーザー名に使えるのは半角英数字とアンダースコアで、各1〜15文字です。空の項目は指定できません。

ターミナルが入力文字を隠せない場合、初期設定は中断されます。入力内容が画面に表示される方法へ自動で切り替わることはありません。Xへのアクセスには必要な許可があることを前提とします。

## Cookieの取得方法

1. **自分のPC**のブラウザーで[x.com](https://x.com)にログインします。
2. **Chrome／Edge**では`F12`（または`Ctrl+Shift+I`）で開発者ツールを開き、**Application → Cookies → https://x.com** を選びます。**Firefox**では **Storage → Cookies → https://x.com** を開きます。
3. `auth_token` と `ct0` を探し、それぞれの **Value（値）** をコピーします。値は `x-deepresearch-setup` の入力欄に、指示に従って1つずつ貼り付けてください。入力した文字は画面に表示されません。

この2つのCookieはログイン情報です。**他人やAIチャットに送らず、GitHubにも載せないでください。** コマンドの引数やMCPのJSON設定へ書く必要もありません。初期設定コマンドがPC内に保存します。

## 設定の保存先

Cookieと検索範囲の設定は、Gitリポジトリの外にある `~/.config/x-deepresearch/` に保存されます。POSIX環境では、ファイルの権限は `0600`、新規作成する設定ディレクトリは `0700` になります。ただし、既存の親ディレクトリの権限までは変更しません。

Windows単独で利用する場合は、NTFSのアクセス権を適切に制限するか、WSLを使用してください。

初期設定により、`codex mcp add` で `x-deepresearch` が登録されます。Codexを再起動したら、次のコマンドで登録を確認できます。

```bash
codex mcp list
```

## 設定の変更

- `X_DEEPRESEARCH_CONFIG_DIR`：Cookieと検索範囲の設定を保存するディレクトリを変更します。
- `TWIKIT_COOKIES_FILE`：Cookieファイルの保存先だけを変更します。
- `ALLOW_ARBITRARY_SEARCH` と `ALLOWED_USERS`：保存済みの検索範囲設定よりも、環境変数の値が優先されます。`ALLOW_ARBITRARY_SEARCH=false` を指定すると、保存済みの「全体検索を許可する」設定よりも優先されます。

Codexへの登録時には、Cookieの値ではなく、設定ファイルの**保存先のパス**を渡します。ほかのMCPクライアントで `--client none` を使う場合も、Cookieと検索範囲の設定は保存されます。保存先を変更した場合は、そのパスをクライアント側でも指定してください。

## 手動インストール・ジョブの復元

次のコマンドで、CLIツールとしてインストールすることもできます。

```bash
uv tool install git+https://github.com/taxma604/X-deepresearch
```

MCPサーバーの起動には `x-deepresearch`、オフラインでの環境確認には `x-deepresearch-doctor` を使用します。初期設定コマンドの `--source` オプションでは、確認済みのGitタグやローカルのGitソースなど、起動に使うソースを変更できます。

SQLiteへの保存は初期状態で無効です。再起動後もジョブを復元したい場合は、`X_RESEARCH_JOB_DB` に、ほかの人から読み取られない永続的な保存先を指定してください。

PC上で実行することや自分のCookieを使うことは、Xへのアクセス許可を意味しません。[README（日本語）](../README.ja.md)も参照してください。
