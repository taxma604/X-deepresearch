# Research workflows (illustrative)

These examples describe tool calls and output *shapes*. They do not claim to show live X results. Your MCP client chooses tool calls from natural language prompts.

## 1. Search with links and coverage diagnostics

**Prompt:** "Find up to 50 recent posts mentioning physical AI. Show relevant post URLs and whether pagination was incomplete."

Tool:

```json
{"tool":"search_x_posts","arguments":{"query":"\"physical AI\"","product":"Latest","limit":50}}
```

The response contains posts with URLs and pagination information. The exact schema and the number of posts depend on upstream X responses. Set up **unrestricted search** for broad queries; with an allowlist, add a permitted `from:handle` constraint.

## 2. Daily trend job (JST)

**Prompt:** "Count observed posts about robot learning from September 1 through September 14, 2026, by JST calendar day."

Start:

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

This returns a `job_id`. Poll:

```json
{"tool":"get_x_posts_daily_stats_job","arguments":{"job_id":"<returned-job-id>"}}
```

If the job is `queued`, `running`, or `waiting_for_rate_limit`, request status again later. When `completed`, inspect `daily` and the coverage indicators. A `failed` result requires investigation before reporting totals.

The job uses bounded searches and splits ranges when necessary, but if X stops returning enough pages, its observed totals can still be incomplete.

## 3. Summary, comparison, export

Using actual `job_id` values returned from two completed jobs with the **same date range**:

```json
{"tool":"summarize_x_research_job","arguments":{"job_id":"<first-job-id>"}}
```

```json
{"tool":"compare_x_research_jobs","arguments":{"job_id_a":"<first-job-id>","job_id_b":"<second-job-id>"}}
```

```json
{"tool":"export_x_research_job","arguments":{"job_id":"<first-job-id>","format":"csv"}}
```

The comparison provides observed totals and daily counts; it **does not** establish the volume of all X posts. CSV, JSON, and Markdown exports are text responses you can save through your own MCP host.

## What a reliable research answer should disclose

- Date range and timezone (JST for daily studies).
- Search query, filters, and observed counts.
- Source post URLs when drawing conclusions from posts.
- Whether `coverage_complete` is true, known `incomplete_ranges`, and any `pagination_issue`.
- That upstream X limits and response completeness are outside the project's control.

**Do not present synthetic examples as real observations.**
