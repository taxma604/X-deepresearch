from __future__ import annotations

from typing import Any, Literal

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from app.api.dependencies import get_x_service
from app.config import Settings
from app.services.daily_stats_jobs import DailyStatsJobManager
from app.services.research_reports import compare, report, summarize
from app.x.serializers import research_tweet_to_model


def _transport_security() -> TransportSecuritySettings:
    allowed_hosts = [
        "localhost",
        "localhost:*",
        "127.0.0.1",
        "127.0.0.1:*",
        "testserver",
    ]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=[
            "https://chatgpt.com",
            "https://chat.openai.com",
            "http://localhost:*",
            "http://127.0.0.1:*",
        ],
    )


mcp = MCPServer(
    name="x-deepresearch",
    title="X-deepresearch",
    description="Read-only X research tools backed by a Twikit browser session.",
    instructions=(
        "Use these tools only to read X data. Search can run across X or be narrowed with "
        "X search operators such as from:user. "
        "Set limit to the number of posts you need; search pagination is inferred from it "
        "unless pages is explicitly supplied. For long daily-stat searches, start a job and "
        "poll its status instead of waiting for one synchronous call."
    ),
    version="0.3.0",
)
daily_stats_jobs = DailyStatsJobManager(db_path=Settings().job_db_path)


