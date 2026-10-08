import time
from datetime import date, timedelta
from types import SimpleNamespace
from typing import ClassVar

import pytest

from app.config import Settings
from app.services.rate_limiter import AsyncRequestLimiter, RetryPolicy
from app.services.x_service import XService
from app.x.client import XPage
from app.x.exceptions import XRateLimitError


class FakeClient:
    def __init__(self) -> None:
        self.user_calls = 0
        self.tweet_calls: list[dict] = []

    async def get_user_by_screen_name(self, username: str):
        self.user_calls += 1
        return SimpleNamespace(
            id="7",
            screen_name=username,
            name="Alice",
            description="",
            followers_count=1,
            following_count=2,
            verified=False,
        )

    async def get_user_tweets(self, user_id: str, **kwargs):
        self.tweet_calls.append({"user_id": user_id, **kwargs})
        return XPage(
            items=[
                SimpleNamespace(
                    id="123",
                    text="old post",
                    created_at="2026-09-13T00:00:00Z",
                    user=SimpleNamespace(id="7", screen_name="alice", name="Alice"),
                    reply_count=0,
                    retweet_count=0,
                    favorite_count=0,
                    quote_count=0,
                    view_count=0,
                    media=[],
                    quote=None,
                )
            ],
            next_cursor="NEXT",
        )


async def test_user_tweets_preserves_cursor_and_uses_profile_cache() -> None:
    settings = Settings(
        TWIKIT_AUTH_TOKEN="AUTH",
        TWIKIT_CT0="CT0",
        X_MIN_REQUEST_INTERVAL_SECONDS=0,
        X_RATE_LIMIT_PER_MINUTE=600,
    )
    client = FakeClient()
    service = XService(client, settings)

    result = await service.user_tweets(
        "@alice",
        limit=40,
        cursor="CURSOR",
        include_replies=False,
    )

    assert result.next_cursor == "NEXT"
    assert result.has_more is True
    assert result.items[0].id == "123"
    assert client.user_calls == 1
    assert client.tweet_calls == [
        {
            "user_id": "7",
            "limit": 40,
            "cursor": "CURSOR",
            "include_replies": False,
        }
    ]


async def test_x_rate_limit_cooldown_blocks_other_shared_requests(monkeypatch) -> None:
    monkeypatch.setattr("app.x.exceptions.time.time", lambda: 1_000.0)

    class TooManyRequests(Exception):
        headers: ClassVar[dict[str, str]] = {"x-rate-limit-reset": "1000.3"}
        rate_limit_reset = 1_000.3

    settings = Settings(
        _env_file=None,
        X_MIN_REQUEST_INTERVAL_SECONDS=0,
        X_RATE_LIMIT_PER_MINUTE=600,
        X_RETRY_BASE_SECONDS=0.01,
        X_RETRY_MAX_SECONDS=1,
    )
    service = XService(FakeClient(), settings)
    policy = RetryPolicy(max_retries=0, base_seconds=0.01, max_seconds=1)

    async def rate_limited():
        raise TooManyRequests("private upstream detail")

    with pytest.raises(XRateLimitError):
        await service._call(rate_limited, retry_policy=policy)

    async def succeeding():
        return "ok"

    started = time.monotonic()
    assert await service._call(succeeding, retry_policy=policy) == "ok"
    assert time.monotonic() - started >= 0.25


class PagedSearchClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def search_tweets(self, query: str, **kwargs):
        self.calls.append({"query": query, **kwargs})
        if kwargs["cursor"] is None:
            items = [SimpleNamespace(id="1"), SimpleNamespace(id="2")]
            return XPage(items=items, next_cursor="CURSOR-1")
        return XPage(items=[SimpleNamespace(id="3")], next_cursor="CURSOR-2")


