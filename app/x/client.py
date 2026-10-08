from __future__ import annotations

import asyncio
import hashlib
import inspect
import sys
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from app.config import Settings

from .auth import require_cookie_credentials
from .exceptions import DependencyError, XNotFoundError


@dataclass(frozen=True)
class XPage:
    items: list[Any]
    next_cursor: str | None = field(default=None, repr=False)
    raw_entries_count: int | None = None
    raw_tweet_count: int | None = None
    cursor_candidates: tuple[tuple[str, str], ...] = ()
    instruction_types: tuple[str, ...] = ()
    terminal_reason: str | None = None


@dataclass(frozen=True)
class _RawCursorCandidate:
    kind: str
    value: str = field(repr=False)
    priority: int = field(repr=False)


def cursor_fingerprint(value: str | None) -> str | None:
    """Return a safe short fingerprint without exposing the opaque cursor."""
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _prepare_twikit_import() -> None:
    """Expose the Python 3.12-compatible Js2Py namespace to twikit 2.3.1."""

    try:
        import js2py_ as compatible_js2py
    except ImportError:
        return
    sys.modules["js2py"] = compatible_js2py


def extract_cursor_value(entry: dict[str, Any]) -> str | None:
    """Read both cursor shapes seen in X timeline responses.

    X has used ``content.itemContent.value`` and ``content.value`` for top-level
    entries, and the same two shapes below ``item`` for nested reply cursors.
    """

    def find_value(value: Any) -> str | None:
        if isinstance(value, dict):
            for key in ("value", "continuation"):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate:
                    return candidate
            for key in ("content", "item", "itemContent", "cursor", "operation", "entry"):
                if key in value:
                    candidate = find_value(value[key])
                    if candidate is not None:
                        return candidate
        elif isinstance(value, list):
            for child in value:
                candidate = find_value(child)
                if candidate is not None:
                    return candidate
        return None

    return find_value(entry)


def _entries_from_payload(payload: Any) -> list[dict[str, Any]]:
    """Extract the first timeline entry list without assuming one response shape."""

    def walk(value: Any):
        if isinstance(value, dict):
            if isinstance(value.get("entries"), list):
                return value["entries"]
            for child in value.values():
                found = walk(child)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = walk(child)
                if found is not None:
                    return found
        return None

    entries = walk(payload)
    return [item for item in (entries or []) if isinstance(item, dict)]


def _cursor_candidates_from_entries(
    entries: list[dict[str, Any]],
) -> list[_RawCursorCandidate]:
    candidates: list[_RawCursorCandidate] = []
    for entry in entries:
        content = entry.get("content") or {}
        item_content = content.get("itemContent") if isinstance(content, dict) else None
        cursor_type = ""
        if isinstance(content, dict):
            cursor_type = str(content.get("cursorType", ""))
        if isinstance(item_content, dict) and not cursor_type:
            cursor_type = str(item_content.get("cursorType", ""))

        entry_id = str(entry.get("entryId", "")).casefold()
        kind = cursor_type.casefold()
        is_cursor = entry_id.startswith("cursor") or (
            isinstance(content, dict)
            and content.get("entryType") == "TimelineTimelineCursor"
        )
        if not is_cursor:
            continue

        if "top" in entry_id or kind == "top":
            candidate_kind = "top"
            priority = 0
        elif "bottom" in entry_id or kind == "bottom":
            candidate_kind = "bottom"
            priority = 3
        elif "showmore" in entry_id or "show_more" in entry_id or "show more" in kind:
            candidate_kind = "show_more"
            priority = 2
        else:
            candidate_kind = "other"
            priority = 1

        value = extract_cursor_value(entry)
        if value is not None:
            candidates.append(
                _RawCursorCandidate(
                    kind=candidate_kind,
                    value=value,
                    priority=priority,
                )
            )
    return candidates


def _select_cursor_candidate(
    candidates: list[_RawCursorCandidate],
) -> _RawCursorCandidate | None:
    selected: _RawCursorCandidate | None = None
    for candidate in candidates:
        if candidate.priority > 0 and (
            selected is None or candidate.priority >= selected.priority
        ):
            selected = candidate
    return selected