def _serialize_research_tweets(items: list[Any]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for item in items:
        model = research_tweet_to_model(item)
        if model is not None:
            serialized.append(model.model_dump())
    return serialized


@mcp.tool(
    title="Search X posts",
    description=(
        "Search read-only posts across X; from:user is optional. limit is the requested "
        "maximum post count. If pages is omitted, enough pages are fetched to approach limit. "
        "The server enforces its configured maximum."
    ),
)
async def search_x_posts(
    query: str,
    product: Literal["Latest", "Top"] = "Latest",
    pages: int | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    service = get_x_service()
    items, next_cursor, pages_fetched, pagination_issue = await service.search_pages(
        query=query,
        product=product,
        pages=pages,
        limit=limit,
        page_size=service.settings.page_size,
    )
    serialized = _serialize_research_tweets(items)
    return {
        "items": serialized,
        "requested_limit": limit,
        "applied_limit": min(max(1, limit), service.settings.max_results),
        "result_count": len(serialized),
        "has_more": bool(next_cursor),
        "next_cursor": next_cursor,
        "pagination_complete": not bool(next_cursor) and pagination_issue is None,
        "pagination_issue": pagination_issue,
        "pages_fetched": pages_fetched,
    }


@mcp.tool(
    title="Sample X daily post counts",
    description=(
        "Return a bounded sample of read-only X search posts per JST calendar day for an inclusive "
        "YYYY-MM-DD date range; this tool does not provide a complete multi-week total. "
        "The date range is sent to X as search operators before pagination. from:user is "
        "optional. limit controls how many matching posts are sampled, up to the server cap. "
        "For a complete multi-week count or 600 or more posts, use start_x_posts_daily_stats "
        "and poll get_x_posts_daily_stats_job. Inspect coverage_complete in the final result."
    ),
)
async def search_x_posts_daily_stats(
    query: str,
    start_date: str,
    end_date: str,
    product: Literal["Latest", "Top"] = "Latest",
    limit: int = 500,
) -> dict[str, Any]:
    service = get_x_service()
    return await service.search_daily_stats(
        query=query,
        product=product,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


@mcp.tool(
    title="Start complete X daily stats job",
    description=(
        "Start an asynchronous complete daily post count, especially for a multi-week range. "
        "Returns a job_id immediately. Poll get_x_posts_daily_stats_job with that ID until "
        "status is completed or failed (waiting_for_rate_limit means upstream requested a pause); "
        "Long daily-stat jobs are queued and run one at a time to protect X's shared rate budget. "
        "complete_range defaults to true; set it false only to request a bounded sample. "
        "In complete mode, limit applies to each search batch, not to the full date range. "
        "The search starts with non-overlapping two-day windows, splits capped windows, and "
        "continues a capped single day from its next cursor. Inspect coverage_complete and "
        "incomplete_ranges; incomplete totals are lower bounds. It supports up to 90 calendar days. "
        "The completed result contains the daily counts. Job "
        "state is kept in process memory for up to one hour after completion and is cleared on restart."
    ),
)
async def start_x_posts_daily_stats(
    query: str,
    start_date: str,
    end_date: str,
    product: Literal["Latest", "Top"] = "Latest",
    limit: int = 2000,
    complete_range: bool = True,
) -> dict[str, Any]:
    service = get_x_service()
    await daily_stats_jobs.resume_pending(service)
    return daily_stats_jobs.start(
        service,
        query=query,
        product=product,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        complete_range=complete_range,
    )


@mcp.tool(
    title="Get X daily stats job",
    description=(
        "Use this to check progress or retrieve the result of a job started with "
        "start_x_posts_daily_stats. A completed job includes its full daily-stat result; "
        "jobs are cleared when the service restarts."
    ),
)
async def get_x_posts_daily_stats_job(job_id: str) -> dict[str, Any]:
    await daily_stats_jobs.resume_pending(get_x_service())
    result = daily_stats_jobs.get(job_id)
    if result is None:
        return {
            "job_id": job_id,
            "status": "not_found",
            "message": "The job was not found or has expired.",
        }
    return result


@mcp.tool(
    title="Get X user posts",
    description="Read recent posts from an X user with bounded pagination.",
)
async def get_x_user_posts(
    screen_name: str,
    pages: int = 1,
    limit: int = 20,
    include_replies: bool = False,
) -> dict[str, Any]:
    service = get_x_service()
    items, next_cursor, pages_fetched = await service.user_tweets_pages(
        screen_name,
        pages=pages,
        limit=limit,
        page_size=service.settings.page_size,
        include_replies=include_replies,
    )
    return {
        "items": _serialize_research_tweets(items),
        "next_cursor": next_cursor,
        "pages_fetched": pages_fetched,
    }


@mcp.tool(
    title="Get X user profile",
    description="Read an X user's public profile metadata.",
)
async def get_x_user_profile(screen_name: str) -> dict[str, Any]:
    profile = await get_x_service().user_profile(screen_name)
    return profile.model_dump()


@mcp.tool(
    title="Get X post",
    description="Read one X post by numeric post ID.",
)
async def get_x_post(tweet_id: str) -> dict[str, Any]:
    post = await get_x_service().tweet_detail(tweet_id)
    return post.model_dump()


def _completed_job(job_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    job = daily_stats_jobs.get(job_id)
    if job is None:
        return None, {"job_id": job_id, "status": "not_found"}
    if job["status"] != "completed":
        return None, {"job_id": job_id, "status": job["status"], "error": job.get("error")}
    return job["result"], None


@mcp.tool(
    title="Summarize completed X research",
    description="Summarize daily post counts, peak day, and coverage of a completed research job.",
)
async def summarize_x_research_job(job_id: str) -> dict[str, Any]:
    await daily_stats_jobs.resume_pending(get_x_service())
    result, error = _completed_job(job_id)
    if error:
        return error
    return {"job_id": job_id, "status": "completed", "summary": summarize(result)}


@mcp.tool(
    title="Compare completed X research queries",
    description="Compare two completed X daily-stat jobs with identical date ranges; show incomplete coverage.",
)
async def compare_x_research_jobs(job_id_a: str, job_id_b: str) -> dict[str, Any]:
    await daily_stats_jobs.resume_pending(get_x_service())
    a, error = _completed_job(job_id_a)
    if error:
        return {"side": "a", **error}
    b, error = _completed_job(job_id_b)
    if error:
        return {"side": "b", **error}
    try:
        result = compare(a, b)
    except ValueError as exc:
        return {"status": "invalid_comparison", "message": str(exc)}
    return {"status": "completed", "comparison": result}


@mcp.tool(
    title="Export X research daily report",
    description="Return Markdown, CSV, or JSON text for observed daily counts from a completed job.",
)
async def export_x_research_job(
    job_id: str, format: Literal["markdown", "csv", "json"] = "markdown"
) -> dict[str, Any]:
    await daily_stats_jobs.resume_pending(get_x_service())
    result, error = _completed_job(job_id)
    if error:
        return error
    return {"job_id": job_id, "status": "completed", "format": format,
            "content": report(result, format)}


mcp_http_app = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
    transport_security=_transport_security(),
)