async def test_search_pages_honors_server_page_and_result_limits() -> None:
    settings = Settings(
        _env_file=None,
        ALLOWED_USERS="alice",
        MAX_PAGES=2,
        MAX_RESULTS=3,
        PAGE_SIZE=2,
        X_MIN_REQUEST_INTERVAL_SECONDS=0,
        X_RATE_LIMIT_PER_MINUTE=600,
    )
    client = PagedSearchClient()
    service = XService(client, settings)

    items, next_cursor, pages_fetched, pagination_issue = await service.search_pages(
        query="from:alice",
        product="Latest",
        pages=20,
        limit=20,
        page_size=20,
    )

    assert [item.id for item in items] == ["1", "2", "3"]
    assert next_cursor == "CURSOR-2"
    assert pages_fetched == 2
    assert pagination_issue is None
    assert client.calls == [
        {"query": "from:alice", "product": "Latest", "limit": 2, "cursor": None},
        {"query": "from:alice", "product": "Latest", "limit": 1, "cursor": "CURSOR-1"},
    ]


class MultiPageSearchClient:
    def __init__(self, *, total_pages: int, duplicate_on_page: int | None = None) -> None:
        self.total_pages = total_pages
        self.duplicate_on_page = duplicate_on_page
        self.calls: list[dict] = []

    async def search_tweets(self, query: str, **kwargs):
        page_number = len(self.calls) + 1
        self.calls.append({"query": query, **kwargs})
        items = []
        for index in range(kwargs["limit"]):
            tweet_id = str((page_number - 1) * 20 + index + 1)
            if page_number == self.duplicate_on_page and index == 0:
                tweet_id = "1"
            items.append(SimpleNamespace(id=tweet_id))
        next_cursor = f"CURSOR-{page_number}" if page_number < self.total_pages else None
        return XPage(items=items, next_cursor=next_cursor)


def make_search_settings(**overrides) -> Settings:
    return Settings(
        _env_file=None,
        ALLOWED_USERS="alice",
        MAX_PAGES=100,
        MAX_RESULTS=2000,
        PAGE_SIZE=20,
        X_MIN_REQUEST_INTERVAL_SECONDS=0,
        X_RATE_LIMIT_PER_MINUTE=600,
        **overrides,
    )


async def search_pages(client, *, limit: int, pages: int | None = None):
    service = XService(client, make_search_settings())
    return await service.search_pages(
        query="from:alice",
        product="Latest",
        pages=pages,
        limit=limit,
        page_size=20,
    )


async def test_search_limit_100_fetches_five_pages() -> None:
    client = MultiPageSearchClient(total_pages=10)

    items, next_cursor, pages_fetched, pagination_issue = await search_pages(client, limit=100)

    assert len(items) == 100
    assert pages_fetched == 5
    assert pagination_issue is None
    assert next_cursor == "CURSOR-5"
    assert [call["cursor"] for call in client.calls] == [
        None,
        "CURSOR-1",
        "CURSOR-2",
        "CURSOR-3",
        "CURSOR-4",
    ]


async def test_search_limit_500_fetches_beyond_40_results() -> None:
    client = MultiPageSearchClient(total_pages=30)

    items, next_cursor, pages_fetched, pagination_issue = await search_pages(client, limit=500)

    assert len(items) == 500
    assert pages_fetched == 25
    assert pagination_issue is None
    assert next_cursor == "CURSOR-25"


async def test_explicit_pages_bound_search_before_limit() -> None:
    client = MultiPageSearchClient(total_pages=10)

    items, next_cursor, pages_fetched, pagination_issue = await search_pages(
        client,
        limit=100,
        pages=3,
    )

    assert len(items) == 60
    assert pages_fetched == 3
    assert pagination_issue is None
    assert next_cursor == "CURSOR-3"


async def test_terminal_upstream_page_returns_no_cursor() -> None:
    client = MultiPageSearchClient(total_pages=2)

    items, next_cursor, pages_fetched, pagination_issue = await search_pages(client, limit=100)

    assert len(items) == 40
    assert pages_fetched == 2
    assert next_cursor is None
    assert pagination_issue is None