def _cursor_from_entries(entries: list[dict[str, Any]]) -> str | None:
    selected = _select_cursor_candidate(_cursor_candidates_from_entries(entries))
    return selected.value if selected is not None else None


def _timeline_instructions_from_payload(payload: Any) -> list[dict[str, Any]]:
    instructions: list[dict[str, Any]] = []
    seen: set[int] = set()

    def find_instruction_lists(value: Any) -> None:
        if isinstance(value, dict):
            children = value.get("instructions")
            if isinstance(children, list):
                for instruction in children:
                    if isinstance(instruction, dict) and id(instruction) not in seen:
                        seen.add(id(instruction))
                        instructions.append(instruction)
            for key, child in value.items():
                if key != "instructions":
                    find_instruction_lists(child)
        elif isinstance(value, list):
            for child in value:
                find_instruction_lists(child)

    find_instruction_lists(payload)
    return instructions


def _timeline_entries_from_payload(payload: Any) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[int] = set()

    def add_entry(value: Any) -> None:
        if isinstance(value, dict) and id(value) not in seen:
            seen.add(id(value))
            entries.append(value)

    for instruction in _timeline_instructions_from_payload(payload):
        values = instruction.get("entries")
        if isinstance(values, list):
            for entry in values:
                add_entry(entry)
        add_entry(instruction.get("entry"))
        module_items = instruction.get("moduleItems")
        if isinstance(module_items, list):
            for item in module_items:
                add_entry(item)

    return entries or _entries_from_payload(payload)


def _timeline_instruction_types(payload: Any) -> tuple[str, ...]:
    types = {
        instruction_type
        for instruction in _timeline_instructions_from_payload(payload)
        if isinstance((instruction_type := instruction.get("type")), str)
        and 0 < len(instruction_type) <= 80
        and instruction_type.isascii()
        and instruction_type.isidentifier()
    }
    return tuple(sorted(types))


def _timeline_terminal_reason(payload: Any) -> str | None:
    terminal_types = {
        "timelineterminatetimeline",
    }
    instructions = _timeline_instructions_from_payload(payload)
    if any(
        instruction.get("type", "").casefold() in terminal_types
        for instruction in instructions
        if isinstance(instruction.get("type"), str)
    ):
        return "terminate_instruction"

    instruction_types = _timeline_instruction_types(payload)
    cursor_candidates = _cursor_candidates_from_payload(payload)
    has_bottom_cursor = any(candidate.kind == "bottom" for candidate in cursor_candidates)
    if (
        instruction_types == ("TimelineReplaceEntry",)
        and _raw_tweet_count(_timeline_entries_from_payload(payload)) == 0
        and has_bottom_cursor
    ):
        # X may keep replacing its cursor entries after the final result page.
        # A cursor-only replacement has no tweet rows to continue to.
        return "cursor_only_replacement"
    return None


def _cursor_nodes_from_payload(payload: Any) -> list[dict[str, Any]]:
    """Find cursor entries across all timeline instruction shapes.

    SearchTimeline places cursors in ``TimelineAddEntries.entries`` on the first
    page, then may move them into ``TimelineReplaceEntry.entry`` on later pages.
    Looking only at the first ``entries`` list therefore misses later-page
    cursors even though the upstream response still contains a bottom cursor.
    """
    cursor_entries: list[dict[str, Any]] = []
    seen: set[int] = set()

    def collect_cursor_nodes(value: Any) -> None:
        if isinstance(value, dict):
            content = value.get("content")
            is_cursor = str(value.get("entryId", "")).casefold().startswith("cursor")
            if isinstance(content, dict) and content.get("entryType") == "TimelineTimelineCursor":
                is_cursor = True
            if is_cursor and id(value) not in seen:
                seen.add(id(value))
                cursor_entries.append(value)
            for child in value.values():
                collect_cursor_nodes(child)
        elif isinstance(value, list):
            for child in value:
                collect_cursor_nodes(child)

    for instruction in _timeline_instructions_from_payload(payload):
        collect_cursor_nodes(instruction)
    if cursor_entries:
        return cursor_entries
    return _entries_from_payload(payload)


