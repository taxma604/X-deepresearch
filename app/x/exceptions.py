from __future__ import annotations

import time
from datetime import UTC
from email.utils import parsedate_to_datetime
from typing import Any


class XApiError(Exception):
    status_code = 502
    code = "x_upstream_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.retry_after = retry_after


class AuthConfigurationError(XApiError):
    status_code = 503
    code = "auth_not_configured"


class DependencyError(XApiError):
    status_code = 503
    code = "dependency_unavailable"


class XNotFoundError(XApiError):
    status_code = 404
    code = "not_found"


class XRateLimitError(XApiError):
    status_code = 429
    code = "rate_limited"


class SearchNotAllowedError(XApiError):
    status_code = 403
    code = "search_not_allowed"


def _retry_after_from_headers(headers: Any) -> float | None:
    if not headers:
        return None
    try:
        raw = headers.get("retry-after")
        if raw is None:
            raw = headers.get("Retry-After")
        if raw is None:
            return None
        try:
            return max(float(str(raw).strip()), 0.0)
        except ValueError:
            retry_at = parsedate_to_datetime(str(raw).strip())
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=UTC)
            return max(retry_at.timestamp() - time.time(), 0.0)
    except (AttributeError, OverflowError, TypeError, ValueError):
        return None


def _retry_after_from_rate_limit_reset(error: Exception, headers: Any) -> float | None:
    reset_at = getattr(error, "rate_limit_reset", None)
    if reset_at is None and headers:
        try:
            reset_at = headers.get("x-rate-limit-reset")
            if reset_at is None:
                reset_at = headers.get("X-Rate-Limit-Reset")
        except AttributeError:
            return None
    if reset_at is None:
        return None
    try:
        return max(float(str(reset_at).strip()) - time.time(), 0.0)
    except (OverflowError, TypeError, ValueError):
        return None


def map_twikit_error(error: Exception) -> XApiError:
    """Map an upstream exception to a safe, cookie-free API error."""

    if isinstance(error, XApiError):
        return error

    name = error.__class__.__name__
    headers = getattr(error, "headers", None)
    status = getattr(error, "status_code", None)
    if not isinstance(status, int):
        status = 429 if name in {"TooManyRequests", "RateLimitError"} else None

    if status == 401 or name in {"Unauthorized", "AccountLocked", "AccountSuspended"}:
        return XApiError("X authentication was rejected.", status_code=401)
    if status == 403 or name == "Forbidden":
        return XApiError("X rejected this request.", status_code=403)
    if status == 404 or name in {"NotFound", "UserNotFound", "TweetNotAvailable"}:
        return XNotFoundError("The requested X resource was not found.")
    if status == 429 or name in {"TooManyRequests", "RateLimitError"}:
        retry_after = _retry_after_from_headers(headers)
        if retry_after is None:
            retry_after = _retry_after_from_rate_limit_reset(error, headers)
        return XRateLimitError(
            "X rate limit reached.",
            retry_after=retry_after,
        )

    if status == 408:
        return XApiError(
            "X request timed out.",
            status_code=408,
            retry_after=_retry_after_from_headers(headers),
        )

    if isinstance(status, int) and status in {500, 502, 503, 504}:
        return XApiError(
            "X request failed.",
            status_code=status,
            retry_after=_retry_after_from_headers(headers),
        )

    if isinstance(status, int) and 400 <= status < 500:
        return XApiError("X rejected the request.", status_code=status)
    return XApiError("X request failed.")
