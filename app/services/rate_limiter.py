from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TypeVar

from app.x.exceptions import XApiError, map_twikit_error

T = TypeVar("T")
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class AsyncRequestLimiter:
    """Limit concurrent requests and pace calls to X."""

    def __init__(
        self,
        *,
        max_concurrent: int,
        min_interval_seconds: float,
        rate_per_minute: float,
    ) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = asyncio.Lock()
        rate_interval = 60.0 / rate_per_minute if rate_per_minute > 0 else 0.0
        self._interval = max(min_interval_seconds, rate_interval)
        self._next_allowed_at = 0.0
        self._rate_limit_until = 0.0

    @asynccontextmanager
    async def slot(
        self,
        *,
        on_rate_limit_wait: Callable[[float], None] | None = None,
    ) -> AsyncIterator[None]:
        await self._semaphore.acquire()
        try:
            async with self._lock:
                now = time.monotonic()
                wait = self._next_allowed_at - now
                rate_limit_wait = self._rate_limit_until - now
                if rate_limit_wait > 0 and on_rate_limit_wait is not None:
                    on_rate_limit_wait(rate_limit_wait)
                if wait > 0:
                    await asyncio.sleep(wait)
                self._next_allowed_at = time.monotonic() + self._interval
            yield
        finally:
            self._semaphore.release()

    async def defer_for(self, seconds: float) -> None:
        """Share an upstream cooldown with every request using this limiter."""
        if seconds <= 0:
            return
        async with self._lock:
            rate_limit_until = time.monotonic() + seconds
            self._rate_limit_until = max(self._rate_limit_until, rate_limit_until)
            self._next_allowed_at = max(
                self._next_allowed_at,
                rate_limit_until,
            )


def retry_after_seconds(error: Exception) -> float | None:
    mapped = map_twikit_error(error)
    if mapped.status_code in RETRYABLE_STATUS_CODES:
        return mapped.retry_after
    return None


class RetryPolicy:
    """Bounded retries for rate limits and transient upstream failures."""

    def __init__(
        self,
        *,
        max_retries: int,
        base_seconds: float,
        max_seconds: float,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        on_wait: Callable[[float], None] | None = None,
    ) -> None:
        self.max_retries = max_retries
        self.base_seconds = base_seconds
        self.max_seconds = max_seconds
        self.sleep = sleep
        self.on_wait = on_wait

    async def run(self, operation: Callable[[], Awaitable[T]]) -> T:
        for attempt in range(self.max_retries + 1):
            try:
                return await operation()
            except Exception as error:  # noqa: BLE001 - normalize arbitrary upstream errors
                mapped = map_twikit_error(error)
                if (
                    mapped.status_code not in RETRYABLE_STATUS_CODES
                    or attempt >= self.max_retries
                ):
                    raise mapped from None
                exponential = min(self.max_seconds, self.base_seconds * (2**attempt))
                retry_after = retry_after_seconds(error)
                if retry_after is not None and retry_after > self.max_seconds:
                    # Do not retry before the upstream's requested wait. Surface
                    # the error so callers can retry later instead of holding an
                    # MCP request open and repeating a request that will fail.
                    raise mapped from None
                delay = max(exponential, retry_after or 0.0)
                if mapped.status_code == 429 and self.on_wait is not None:
                    self.on_wait(delay)
                await self.sleep(delay)
        raise XApiError("X request failed.")