def _cursor_candidates_from_payload(payload: Any) -> list[_RawCursorCandidate]:
    return _cursor_candidates_from_entries(_cursor_nodes_from_payload(payload))


def _cursor_from_payload(payload: Any) -> str | None:
    selected = _select_cursor_candidate(_cursor_candidates_from_payload(payload))
    return selected.value if selected is not None else None


def _raw_tweet_count(entries: list[dict[str, Any]]) -> int:
    count = 0
    for entry in entries:
        entry_id = str(entry.get("entryId", ""))
        content = entry.get("content") or {}
        if entry_id.startswith(("tweet", "profile-grid")):
            count += 1
        elif entry_id.startswith(("search-grid", "profile-conversation")) and isinstance(
            content, dict
        ):
            items = content.get("items") or []
            if isinstance(items, list):
                count += sum(isinstance(item, dict) for item in items)
    return count


def _page_cursor_diagnostics(
    payload: Any,
) -> tuple[str | None, tuple[tuple[str, str], ...]]:
    candidates = _cursor_candidates_from_payload(payload)
    selected = _select_cursor_candidate(candidates)
    safe_candidates = tuple(
        (candidate.kind, fingerprint)
        for candidate in candidates
        if (fingerprint := cursor_fingerprint(candidate.value)) is not None
    )
    return (selected.value if selected is not None else None), safe_candidates


def _normalize_user_result(data: Any) -> Any:
    """Fill optional user fields that twikit 2.3.1 still treats as mandatory."""

    if not isinstance(data, dict):
        return data
    legacy = data.get("legacy")
    if not isinstance(legacy, dict) or "rest_id" not in data:
        return data

    entities = legacy.setdefault("entities", {})
    if not isinstance(entities, dict):
        entities = {}
        legacy["entities"] = entities
    description = entities.setdefault("description", {})
    if not isinstance(description, dict):
        description = {}
        entities["description"] = description
    description.setdefault("urls", [])

    defaults = {
        "created_at": "",
        "name": "",
        "screen_name": "",
        "profile_image_url_https": "",
        "location": "",
        "description": "",
        "pinned_tweet_ids_str": [],
        "verified": False,
        "possibly_sensitive": False,
        "can_dm": False,
        "can_media_tag": False,
        "want_retweets": False,
        "default_profile": False,
        "default_profile_image": False,
        "has_custom_timelines": False,
        "followers_count": 0,
        "fast_followers_count": 0,
        "normal_followers_count": 0,
        "friends_count": 0,
        "favourites_count": 0,
        "listed_count": 0,
        "media_count": 0,
        "statuses_count": 0,
        "is_translator": False,
        "translator_type": "none",
        "withheld_in_countries": [],
    }
    for key, value in defaults.items():
        legacy.setdefault(key, value)
    data.setdefault("is_blue_verified", False)
    return data


def _normalize_user_payload(value: Any) -> Any:
    """Recursively normalize user result objects in GraphQL payloads."""

    if isinstance(value, dict):
        _normalize_user_result(value)
        for child in value.values():
            _normalize_user_payload(child)
    elif isinstance(value, list):
        for child in value:
            _normalize_user_payload(child)
    return value


def _unique_tweets(
    client: Any,
    entries: list[dict[str, Any]],
    *,
    include_replies: bool = False,
) -> list[Any]:
    _prepare_twikit_import()
    from twikit.tweet import tweet_from_data

    results: list[Any] = []
    seen: set[str] = set()

    def add(item: dict[str, Any]) -> None:
        _normalize_user_payload(item)
        try:
            tweet = tweet_from_data(client, item)
        except (KeyError, TypeError, ValueError):
            return
        if tweet is None:
            return
        tweet_id = str(getattr(tweet, "id", ""))
        if tweet_id and tweet_id in seen:
            return
        if tweet_id:
            seen.add(tweet_id)
        results.append(tweet)

    for entry in entries:
        entry_id = str(entry.get("entryId", ""))
        content = entry.get("content") or {}
        if entry_id.startswith("profile-conversation"):
            conversation = content.get("items") if isinstance(content, dict) else None
            if not isinstance(conversation, list):
                continue
            for index, item in enumerate(conversation):
                if not isinstance(item, dict):
                    continue
                if include_replies or index == 0:
                    add(item)
        elif entry_id.startswith(("tweet", "profile-grid")):
            add(entry)
        elif entry_id.startswith("search-grid") and isinstance(content, dict):
            items = content.get("items") or []
            for item in items:
                if isinstance(item, dict):
                    add(item)
    return results


