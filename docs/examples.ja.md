# 調査の使用例

[English](examples.md) · [日本語](examples.ja.md)

ここではMCPツールの呼び出し方と、返却される情報の例を示します。**実際のXから取得した結果ではありません。** AIエージェントは利用者の自然な言葉による指示をもとに、必要なツールを選んで実行します。

## 1. 投稿を検索し、取得状況を確認する

AIへの指示例：

> 「physical AI」に関する最近の投稿を最大50件調べて。投稿のURLと、ページの取得漏れがあったかどうかを教えて。

ツールの呼び出し例：

```json
{"tool":"search_x_posts","arguments":{"query":"\"physical AI\"","product":"Latest","limit":50}}
```

応答には投稿のURLやページ取得の状況が含まれます。返却形式の詳細や投稿数はX側の応答に左右されます。投稿者を限定しない検索では、初期設定でX全体の検索を許可する必要があります。許可する投稿者を限定している場合は、検索クエリに許可済みの `from:handle` 条件を付けてください。

## 2. 日本時間の日別件数を集計する

AIへの指示例：

> 2026年9月1日から14日までの「robot learning」に関する投稿件数を、日本時間の日別で集計して。

まず調査ジョブを開始します。

```json
{
  "tool": "start_x_posts_daily_stats",
  "arguments": {
    "query": "\"robot learning\"",
    "start_date": "2026-09-01",
    "end_date": "2026-09-14",
    "complete_range": true
  }
}
```

実行すると `job_id` が返ります。そのIDで進捗を確認します。

```json
{"tool":"get_x_posts_daily_stats_job","arguments":{"job_id":"<returned-job-id>"}}
```

状態が `queued`（待機中）、`running`（実行中）、`waiting_for_rate_limit`（レート制限による待機中）の場合は、時間をおいて再確認してください。

`completed`（完了）になったら、`daily` と取得状況のフィールドを確認します。`failed`（失敗）の場合は、件数を報告する前に原因を調べる必要があります。

ジョブは取得範囲を分割し、1回あたりの検索件数に上限を設けます。ただし、Xから十分な数のページを取得できなかった場合、集計結果は不完全になることがあります。

## 3. 要約・比較・エクスポート

**同じ日付範囲**で完了した2つのジョブから、実際に返された `job_id` を使用してください。

要約：

```json
{"tool":"summarize_x_research_job","arguments":{"job_id":"<first-job-id>"}}
```

比較：

```json
{"tool":"compare_x_research_jobs","arguments":{"job_id_a":"<first-job-id>","job_id_b":"<second-job-id>"}}
```

CSVへの出力：

```json
{"tool":"export_x_research_job","arguments":{"job_id":"<first-job-id>","format":"csv"}}
```

比較機能が示すのは、**実際に取得できた投稿の件数と日別の差**です。X全体の投稿数を確定するものではありません。CSV・JSON・Markdownの出力はテキストとして返されるため、必要に応じて利用中のMCPクライアントから保存してください。

## 調査結果をまとめるときに確認すること

- 検索期間とタイムゾーン（日別集計では日本時間）。
- 検索クエリ、絞り込み条件、取得できた件数。
- 投稿の内容を根拠として使う場合は、元の投稿URL。
- `coverage_complete`、`incomplete_ranges`、`pagination_issue` で示される取得状況。
- X側の制限によって、結果に取得漏れが生じる可能性があること。

**架空の実行例を、実際の調査結果として示さないでください。**