async def test_repeated_cursor_is_not_reported_as_more_results() -> None:
    class RepeatedCursorClient:
        def __init__(self) -> None:
            self.calls: list[str | None] = []

        async def search_tweets(self, query: str, **kwargs):
            self.calls.append(kwargs["cursor"])
            return XPage(
                items=[SimpleNamespace(id=f"{len(self.calls)}-{index}") for index in range(20)],
                next_cursor="SAME-CURSOR",
            )

    client = RepeatedCursorClient()
    items, next_cursor, pages_fetched, pagination_issue = await search_pages(client, limit=100)

    assert len(items) == 40
    assert pages_fetched == 2
    assert client.calls == [None, "SAME-CURSOR"]
    assert next_cursor is None
    assert pagination_issue == "cursor_cycle"


async def test_multi_cursor_cycle_stops_and_marks_pagination_incomplete() -> None:
    class CursorCycleClient:
        def __init__(self) -> None:
            self.calls: list[str | None] = []
            self.cursors = ["CURSOR-A", "CURSOR-B", "CURSOR-A"]

        async def search_tweets(self, query: str, **kwargs):
            page_number = len(self.calls) + 1
            self.calls.append(kwargs["cursor"])
            items = [SimpleNamespace(id=f"{page_number}-{index}") for index in range(20)]
            return XPage(items=items, next_cursor=self.cursors[page_number - 1])

    client = CursorCycleClient()
    items, next_cursor, pages_fetched, pagination_issue = await search_pages(
        client,
        limit=100,
    )

    assert len(items) == 60
    assert client.calls == [None, "CURSOR-A", "CURSOR-B"]
    assert pages_fetched == 3
    assert next_cursor is None
    assert pagination_issue == "cursor_cycle"


async def test_cursor_only_terminal_stops_even_when_upstream_cursor_is_present() -> None:
    class TerminalInstructionClient:
        async def search_tweets(self, query: str, **kwargs):
            return XPage(
                items=[SimpleNamespace(id=f"tweet-{index}") for index in range(20)],
                next_cursor="OPAQUE-NEXT",
                instruction_types=("TimelineReplaceEntry",),
                terminal_reason="cursor_only_replacement",
            )

    items, next_cursor, pages_fetched, pagination_issue = await search_pages(
        TerminalInstructionClient(),
        limit=100,
    )

    assert len(items) == 20
    assert next_cursor is None
    assert pages_fetched == 1
    assert pagination_issue is None


async def test_duplicate_tweets_do_not_stop_pagination() -> None:
    client = MultiPageSearchClient(total_pages=4, duplicate_on_page=2)

    items, next_cursor, pages_fetched, pagination_issue = await search_pages(client, limit=60)

    assert len(items) == 60
    assert pages_fetched == 4
    assert pagination_issue is None
    assert client.calls[1]["cursor"] == "CURSOR-1"
    assert client.calls[2]["cursor"] == "CURSOR-2"
    assert client.calls[3]["cursor"] == "CURSOR-3"
    assert next_cursor is None


