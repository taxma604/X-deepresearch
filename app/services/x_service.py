from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any, TypeVar
from zoneinfo import ZoneInfo

from app.config import Settings
from app.models.common import PageData
from app.models.tweet import Tweet
from app.x.client import XClient, cursor_fingerprint
from app.x.exceptions import SearchNotAllowedError, map_twikit_error
from app.x.policy import search_query_is_allowed
from app.x.serializers import page_to_data, tweet_to_model, user_to_model

from .cache import MISSING, TTLCache
from .rate_limiter import AsyncRequestLimiter, RetryPolicy

T = TypeVar("T")
JAPAN_TZ = ZoneInfo("Asia/Tokyo")
COMPLETE_DAILY_STATS_WINDOW_DAYS = 2
MAX_COMPLETE_DAILY_STATS_DAYS = 90
MAX_COMPLETE_SINGLE_DAY_PAGES = 1000
logger = logging.getLogger(__name__)


class XService:
    """Coordinate authentication-backed reads, caching, pacing, and retries."""

    def __init__(
        self,
        client: XClient,
        settings: Settings,
        *,
        cache: TTLCache | None = None,
        limiter: AsyncRequestLimiter | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.client = client
        self.settings = settings
        self.cache = cache or TTLCache()
        self.limiter = limiter or AsyncRequestLimiter(
            max_concurrent=settings.max_concurrent_requests,
            min_interval_seconds=settings.min_request_interval_seconds,
            rate_per_minute=settings.rate_limit_per_minute,
        )
        self.retry_policy = retry_policy or RetryPolicy(
            max_retries=settings.max_retries,
            base_seconds=settings.retry_base_seconds,
            max_seconds=settings.retry_max_seconds,
        )

    async def _call(
        self,
        operation: Callable[[], Awaitable[T]],
        *,
        retry_policy: RetryPolicy | None = None,
    ) -> T:
        policy = retry_policy or self.retry_policy

        async def limited_operation() -> T:
            async with self.limiter.slot(on_rate_limit_wait=policy.on_wait):
                try:
                    return await operation()
                except Exception as error:
                    mapped = map_twikit_error(error)
                    if mapped.status_code == 429:
                        cooldown = max(
                            mapped.retry_after or 0.0,
                            policy.base_seconds,
                        )
                        await self.limiter.defer_for(cooldown)
                    raise

        return await policy.run(limited_operation)

    async def user_profile(self, username: str):
        username = username.lstrip("@").strip()
        key = f"user:{username.casefold()}"
        cached = self.cache.get(key)
        if cached is not MISSING:
            return cached
        user = await self._call(lambda: self.client.get_user_by_screen_name(username))
        data = user_to_model(user)
        if data is None:
            from app.x.exceptions import XNotFoundError

            raise XNotFoundError("The requested X user was not found.")
        return self.cache.set(key, data, self.settings.user_cache_ttl_seconds)

    async def user_tweets(
        self,
        username: str,
        *,
        limit: int,
        cursor: str | None,
        include_replies: bool,
    ) -> PageData:
        user = await self.user_profile(username)
        if not user.id:
            from app.x.exceptions import XNotFoundError

            raise XNotFoundError("The requested X user has no usable id.")
        key = f"tweets:{user.id}:{limit}:{cursor or '-'}:{int(include_replies)}"
        cached = self.cache.get(key)
        if cached is not MISSING:
            return cached
        page = await self._call(
            lambda: self.client.get_user_tweets(
                user.id,
                limit=limit,
                cursor=cursor,
                include_replies=include_replies,
            )
        )
        data = PageData[Tweet](**page_to_data(page.items, page.next_cursor, tweet_to_model))
        return self.cache.set(key, data, self.settings.tweet_cache_ttl_seconds)

    async def search(
        self,
        *,
        query: str,
        product: str,
        limit: int,
        cursor: str | None,
    ) -> PageData:
        if not search_query_is_allowed(query, self.settings):
            raise SearchNotAllowedError("Search must include an allowed from:user filter.")
        key = f"search:{product}:{limit}:{cursor or '-'}:{query}"
        cached = self.cache.get(key)
        if cached is not MISSING:
            return cached
        page = await self._call(
            lambda: self.client.search_tweets(
                query,
                product=product,
                limit=limit,
                cursor=cursor,
            )
        )
        data = PageData[Tweet](**page_to_data(page.items, page.next_cursor, tweet_to_model))
        return self.cache.set(key, data, self.settings.search_cache_ttl_seconds)

    async def search_pages(
        self,
        *,
        query: str,
        product: str,
        pages: int | None,
        limit: int,
        page_size: int,
        item_filter: Callable[[Any], bool] | None = None,
        stop_before: Callable[[Any], bool] | None = None,
        diagnostic_range: str | None = None,
        progress_callback: Callable[[int, int, bool], None] | None = None,
        retry_policy: RetryPolicy | None = None,
        start_cursor: str | None = None,
        seen_ids: set[str] | None = None,
        seen_cursors: dict[str, int] | None = None,
    ) -> tuple[list[Any], str | None, int, str | None]:
        """Fetch bounded search pages while preserving raw Twikit tweet objects."""

        if not search_query_is_allowed(query, self.settings):
            raise SearchNotAllowedError("Search must include an allowed from:user filter.")

        max_results = min(max(1, limit), self.settings.max_results)
        batch_size = min(max(1, page_size), self.settings.page_size, 20)
        # When pages is omitted, treat the result limit as the stopping target and
        # keep a server-side page cap available for short or overlapping pages.
        # In the common case, limit=100 still stops after five 20-item pages.
        requested_pages = self.settings.max_pages if pages is None else max(1, pages)
        max_pages = min(requested_pages, self.settings.max_pages)
        cursor = start_cursor
        items: list[Any] = []
        if seen_ids is None:
            seen_ids = set()
        if seen_cursors is None:
            seen_cursors = {}
        pages_fetched = 0
        pagination_issue: str | None = None

        for _ in range(max_pages):
            remaining = max_results - len(items)
            if remaining <= 0:
                break
            count = min(batch_size, remaining)
            current_cursor = cursor
            if current_cursor is not None:
                seen_cursors.setdefault(current_cursor, len(seen_cursors) + 1)
            page_started = time.perf_counter()
            try:
                page = await self._call(
                    lambda current_cursor=current_cursor, count=count: self.client.search_tweets(
                        query,
                        product=product,
                        limit=count,
                        cursor=current_cursor,
                    ),
                    retry_policy=retry_policy,
                )
            except Exception as error:
                mapped = map_twikit_error(error)
                logger.warning(
                    "X search page failed: page=%d elapsed_ms=%d status=%s "
                    "retry_after_seconds=%s",
                    pages_fetched + 1,
                    round((time.perf_counter() - page_started) * 1000),
                    mapped.status_code,
                    mapped.retry_after,
                )
                raise
            page_elapsed_ms = round((time.perf_counter() - page_started) * 1000)
            pages_fetched += 1
            matched_tweets = (
                sum(1 for item in page.items if item_filter(item))
                if item_filter is not None
                else len(page.items)
            )
            stop_paging = False
            for item in page.items:
                item_id = str(getattr(item, "id", ""))
                if item_id and item_id in seen_ids:
                    continue
                if item_id:
                    seen_ids.add(item_id)
                if stop_before is not None and stop_before(item):
                    stop_paging = True
                    break
                if item_filter is not None and not item_filter(item):
                    continue
                items.append(item)
                if len(items) >= max_results:
                    break
            selected_next_cursor = page.next_cursor
            next_cursor = None if page.terminal_reason else selected_next_cursor
            raw_entries_count = (
                page.raw_entries_count
                if page.raw_entries_count is not None
                else len(page.items)
            )
            raw_tweet_count = (
                page.raw_tweet_count
                if page.raw_tweet_count is not None
                else len(page.items)
            )
            cursor_candidates = ",".join(
                f"{kind}:{fingerprint}"
                for kind, fingerprint in page.cursor_candidates[:8]
            ) or "none"
            instruction_types = ",".join(page.instruction_types[:8]) or "none"
            if self.settings.x_pagination_diagnostics:
                logger.info(
                    "X search pagination page: range=%s page=%d elapsed_ms=%d "
                    "raw_entries=%d raw_tweets=%d response_tweets=%d "
                    "matched_tweets=%d filtered_tweets=%d cursor_candidates=%s "
                    "instruction_types=%s terminal_reason=%s "
                    "selected_next_cursor=%s previous_cursor=%s new_cursor=%s "
                    "deduplicated_total_count=%d",
                    diagnostic_range or "unspecified",
                    pages_fetched,
                    page_elapsed_ms,
                    raw_entries_count,
                    raw_tweet_count,
                    len(page.items),
                    matched_tweets,
                    max(len(page.items) - matched_tweets, 0),
                    cursor_candidates,
                    instruction_types,
                    page.terminal_reason or "none",
                    cursor_fingerprint(selected_next_cursor) or "none",
                    cursor_fingerprint(current_cursor) or "none",
                    cursor_fingerprint(next_cursor) or "none",
                    len(items),
                )
            logger.debug(
                "X search page completed: page=%d elapsed_ms=%d response_tweets=%d "
                "unique_results=%d cursor_present=%s",
                pages_fetched,
                page_elapsed_ms,
                len(page.items),
                len(items),
                bool(next_cursor),
            )
            if stop_paging:
                cursor = None
                if progress_callback is not None:
                    progress_callback(pages_fetched, len(items), False)
                break
            if next_cursor and next_cursor in seen_cursors:
                # A cursor cycle does not prove the upstream range is complete.
                # Stop replaying the same page and preserve an explicit issue.
                pagination_issue = "cursor_cycle"
                repeated_page = seen_cursors[next_cursor]
                logger.warning(
                    "X search cursor cycle detected: range=%s page=%d "
                    "repeat_of_page=%d raw_entries=%d raw_tweets=%d "
                    "cursor_candidates=%s previous_cursor=%s new_cursor=%s "
                    "deduplicated_total_count=%d",
                    diagnostic_range or "unspecified",
                    pages_fetched,
                    repeated_page,
                    raw_entries_count,
                    raw_tweet_count,
                    cursor_candidates,
                    cursor_fingerprint(current_cursor) or "none",
                    cursor_fingerprint(next_cursor) or "none",
                    len(items),
                )
                cursor = None
                if progress_callback is not None:
                    progress_callback(pages_fetched, len(items), True)
                break
            if not next_cursor:
                cursor = None
                if progress_callback is not None:
                    progress_callback(pages_fetched, len(items), False)
                break
            cursor = next_cursor
            if progress_callback is not None:
                progress_callback(pages_fetched, len(items), True)

        return items[:max_results], cursor, pages_fetched, pagination_issue

    async def search_daily_stats(
        self,
        *,
        query: str,
        product: str,
        start_date: str,
        end_date: str,
        limit: int,
        progress_callback: Callable[[int, int, bool], None] | None = None,
        retry_policy: RetryPolicy | None = None,
        start_cursor: str | None = None,
        seen_ids: set[str] | None = None,
        seen_cursors: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Search within an inclusive JST date range and count posts per day."""
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError as error:
            raise ValueError("start_date and end_date must use YYYY-MM-DD format.") from error
        if start > end:
            raise ValueError("start_date must be on or before end_date.")

        def local_post_day(item: Any) -> date | None:
            created_at = _tweet_created_at(item)
            if created_at is None:
                return None
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            return created_at.astimezone(JAPAN_TZ).date()

        bounded_query = _query_for_date_range(query, start, end)
        items, next_cursor, pages_fetched, pagination_issue = await self.search_pages(
            query=bounded_query,
            product=product,
            pages=self.settings.max_pages,
            limit=limit,
            page_size=self.settings.page_size,
            diagnostic_range=f"{start.isoformat()}..{end.isoformat()}",
            item_filter=lambda item: (
                (day := local_post_day(item)) is not None and start <= day <= end
            ),
            stop_before=(
                (lambda item: (day := local_post_day(item)) is not None and day < start)
                if product == "Latest"
                else None
            ),
            progress_callback=progress_callback,
            retry_policy=retry_policy,
            start_cursor=start_cursor,
            seen_ids=seen_ids,
            seen_cursors=seen_cursors,
        )

        counts: dict[str, int] = defaultdict(int)
        for item in items:
            day = local_post_day(item)
            if day is not None:
                counts[day] += 1

        daily: list[dict[str, Any]] = []
        current_day = start
        total_posts = sum(counts.values())
        while current_day <= end:
            day = current_day.isoformat()
            daily.append({"date": day, "count": counts[current_day]})
            current_day += timedelta(days=1)
        return {
            "query": query,
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "timezone": "Asia/Tokyo",
            },
            "total_posts": total_posts,
            "daily": daily,
            "requested_limit": limit,
            "applied_limit": min(max(1, limit), self.settings.max_results),
            "result_count": total_posts,
            "fetched_posts": len(items),
            "has_more": bool(next_cursor),
            "next_cursor": next_cursor,
            "pagination_complete": not bool(next_cursor) and pagination_issue is None,
            "pagination_issue": pagination_issue,
            "pages_fetched": pages_fetched,
        }

    async def search_daily_stats_complete(
        self,
        *,
        query: str,
        product: str,
        start_date: str,
        end_date: str,
        limit: int,
        progress_callback: Callable[[int, int, bool], None] | None = None,
        retry_policy: RetryPolicy | None = None,
        checkpoint: dict[str, Any] | None = None,
        checkpoint_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Count a JST date range, splitting any capped search window."""
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError as error:
            raise ValueError("start_date and end_date must use YYYY-MM-DD format.") from error
        if start > end:
            raise ValueError("start_date must be on or before end_date.")
        if (end - start).days + 1 > MAX_COMPLETE_DAILY_STATS_DAYS:
            raise ValueError(
                f"complete_range supports at most {MAX_COMPLETE_DAILY_STATS_DAYS} calendar days."
            )

        pending: list[tuple[date, date]] = []
        segment_start = start
        while segment_start <= end:
            segment_end = min(
                segment_start + timedelta(days=COMPLETE_DAILY_STATS_WINDOW_DAYS - 1),
                end,
            )
            pending.append((segment_start, segment_end))
            segment_start = segment_end + timedelta(days=1)

        counts: dict[date, int] = defaultdict(int)
        incomplete_ranges: list[dict[str, Any]] = []
        pages_fetched = 0
        scanned_posts = 0
        segments_fetched = 0

        def persist_checkpoint() -> None:
            if checkpoint_callback is not None:
                checkpoint_callback({
                    "query": query,
                    "product": product,
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": limit,
                    "pending": [[left.isoformat(), right.isoformat()] for left, right in pending],
                    "counts": {day.isoformat(): n for day, n in counts.items()},
                    "incomplete_ranges": incomplete_ranges,
                    "pages_fetched": pages_fetched,
                    "scanned_posts": scanned_posts,
                    "segments_fetched": segments_fetched,
                })

        if checkpoint is not None and all(
            checkpoint.get(key) == value
            for key, value in {
                "query": query,
                "product": product,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
            }.items()
        ):
            try:
                resumed_pending = [
                    (date.fromisoformat(left), date.fromisoformat(right))
                    for left, right in checkpoint["pending"]
                ]
                if any(left < start or right > end or left > right for left, right in resumed_pending):
                    raise ValueError("Invalid window")
                resumed_counts = {
                    date.fromisoformat(day): int(n)
                    for day, n in checkpoint["counts"].items()
                }
                pending = resumed_pending
                counts.update(resumed_counts)
                incomplete_ranges = list(checkpoint["incomplete_ranges"])
                pages_fetched = int(checkpoint["pages_fetched"])
                scanned_posts = int(checkpoint["scanned_posts"])
                segments_fetched = int(checkpoint["segments_fetched"])
            except (KeyError, TypeError, ValueError):
                # Safest fallback for invalid state is a fresh full scan.
                pending.clear()
                cursor_day = start
                while cursor_day <= end:
                    stop_day = min(
                        cursor_day + timedelta(days=COMPLETE_DAILY_STATS_WINDOW_DAYS - 1), end
                    )
                    pending.append((cursor_day, stop_day))
                    cursor_day = stop_day + timedelta(days=1)
                counts.clear()
                incomplete_ranges.clear()
                pages_fetched = 0
                scanned_posts = 0
                segments_fetched = 0

        while pending:
            window_start, window_end = pending.pop(0)
            window_counts: dict[date, int] = defaultdict(int)
            window_seen_ids: set[str] = set()
            window_seen_cursors: dict[str, int] = {}
            window_cursor: str | None = None
            window_pages = 0
            empty_chunks = 0
            incomplete_reason: str | None = None
            split_window = False

            while True:
                pages_before = pages_fetched
                posts_before = scanned_posts

                def report_window_progress(
                    pages: int,
                    posts: int,
                    has_more: bool,
                    *,
                    base_pages: int = pages_before,
                    base_posts: int = posts_before,
                ) -> None:
                    if progress_callback is not None:
                        progress_callback(base_pages + pages, base_posts + posts, has_more)

                result = await self.search_daily_stats(
                    query=query,
                    product=product,
                    start_date=window_start.isoformat(),
                    end_date=window_end.isoformat(),
                    limit=limit,
                    progress_callback=report_window_progress,
                    retry_policy=retry_policy,
                    start_cursor=window_cursor,
                    seen_ids=window_seen_ids,
                    seen_cursors=window_seen_cursors,
                )
                segments_fetched += 1
                pages_fetched += result["pages_fetched"]
                window_pages += result["pages_fetched"]
                scanned_posts += result["fetched_posts"]

                window_incomplete = bool(result["has_more"] or result.get("pagination_issue"))
                if window_incomplete and window_start < window_end:
                    midpoint = window_start + (window_end - window_start) // 2
                    pending[0:0] = [
                        (window_start, midpoint),
                        (midpoint + timedelta(days=1), window_end),
                    ]
                    split_window = True
                    if progress_callback is not None:
                        progress_callback(pages_fetched, scanned_posts, True)
                    break

                if window_cursor is not None and result["next_cursor"] == window_cursor:
                    incomplete_reason = "cursor_cycle"
                    break
                for bucket in result["daily"]:
                    bucket_day = date.fromisoformat(bucket["date"])
                    window_counts[bucket_day] += bucket["count"]

                if result.get("pagination_issue"):
                    incomplete_reason = result["pagination_issue"]
                    break
                if not result["has_more"]:
                    break
                if not result["next_cursor"]:
                    incomplete_reason = "missing_cursor"
                    break
                if window_pages >= MAX_COMPLETE_SINGLE_DAY_PAGES:
                    incomplete_reason = "page_budget_exceeded"
                    break
                empty_chunks = empty_chunks + 1 if result["fetched_posts"] == 0 else 0
                if empty_chunks >= 2:
                    incomplete_reason = "stalled_pagination"
                    break
                window_cursor = result["next_cursor"]

            if split_window:
                persist_checkpoint()
                continue
            for bucket_day, count in window_counts.items():
                counts[bucket_day] += count

            if incomplete_reason:
                incomplete_range = {
                    "start": window_start.isoformat(),
                    "end": window_end.isoformat(),
                    "posts_returned": sum(window_counts.values()),
                    "reason": incomplete_reason,
                }
                incomplete_ranges.append(incomplete_range)
            persist_checkpoint()
            if progress_callback is not None:
                progress_callback(
                    pages_fetched,
                    scanned_posts,
                    bool(incomplete_reason),
                )

        daily: list[dict[str, Any]] = []
        current_day = start
        while current_day <= end:
            daily.append(
                {
                    "date": current_day.isoformat(),
                    "count": counts[current_day],
                }
            )
            current_day += timedelta(days=1)

        total_posts = sum(counts.values())
        coverage_complete = not incomplete_ranges
        return {
            "query": query,
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "timezone": "Asia/Tokyo",
            },
            "total_posts": total_posts,
            "daily": daily,
            "requested_limit": limit,
            "applied_limit": min(max(1, limit), self.settings.max_results),
            "limit_scope": "per_search_window",
            "result_count": total_posts,
            "fetched_posts": total_posts,
            "scanned_posts": scanned_posts,
            "has_more": not coverage_complete,
            "next_cursor": None,
            "pages_fetched": pages_fetched,
            "segments_fetched": segments_fetched,
            "coverage_complete": coverage_complete,
            "pagination_complete": coverage_complete,
            "count_is_lower_bound": not coverage_complete,
            "incomplete_ranges": incomplete_ranges,
        }

    async def user_tweets_pages(
        self,
        username: str,
        *,
        pages: int,
        limit: int,
        page_size: int,
        include_replies: bool = False,
    ) -> tuple[list[Any], str | None, int]:
        """Fetch bounded user-timeline pages while preserving raw tweet fields."""

        user = await self.user_profile(username)
        if not user.id:
            from app.x.exceptions import XNotFoundError

            raise XNotFoundError("The requested X user has no usable id.")

        max_pages = min(max(1, pages), self.settings.max_pages)
        max_results = min(max(1, limit), self.settings.max_results)
        batch_size = min(max(1, page_size), self.settings.page_size, 40)
        cursor: str | None = None
        items: list[Any] = []
        seen_ids: set[str] = set()
        pages_fetched = 0

        for _ in range(max_pages):
            remaining = max_results - len(items)
            if remaining <= 0:
                break
            count = min(batch_size, remaining)
            current_cursor = cursor
            page = await self._call(
                lambda current_cursor=current_cursor, count=count: self.client.get_user_tweets(
                    user.id,
                    limit=count,
                    cursor=current_cursor,
                    include_replies=include_replies,
                )
            )
            pages_fetched += 1
            for item in page.items:
                item_id = str(getattr(item, "id", ""))
                if item_id and item_id in seen_ids:
                    continue
                if item_id:
                    seen_ids.add(item_id)
                items.append(item)
                if len(items) >= max_results:
                    break
            next_cursor = page.next_cursor
            if not next_cursor or next_cursor == current_cursor:
                cursor = next_cursor
                break
            cursor = next_cursor

        return items[:max_results], cursor, pages_fetched

    async def tweet_detail(self, tweet_id: str):
        key = f"tweet:{tweet_id}"
        cached = self.cache.get(key)
        if cached is not MISSING:
            return cached
        tweet = await self._call(lambda: self.client.get_tweet_by_id(tweet_id))
        data = tweet_to_model(tweet)
        if data is None:
            from app.x.exceptions import XNotFoundError

            raise XNotFoundError("The requested X post was not found.")
        return self.cache.set(key, data, self.settings.tweet_cache_ttl_seconds)


def _query_for_date_range(query: str, start: date, end: date) -> str:
    """Add exact Unix-time bounds for inclusive JST calendar dates."""
    tokens = [
        token
        for token in query.split()
        if not token.casefold().startswith(
            ("since:", "until:", "since_time:", "until_time:")
        )
    ]
    start_at = datetime(start.year, start.month, start.day, tzinfo=JAPAN_TZ)
    end_date = end + timedelta(days=1)
    end_at = datetime(end_date.year, end_date.month, end_date.day, tzinfo=JAPAN_TZ)
    tokens.extend(
        (
            f"since_time:{int(start_at.timestamp())}",
            f"until_time:{int(end_at.timestamp())}",
        )
    )
    return " ".join(tokens)


def _tweet_created_at(tweet: Any) -> datetime | None:
    try:
        created_at = getattr(tweet, "created_at_datetime", None)
    except (AttributeError, TypeError, ValueError):
        created_at = None
    if isinstance(created_at, datetime):
        return created_at
    raw_created_at = getattr(tweet, "created_at", None)
    if not isinstance(raw_created_at, str):
        return None
    try:
        return datetime.fromisoformat(raw_created_at)
    except ValueError:
        try:
            return datetime.strptime(raw_created_at, "%a %b %d %H:%M:%S %z %Y")
        except ValueError:
            return None
