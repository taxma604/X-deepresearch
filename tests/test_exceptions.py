from typing import ClassVar

from app.x.exceptions import XRateLimitError, map_twikit_error


def test_rate_limit_mapping_keeps_retry_after_without_raw_body() -> None:
    class TooManyRequests(Exception):
        headers: ClassVar[dict[str, str]] = {"retry-after": "3"}

    mapped = map_twikit_error(TooManyRequests("cookie=must-not-leak"))
    assert isinstance(mapped, XRateLimitError)
    assert mapped.retry_after == 3
    assert mapped.message == "X rate limit reached."


def test_rate_limit_mapping_uses_twikit_reset_timestamp(monkeypatch) -> None:
    monkeypatch.setattr("app.x.exceptions.time.time", lambda: 1_000.0)

    class TooManyRequests(Exception):
        headers: ClassVar[dict[str, str]] = {"x-rate-limit-reset": "1060"}
        rate_limit_reset = 1060

    mapped = map_twikit_error(TooManyRequests("private upstream detail"))

    assert isinstance(mapped, XRateLimitError)
    assert mapped.retry_after == 60
    assert mapped.message == "X rate limit reached."


def test_rate_limit_mapping_accepts_http_date_retry_after(monkeypatch) -> None:
    from email.utils import formatdate

    monkeypatch.setattr("app.x.exceptions.time.time", lambda: 1_000.0)

    class TooManyRequests(Exception):
        headers: ClassVar[dict[str, str]] = {
            "Retry-After": formatdate(1_007, usegmt=True),
        }

    mapped = map_twikit_error(TooManyRequests("private upstream detail"))

    assert isinstance(mapped, XRateLimitError)
    assert mapped.retry_after == 7


def test_upstream_502_mapping_preserves_safe_retry_after() -> None:
    class BadGateway(Exception):
        status_code = 502
        headers: ClassVar[dict[str, str]] = {"retry-after": "4"}

    mapped = map_twikit_error(BadGateway("private upstream response"))

    assert mapped.status_code == 502
    assert mapped.retry_after == 4
    assert mapped.message == "X request failed."