async def test_daily_stats_aggregates_multiple_pages_in_jst() -> None:
    class DailyPagedSearchClient:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        async def search_tweets(self, query: str, **kwargs):
            page_number = len(self.calls) + 1
            self.calls.append({"query": query, **kwargs})
            day = {1: "2026-09-23", 2: "2026-09-22", 3: "2026-09-21"}[page_number]
            items = [
                SimpleNamespace(
                    id=f"{page_number}-{index}",
                    created_at=f"{day}T12:00:00+09:00",
                )
                for index in range(kwargs["limit"])
            ]
            next_cursor = f"CURSOR-{page_number}" if page_number < 3 else None
            return XPage(items=items, next_cursor=next_cursor)

    client = DailyPagedSearchClient()
    service = XService(client, make_search_settings())
    progress = []

    result = await service.search_daily_stats(
        query="from:alice",
        product="Latest",
        start_date="2026-09-16",
        end_date="2026-09-23",
        limit=500,
        progress_callback=lambda pages, posts, more: progress.append((pages, posts, more)),
    )

    assert result["total_posts"] == 60
    assert result["pages_fetched"] == 3
    assert result["pagination_complete"] is True
    assert result["pagination_issue"] is None
    assert progress == [(1, 20, True), (2, 40, True), (3, 60, False)]
    assert result["daily"] == [
        {"date": "2026-09-16", "count": 0},
        {"date": "2026-09-17", "count": 0},
        {"date": "2026-09-18", "count": 0},
        {"date": "2026-09-19", "count": 0},
        {"date": "2026-09-20", "count": 0},
        {"date": "2026-09-21", "count": 20},
        {"date": "2026-09-22", "count": 20},
        {"date": "2026-09-23", "count": 20},
    ]
    assert "since_time:" in client.calls[0]["query"]
    assert "until_time:" in client.calls[0]["query"]


