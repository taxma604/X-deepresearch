import time
from typing import ClassVar

import pytest

from app.config import Settings
from app.services.rate_limiter import AsyncRequestLimiter, RetryPolicy
from app.x.exceptions import XApiError, XRateLimitError


def test_default_request_pacing_allows_sixty_requests_per_minute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("X_RATE_LIMIT_PER_MINUTE", raising=False)
    settings = Settings(_env_file=None)

    assert settings.rate_limit_per_minute == 60
    limiter = AsyncRequestLimiter(
        max_concurrent=settings.max_concurrent_requests,
        min_interval_seconds=settings.min_request_interval_seconds,
        rate_per_minute=settings.rate_limit_per_minute,
    )
    assert limiter._interval == 1.0


async def test_retry_policy_uses_bounded_exponential_backoff() -> None:
    attempts = 0
    delays: list[float] = []

    async def sleep(delay: float) -> None:
        delays.append(delay)

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise XRateLimitError("limited", retry_after=0)
        return "ok"

    result = await RetryPolicy(
        max_retries=2,
        base_seconds=1,
        max_seconds=10,
        sleep=sleep,
    ).run(operation)
    assert result == "ok"
    assert attempts == 3
    assert delays == [1, 2]


async def test_retry_policy_does_not_retry_non_retryable_4xx_errors() -> None:
    attempts = 0

    async def operation() -> None:
        nonlocal attempts
        attempts += 1
        raise XApiError("forbidden", status_code=403)

    with pytest.raises(XApiError) as raised:
        await RetryPolicy(max_retries=3, base_seconds=1, max_seconds=10).run(operation)

    assert raised.value.status_code == 403
    assert attempts == 1


async def test_retry_policy_retries_transient_upstream_502() -> None:
    attempts = 0
    delays: list[float] = []
    reported_rate_limit_waits: list[float] = []

    async def sleep(delay: float) -> None:
        delays.append(delay)

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise XApiError("private upstream body", status_code=502)
        return "ok"

    result = await RetryPolicy(
        max_retries=2,
        base_seconds=1,
        max_seconds=10,
        sleep=sleep,
        on_wait=reported_rate_limit_waits.append,
    ).run(operation)

    assert result == "ok"
    assert attempts == 3
    assert delays == [1, 2]
    assert reported_rate_limit_waits == []


async def test_retry_after_longer_than_budget_is_returned_without_retry() -> None:
    attempts = 0
    delays: list[float] = []

    async def sleep(delay: float) -> None:
        delays.append(delay)

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise XRateLimitError("limited", retry_after=999999)
        return "ok"

    with pytest.raises(XRateLimitError) as raised:
        await RetryPolicy(
            max_retries=1,
            base_seconds=1,
            max_seconds=5,
            sleep=sleep,
        ).run(operation)

    assert attempts == 1
    assert delays == []
    assert raised.value.retry_after == 999999


async def test_retry_after_within_budget_is_honored() -> None:
    attempts = 0
    delays: list[float] = []
    reported_waits: list[float] = []

    async def sleep(delay: float) -> None:
        delays.append(delay)

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise XRateLimitError("limited", retry_after=3)
        return "ok"

    result = await RetryPolicy(
        max_retries=1,
        base_seconds=1,
        max_seconds=5,
        sleep=sleep,
        on_wait=reported_waits.append,
    ).run(operation)

    assert result == "ok"
    assert attempts == 2
    assert delays == [3]
    assert reported_waits == [3]


async def test_shared_limiter_observes_and_reports_upstream_cooldown() -> None:
    limiter = AsyncRequestLimiter(
        max_concurrent=1,
        min_interval_seconds=0,
        rate_per_minute=600,
    )
    await limiter.defer_for(0.15)
    waits: list[float] = []
    started = time.monotonic()

    async with limiter.slot(on_rate_limit_wait=waits.append):
        pass

    assert time.monotonic() - started >= 0.13
    assert waits and waits[0] >= 0.13


async def test_regular_request_pacing_is_not_reported_as_rate_limit_wait() -> None:
    limiter = AsyncRequestLimiter(
        max_concurrent=1,
        min_interval_seconds=0,
        rate_per_minute=600,
    )
    waits: list[float] = []

    async with limiter.slot(on_rate_limit_wait=waits.append):
        pass
    async with limiter.slot(on_rate_limit_wait=waits.append):
        pass

    assert waits == []


async def test_retry_policy_uses_twikit_rate_limit_reset(monkeypatch) -> None:
    monkeypatch.setattr("app.x.exceptions.time.time", lambda: 1_000.0)
    attempts = 0
    delays: list[float] = []

    class TooManyRequests(Exception):
        headers: ClassVar[dict[str, str]] = {"x-rate-limit-reset": "1045"}
        rate_limit_reset = 1045

    async def sleep(delay: float) -> None:
        delays.append(delay)

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TooManyRequests("private upstream detail")
        return "ok"

    result = await RetryPolicy(
        max_retries=1,
        base_seconds=1,
        max_seconds=60,
        sleep=sleep,
    ).run(operation)

    assert result == "ok"
    assert attempts == 2
    assert delays == [45]
