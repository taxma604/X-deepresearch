from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

MISSING = object()


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    """Small process-local TTL cache for read responses."""

    def __init__(self) -> None:
        self._entries: dict[str, _CacheEntry] = {}

    def get(self, key: str) -> Any:
        entry = self._entries.get(key)
        if entry is None:
            return MISSING
        if entry.expires_at <= time.monotonic():
            self._entries.pop(key, None)
            return MISSING
        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: float) -> Any:
        if ttl_seconds > 0:
            self._entries[key] = _CacheEntry(
                value=value,
                expires_at=time.monotonic() + ttl_seconds,
            )
        return value

    def clear(self) -> None:
        self._entries.clear()