async def test_complete_daily_stats_splits_capped_windows_without_double_counting(
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.services.x_service.COMPLETE_DAILY_STATS_WINDOW_DAYS", 7)
    service = XService(FakeClient(), make_search_settings())
    calls: list[tuple[str, str]] = []

    async def stub_daily_stats(**kwargs):
        window_start = kwargs["start_date"]
        window_end = kwargs["end_date"]
        calls.append((window_start, window_end))
        start = date.fromisoformat(window_start)
        end = date.fromisoformat(window_end)
        days = []
        current = start
        while current <= end:
            days.append({"date": current.isoformat(), "count": 2})
            current += timedelta(days=1)
        capped = (window_start, window_end) == ("2026-09-01", "2026-09-07")
        return {
            "total_posts": 2000 if capped else 2 * len(days),
            "daily": days,
            "requested_limit": kwargs["limit"],
            "applied_limit": kwargs["limit"],
            "result_count": 2000 if capped else 2 * len(days),
            "fetched_posts": 2000 if capped else 2 * len(days),
            "has_more": capped,
            "next_cursor": "CURSOR" if capped else None,
            "pages_fetched": 100 if capped else 1,
        }

    service.search_daily_stats = stub_daily_stats
    result = await service.search_daily_stats_complete(
        query="Qwen",
        product="Latest",
        start_date="2026-09-01",
        end_date="2026-09-08",
        limit=2000,
    )

    assert calls == [
        ("2026-09-01", "2026-09-07"),
        ("2026-09-01", "2026-09-04"),
        ("2026-09-05", "2026-09-07"),
        ("2026-09-08", "2026-09-08"),
    ]
    assert result["total_posts"] == 16
    assert result["result_count"] == 16
    assert result["pages_fetched"] == 103
    assert result["segments_fetched"] == 4
    assert result["coverage_complete"] is True
    assert result["pagination_complete"] is True
    assert result["count_is_lower_bound"] is False
    assert result["has_more"] is False
    assert result["next_cursor"] is None
    assert all(bucket["count"] == 2 for bucket in result["daily"])


async def test_complete_daily_stats_uses_non_overlapping_two_day_windows() -> None:
    service = XService(FakeClient(), make_search_settings())
    calls: list[tuple[str, str]] = []

    async def stub_daily_stats(**kwargs):
        calls.append((kwargs["start_date"], kwargs["end_date"]))
        start = date.fromisoformat(kwargs["start_date"])
        end = date.fromisoformat(kwargs["end_date"])
        daily = []
        current = start
        while current <= end:
            daily.append({"date": current.isoformat(), "count": 1})
            current += timedelta(days=1)
        return {
            "total_posts": len(daily),
            "daily": daily,
            "requested_limit": kwargs["limit"],
            "applied_limit": kwargs["limit"],
            "result_count": len(daily),
            "fetched_posts": len(daily),
            "has_more": False,
            "next_cursor": None,
            "pages_fetched": 1,
        }

    service.search_daily_stats = stub_daily_stats
    result = await service.search_daily_stats_complete(
        query="Qwen",
        product="Latest",
        start_date="2026-09-01",
        end_date="2026-09-06",
        limit=2000,
    )

    assert calls == [
        ("2026-09-01", "2026-09-02"),
        ("2026-09-03", "2026-09-04"),
        ("2026-09-05", "2026-09-06"),
    ]
    assert result["total_posts"] == 6
    assert result["segments_fetched"] == 3
    assert result["coverage_complete"] is True
    assert result["pagination_complete"] is True


async def test_complete_daily_stats_counts_30_days_beyond_the_single_search_cap() -> None:
    service = XService(FakeClient(), make_search_settings())
    windows: list[tuple[str, str]] = []

    async def stub_daily_stats(**kwargs):
        start = date.fromisoformat(kwargs["start_date"])
        end = date.fromisoformat(kwargs["end_date"])
        windows.append((kwargs["start_date"], kwargs["end_date"]))
        days = [start + timedelta(days=offset) for offset in range((end - start).days + 1)]
        return {
            "total_posts": 100 * len(days),
            "daily": [{"date": day.isoformat(), "count": 100} for day in days],
            "fetched_posts": 100 * len(days),
            "has_more": False,
            "next_cursor": None,
            "pages_fetched": 1,
        }

    service.search_daily_stats = stub_daily_stats
    result = await service.search_daily_stats_complete(
        query="Qwen",
        product="Latest",
        start_date="2026-09-01",
        end_date="2026-09-30",
        limit=2000,
    )

    assert len(windows) == 15
    assert len(result["daily"]) == 30
    assert result["total_posts"] == 3000
    assert result["coverage_complete"] is True
    assert result["incomplete_ranges"] == []


async def test_complete_daily_stats_continues_past_the_per_search_limit() -> None:
    class CappedDayClient:
        def __init__(self) -> None:
            self.cursors: list[str | None] = []

        async def search_tweets(self, query: str, **kwargs):
            cursor = kwargs["cursor"]
            self.cursors.append(cursor)
            page = 1 if cursor is None else int(cursor.rsplit("-", 1)[1]) + 1
            ids = list(range((page - 1) * 20 + 1, page * 20 + 1))
            if page == 3:
                ids[0] = 40  # The first item overlaps the previous batch.
            return XPage(
                items=[
                    SimpleNamespace(id=str(tweet_id), created_at="2026-09-01T12:00:00+09:00")
                    for tweet_id in ids
                ],
                next_cursor=f"CURSOR-{page}" if page < 4 else None,
            )

    client = CappedDayClient()
    settings = Settings(
        _env_file=None,
        ALLOW_ARBITRARY_SEARCH=True,
        MAX_PAGES=2,
        MAX_RESULTS=40,
        PAGE_SIZE=20,
    )
    service = XService(
        client,
        settings,
        limiter=AsyncRequestLimiter(
            max_concurrent=1,
            min_interval_seconds=0,
            rate_per_minute=1_000_000,
        ),
    )

    result = await service.search_daily_stats_complete(
        query="Qwen",
        product="Latest",
        start_date="2026-09-01",
        end_date="2026-09-01",
        limit=40,
    )

    assert client.cursors == [None, "CURSOR-1", "CURSOR-2", "CURSOR-3"]
    assert result["total_posts"] == 79
    assert result["daily"] == [{"date": "2026-09-01", "count": 79}]
    assert result["pages_fetched"] == 4
    assert result["segments_fetched"] == 2
    assert result["coverage_complete"] is True
    assert result["count_is_lower_bound"] is False
    assert result["incomplete_ranges"] == []


async def test_complete_daily_stats_marks_a_repeated_cursor_as_incomplete() -> None:
    service = XService(FakeClient(), make_search_settings())

    async def stub_daily_stats(**kwargs):
        return {
            "query": kwargs["query"],
            "period": {"start": kwargs["start_date"], "end": kwargs["end_date"]},
            "total_posts": 2000,
            "daily": [{"date": kwargs["start_date"], "count": 2000}],
            "requested_limit": kwargs["limit"],
            "applied_limit": kwargs["limit"],
            "result_count": 2000,
            "fetched_posts": 2000,
            "has_more": True,
            "next_cursor": "CURSOR",
            "pages_fetched": 100,
        }

    service.search_daily_stats = stub_daily_stats
    result = await service.search_daily_stats_complete(
        query="Qwen",
        product="Latest",
        start_date="2026-09-01",
        end_date="2026-09-01",
        limit=2000,
    )

    assert result["total_posts"] == 2000
    assert result["coverage_complete"] is False
    assert result["pagination_complete"] is False
    assert result["count_is_lower_bound"] is True
    assert result["has_more"] is True
    assert result["next_cursor"] is None
    assert result["incomplete_ranges"] == [
        {
            "start": "2026-09-01",
            "end": "2026-09-01",
            "posts_returned": 2000,
            "reason": "cursor_cycle",
        }
    ]


async def test_complete_daily_stats_keeps_cursor_cycle_as_lower_bound() -> None:
    service = XService(FakeClient(), make_search_settings())

    async def stub_daily_stats(**kwargs):
        return {
            "total_posts": 17,
            "daily": [{"date": kwargs["start_date"], "count": 17}],
            "fetched_posts": 17,
            "has_more": False,
            "next_cursor": None,
            "pagination_complete": False,
            "pagination_issue": "cursor_cycle",
            "pages_fetched": 3,
        }

    service.search_daily_stats = stub_daily_stats
    result = await service.search_daily_stats_complete(
        query="Qwen",
        product="Latest",
        start_date="2026-09-01",
        end_date="2026-09-01",
        limit=2000,
    )

    assert result["total_posts"] == 17
    assert result["coverage_complete"] is False
    assert result["count_is_lower_bound"] is True
    assert result["incomplete_ranges"] == [
        {
            "start": "2026-09-01",
            "end": "2026-09-01",
            "posts_returned": 17,
            "reason": "cursor_cycle",
        }
    ]


async def test_complete_daily_stats_stops_on_cursor_only_replacement() -> None:
    class CursorOnlyPageClient:
        def __init__(self) -> None:
            self.calls = 0

        async def search_tweets(self, query: str, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return XPage(
                    items=[
                        SimpleNamespace(
                            id=f"tweet-{index}",
                            created_at="2026-08-28T12:00:00+09:00",
                        )
                        for index in range(20)
                    ],
                    next_cursor="CURSOR-A",
                )
            return XPage(
                items=[],
                next_cursor="CURSOR-B",
                raw_entries_count=2,
                raw_tweet_count=0,
                cursor_candidates=(("top", "abc123"), ("bottom", "def456")),
                instruction_types=("TimelineReplaceEntry",),
                terminal_reason="cursor_only_replacement",
            )

    client = CursorOnlyPageClient()
    service = XService(client, make_search_settings(ALLOW_ARBITRARY_SEARCH=True))
    result = await service.search_daily_stats_complete(
        query="Qwen",
        product="Latest",
        start_date="2026-08-28",
        end_date="2026-08-28",
        limit=2000,
    )

    assert client.calls == 2
    assert result["total_posts"] == 20
    assert result["daily"] == [{"date": "2026-08-28", "count": 20}]
    assert result["pages_fetched"] == 2
    assert result["coverage_complete"] is True
    assert result["count_is_lower_bound"] is False
    assert result["incomplete_ranges"] == []


async def test_complete_daily_stats_rejects_ranges_over_90_days() -> None:
    service = XService(FakeClient(), make_search_settings())

    with pytest.raises(ValueError, match="at most 90 calendar days"):
        await service.search_daily_stats_complete(
            query="Qwen",
            product="Latest",
            start_date="2026-01-01",
            end_date="2026-04-01",
            limit=2000,
        )