def _safe_rate_limit_headers(headers: Any) -> dict[str, str]:
    """Keep only non-sensitive headers needed to schedule a safe X retry."""
    if not headers:
        return {}
    safe_headers: dict[str, str] = {}
    for name in ("retry-after", "x-rate-limit-reset"):
        value = headers.get(name)
        if value is None:
            value = headers.get(name.title())
        if value is not None:
            safe_headers[name] = str(value)
    return safe_headers


def _build_client(settings: Settings) -> Any:
    """Build twikit with the two small compatibility guards needed by current X."""

    _prepare_twikit_import()
    try:
        from twikit import Client as BaseClient
        from twikit.errors import (
            BadRequest,
            Forbidden,
            NotFound,
            RequestTimeout,
            ServerError,
            TooManyRequests,
            TwitterException,
            Unauthorized,
        )
    except ImportError as error:
        raise DependencyError("The twikit dependency is not installed.") from error

    class ResilientClient(BaseClient):
        _client_transaction_disabled = False

        async def request(
            self,
            method: str,
            url: str,
            auto_unlock: bool = True,
            raise_exception: bool = True,
            **kwargs: Any,
        ) -> tuple[dict | Any, Any]:
            """Keep read requests usable when X changes transaction-id assets."""

            headers = dict(kwargs.pop("headers", {}) or {})
            transaction = self.client_transaction
            if not self._client_transaction_disabled and not getattr(
                transaction, "home_page_response", None
            ):
                cookies_backup = self.get_cookies().copy()
                transaction_headers = {
                    "Accept-Language": f"{self.language},{self.language.split('-')[0]};q=0.9",
                    "Cache-Control": "no-cache",
                    "Referer": "https://x.com",
                    "User-Agent": self._user_agent,
                }
                try:
                    await transaction.init(self.http, transaction_headers)
                except Exception:  # noqa: BLE001 - transaction assets can fail in many ways
                    self._client_transaction_disabled = True
                    warnings.warn(
                        "Could not generate x-client-transaction-id; continuing without it.",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                finally:
                    self.set_cookies(cookies_backup, clear_cookies=True)

            if (
                not self._client_transaction_disabled
                and getattr(transaction, "key", None) is not None
            ):
                try:
                    headers["X-Client-Transaction-Id"] = transaction.generate_transaction_id(
                        method=method,
                        path=urlparse(url).path,
                    )
                except Exception:  # noqa: BLE001 - transaction assets can fail in many ways
                    self._client_transaction_disabled = True
                    warnings.warn(
                        "Could not generate x-client-transaction-id; continuing without it.",
                        RuntimeWarning,
                        stacklevel=2,
                    )

            response = await self.http.request(method, url, headers=headers, **kwargs)
            self._remove_duplicate_ct0_cookie()
            try:
                response_data = response.json()
            except ValueError:
                response_data = response.text

            if (
                isinstance(response_data, dict)
                and response_data.get("errors")
                and response.status_code < 400
            ):
                raise TwitterException("X returned an upstream error.")

            if response.status_code >= 400 and raise_exception:
                safe_message = f"X request failed with status {response.status_code}."
                safe_headers = _safe_rate_limit_headers(response.headers)
                error_type = {
                    400: BadRequest,
                    401: Unauthorized,
                    403: Forbidden,
                    404: NotFound,
                    408: RequestTimeout,
                    429: TooManyRequests,
                }.get(response.status_code)
                if error_type is None:
                    error_type = ServerError if response.status_code >= 500 else TwitterException
                raise error_type(safe_message, headers=safe_headers)
            return response_data, response

    return ResilientClient(
        language=settings.twikit_language,
        proxy=settings.twikit_proxy or None,
    )


class XClient:
    """Small read-only adapter around twikit's async client."""

    def __init__(
        self,
        settings: Settings,
        *,
        client_factory: Callable[[Settings], Any] | None = None,
    ) -> None:
        self.settings = settings
        self._client_factory = client_factory or _build_client
        self._client: Any | None = None
        self._lock = asyncio.Lock()

    async def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        async with self._lock:
            if self._client is not None:
                return self._client
            cookies = require_cookie_credentials(self.settings)
            client = self._client_factory(self.settings)
            if inspect.isawaitable(client):
                client = await client
            client.set_cookies(cookies, clear_cookies=True)
            self._client = client
            return client

    async def get_user_by_screen_name(self, username: str) -> Any:
        client = await self._get_client()
        payload, _ = await client.gql.user_by_screen_name(username.lstrip("@"))
        user_data = ((payload.get("data") or {}).get("user") or {}).get("result")
        if not isinstance(user_data, dict) or user_data.get("__typename") == "UserUnavailable":
            raise XNotFoundError("The requested X user was not found.")
        _normalize_user_result(user_data)
        _prepare_twikit_import()
        from twikit.user import User

        return User(client, user_data)

    async def get_user_tweets(
        self,
        user_id: str,
        *,
        limit: int,
        cursor: str | None,
        include_replies: bool,
    ) -> XPage:
        client = await self._get_client()
        method = client.gql.user_tweets_and_replies if include_replies else client.gql.user_tweets
        payload, _ = await method(user_id, limit, cursor)
        entries = _timeline_entries_from_payload(payload)
        next_cursor, cursor_candidates = _page_cursor_diagnostics(payload)
        return XPage(
            items=_unique_tweets(client, entries, include_replies=include_replies),
            next_cursor=next_cursor,
            raw_entries_count=len(entries),
            raw_tweet_count=_raw_tweet_count(entries),
            cursor_candidates=cursor_candidates,
            instruction_types=_timeline_instruction_types(payload),
            terminal_reason=_timeline_terminal_reason(payload),
        )

    async def search_tweets(
        self,
        query: str,
        *,
        product: str,
        limit: int,
        cursor: str | None,
    ) -> XPage:
        client = await self._get_client()
        _prepare_twikit_import()
        from twikit.client.gql import Endpoint
        from twikit.constants import FEATURES

        variables = {
            "rawQuery": query,
            "count": limit,
            "querySource": "typed_query",
            "product": product,
        }
        if cursor is not None:
            variables["cursor"] = cursor
        payload, _ = await client.gql.gql_post(Endpoint.SEARCH_TIMELINE, variables, FEATURES)
        entries = _timeline_entries_from_payload(payload)
        next_cursor, cursor_candidates = _page_cursor_diagnostics(payload)
        return XPage(
            items=_unique_tweets(client, entries),
            next_cursor=next_cursor,
            raw_entries_count=len(entries),
            raw_tweet_count=_raw_tweet_count(entries),
            cursor_candidates=cursor_candidates,
            instruction_types=_timeline_instruction_types(payload),
            terminal_reason=_timeline_terminal_reason(payload),
        )

    async def get_tweet_by_id(self, tweet_id: str) -> Any:
        client = await self._get_client()
        _prepare_twikit_import()
        from twikit.tweet import tweet_from_data

        payload, _ = await client.gql.tweet_detail(tweet_id, None)
        _normalize_user_payload(payload)
        entries = _entries_from_payload(payload)
        for entry in entries:
            if str(entry.get("entryId", "")) == f"tweet-{tweet_id}":
                try:
                    tweet = tweet_from_data(client, entry)
                except (KeyError, TypeError, ValueError):
                    continue
                if tweet is not None:
                    return tweet
        for entry in entries:
            try:
                tweet = tweet_from_data(client, entry)
            except (KeyError, TypeError, ValueError):
                continue
            if tweet is not None and str(getattr(tweet, "id", "")) == tweet_id:
                return tweet
        raise XNotFoundError("The requested X post was not found.")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.http.aclose()
