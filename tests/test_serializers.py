from types import SimpleNamespace
from typing import ClassVar

from app.x.serializers import research_tweet_to_model, tweet_to_model, user_to_model


class PartialTweet:
    id = "123"
    text = "hello"
    created_at = "2026-09-13T00:00:00Z"
    user = SimpleNamespace(
        id="7",
        screen_name="alice",
        name="Alice",
        description="Researcher",
        followers_count=10,
        following_count=20,
        verified=False,
        is_blue_verified=True,
    )
    reply_count = 1
    retweet_count = 2
    favorite_count = 3
    quote_count = 4
    view_count = 5
    media: ClassVar[list[object]] = []
    quote = None

    @property
    def bookmark_count(self):
        raise KeyError("field omitted by X")


def test_user_serializer_maps_stable_field_names() -> None:
    user = user_to_model(PartialTweet.user)
    assert user is not None
    assert user.username == "alice"
    assert user.followers == 10
    assert user.profile_url == "https://x.com/alice"


def test_tweet_serializer_tolerates_missing_optional_fields() -> None:
    tweet = tweet_to_model(PartialTweet())
    assert tweet is not None
    assert tweet.id == "123"
    assert tweet.like_count == 3
    assert tweet.bookmark_count is None
    assert tweet.url == "https://x.com/alice/status/123"


def test_tweet_serializer_stops_cyclic_quote_references() -> None:
    tweet = PartialTweet()
    tweet.quote = tweet

    serialized = tweet_to_model(tweet)

    assert serialized is not None
    assert serialized.quoted_tweet is None


def test_research_tweet_serializer_emits_stable_read_shape() -> None:
    serialized = research_tweet_to_model(PartialTweet())

    assert serialized is not None
    assert serialized.model_dump() == {
        "id": "123",
        "url": "https://x.com/alice/status/123",
        "created_at": "2026-09-13T00:00:00Z",
        "text": "hello",
        "lang": None,
        "author": {"id": "7", "name": "Alice", "screen_name": "alice"},
        "metrics": {
            "likes": 3,
            "reposts": 2,
            "replies": 1,
            "quotes": 4,
            "views": 5,
            "bookmarks": 0,
        },
        "is_reply": False,
        "is_quote": False,
        "is_repost": False,
    }
