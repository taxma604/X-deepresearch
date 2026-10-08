from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from app.models.tweet import MediaItem, ResearchTweet, Tweet
from app.models.user import UserProfile


def _get(obj: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(obj, name, default)
    except Exception:  # noqa: BLE001 - optional upstream properties may raise
        return default


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def user_to_model(user: Any) -> UserProfile | None:
    if user is None:
        return None
    username = _get(user, "screen_name") or _get(user, "username")
    return UserProfile(
        id=_as_string(_get(user, "id")),
        username=_as_string(username),
        display_name=_as_string(_get(user, "name")),
        description=_as_string(_get(user, "description")),
        followers=_as_int(_get(user, "followers_count")),
        following=_as_int(_get(user, "following_count")),
        verified=_get(user, "verified"),
        is_blue_verified=_get(user, "is_blue_verified"),
        profile_url=(f"https://x.com/{username}" if username else None),
    )


def _media_to_model(media: Any) -> MediaItem:
    return MediaItem(
        id=_as_string(_get(media, "id")),
        type=_as_string(_get(media, "type")),
        url=_as_string(_get(media, "url") or _get(media, "media_url")),
        display_url=_as_string(_get(media, "display_url")),
    )


def tweet_to_model(
    tweet: Any,
    *,
    include_quoted: bool = True,
    _seen: set[str] | None = None,
) -> Tweet | None:
    if tweet is None:
        return None
    seen = _seen if _seen is not None else set()
    object_marker = f"object:{id(tweet)}"
    if object_marker in seen:
        return None
    tweet_id = _as_string(_get(tweet, "id"))
    if tweet_id and tweet_id in seen:
        return None
    seen.add(object_marker)
    if tweet_id:
        seen.add(tweet_id)

    user = user_to_model(_get(tweet, "user"))
    username = user.username if user else None
    direct_url = _get(tweet, "url")
    tweet_url = _as_string(direct_url)
    if not tweet_url and username and tweet_id:
        tweet_url = f"https://x.com/{username}/status/{tweet_id}"

    media = _get(tweet, "media") or []
    quoted = _get(tweet, "quote") or _get(tweet, "quoted_tweet")
    quoted_model = (
        tweet_to_model(quoted, include_quoted=True, _seen=seen)
        if include_quoted and quoted is not None
        else None
    )

    return Tweet(
        id=tweet_id,
        text=_as_string(_get(tweet, "full_text") or _get(tweet, "text")),
        created_at=_as_string(_get(tweet, "created_at")),
        lang=_as_string(_get(tweet, "lang")),
        user=user,
        reply_count=_as_int(_get(tweet, "reply_count")),
        retweet_count=_as_int(_get(tweet, "retweet_count")),
        like_count=_as_int(_get(tweet, "favorite_count")),
        quote_count=_as_int(_get(tweet, "quote_count")),
        view_count=_as_int(_get(tweet, "view_count")),
        bookmark_count=_as_int(_get(tweet, "bookmark_count")),
        is_reply=bool(
            _get(tweet, "in_reply_to_status_id")
            or _get(tweet, "in_reply_to_status_id_str")
        ),
        is_quote=bool(_get(tweet, "is_quote_status") or quoted is not None),
        is_repost=bool(
            _get(tweet, "retweeted_tweet")
            or _get(tweet, "retweeted_status_result")
            or _get(tweet, "retweeted_status")
        ),
        url=tweet_url,
        media=[_media_to_model(item) for item in media if item is not None],
        quoted_tweet=quoted_model,
    )


def research_tweet_to_model(tweet: Any) -> ResearchTweet | None:
    """Serialize a Twikit tweet into the stable read-only research shape."""

    if tweet is None:
        return None
    tweet_id = _as_string(_get(tweet, "id"))
    user = _get(tweet, "user")
    screen_name = _as_string(_get(user, "screen_name") or _get(user, "username"))
    tweet_url = _as_string(_get(tweet, "url"))
    if not tweet_url and screen_name and tweet_id:
        tweet_url = f"https://x.com/{screen_name}/status/{tweet_id}"

    quoted = _get(tweet, "quote") or _get(tweet, "quoted_tweet")
    return ResearchTweet(
        id=tweet_id,
        url=tweet_url,
        created_at=_as_string(_get(tweet, "created_at")),
        text=_as_string(_get(tweet, "full_text") or _get(tweet, "text")),
        lang=_as_string(_get(tweet, "lang")),
        author={
            "id": _as_string(_get(user, "id")),
            "name": _as_string(_get(user, "name")),
            "screen_name": screen_name,
        },
        metrics={
            "likes": _as_int(_get(tweet, "favorite_count") or _get(tweet, "like_count")) or 0,
            "reposts": _as_int(_get(tweet, "retweet_count")) or 0,
            "replies": _as_int(_get(tweet, "reply_count")) or 0,
            "quotes": _as_int(_get(tweet, "quote_count")) or 0,
            "views": _as_int(_get(tweet, "view_count")) or 0,
            "bookmarks": _as_int(_get(tweet, "bookmark_count")) or 0,
        },
        is_reply=bool(
            _get(tweet, "in_reply_to_status_id")
            or _get(tweet, "in_reply_to_status_id_str")
        ),
        is_quote=bool(_get(tweet, "is_quote_status") or quoted is not None),
        is_repost=bool(
            _get(tweet, "retweeted_tweet")
            or _get(tweet, "retweeted_status_result")
            or _get(tweet, "retweeted_status")
        ),
    )


def page_to_data(
    items: Iterable[Any],
    next_cursor: str | None,
    serializer,
    *,
    pagination_issue: str | None = None,
) -> dict[str, Any]:
    serialized = [item for raw in items if (item := serializer(raw)) is not None]
    return {
        "items": serialized,
        "next_cursor": next_cursor,
        "has_more": bool(next_cursor),
        "pagination_complete": not bool(next_cursor) and pagination_issue is None,
        "pagination_issue": pagination_issue,
    }
