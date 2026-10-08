import asyncio
from types import SimpleNamespace

from app.config import Settings
from app.x.client import XClient, _safe_rate_limit_headers


def test_safe_rate_limit_headers_preserve_reset_without_other_response_headers() -> None:
    headers = {
        "Retry-After": "30",
        "X-Rate-Limit-Reset": "1790000000",
        "Set-Cookie": "auth_token=must-not-leak",
        "Authorization": "secret",
    }

    assert _safe_rate_limit_headers(headers) == {
        "retry-after": "30",
        "x-rate-limit-reset": "1790000000",
    }


class FakeGraphQL:
    def __init__(self) -> None:
        self.user_tweets_and_replies_calls: list[tuple[str, int, str | None]] = []
        self.search_calls: list[dict] = []

    async def user_tweets_and_replies(
        self, user_id: str, count: int, cursor: str | None
    ) -> tuple[dict, object]:
        self.user_tweets_and_replies_calls.append((user_id, count, cursor))
        return {
            "data": {
                "timeline": {
                    "instructions": [
                        {"entries": [{"entryId": "cursor-bottom-0", "content": {"value": "NEXT"}}]}
                    ]
                }
            }
        }, SimpleNamespace()

    async def gql_post(self, url: str, variables: dict, features: dict) -> tuple[dict, object]:
        self.search_calls.append({"url": url, "variables": variables, "features": features})
        return {
            "data": {
                "timeline": {
                    "instructions": [
                        {"entries": [{"entryId": "cursor-bottom-0", "content": {"value": "NEXT"}}]}
                    ]
                }
            }
        }, SimpleNamespace()

    async def user_by_screen_name(self, screen_name: str) -> tuple[dict, object]:
        return {
            "data": {
                "user": {
                    "result": {
                        "rest_id": "7",
                        "is_blue_verified": False,
                        "legacy": {
                            "created_at": "Mon Jan 01 00:00:00 +0000 2024",
                            "name": "Alice",
                            "screen_name": screen_name,
                            "profile_image_url_https": "https://example.test/avatar.jpg",
                            "location": "",
                            "description": "",
                            "entities": {"description": {}},
                            "pinned_tweet_ids_str": [],
                            "verified": False,
                            "followers_count": 1,
                            "friends_count": 2,
                            "favourites_count": 3,
                            "listed_count": 0,
                            "media_count": 0,
                            "statuses_count": 4,
                        },
                    }
                }
            }
        }, SimpleNamespace()


class FakeClient:
    def __init__(self) -> None:
        self.cookies: dict[str, str] = {}
        self.gql = FakeGraphQL()

    def set_cookies(self, cookies: dict[str, str], clear_cookies: bool = False) -> None:
        if clear_cookies:
            self.cookies.clear()
        self.cookies.update(cookies)


def test_client_injects_cookies_and_forwards_read_cursors() -> None:
    asyncio.run(_exercise_client())


async def _exercise_client() -> None:
    settings = Settings(TWIKIT_AUTH_TOKEN="AUTH", TWIKIT_CT0="CT0")
    clients: list[FakeClient] = []

    def factory(_: Settings) -> FakeClient:
        client = FakeClient()
        clients.append(client)
        return client

    adapter = XClient(settings, client_factory=factory)
    client = await adapter._get_client()
    user = await adapter.get_user_by_screen_name("alice")
    user_page = await adapter.get_user_tweets(
        "7", limit=40, cursor="USER_CURSOR", include_replies=True
    )
    search_page = await adapter.search_tweets(
        "from:alice", product="Top", limit=20, cursor="SEARCH_CURSOR"
    )

    assert clients == [client]
    assert client.cookies == {"auth_token": "AUTH", "ct0": "CT0"}
    assert user.id == "7"
    assert user.withheld_in_countries == []
    assert client.gql.user_tweets_and_replies_calls == [("7", 40, "USER_CURSOR")]
    assert len(client.gql.search_calls) == 1
    assert client.gql.search_calls[0]["url"].endswith("/SearchTimeline")
    assert client.gql.search_calls[0]["variables"] == {
        "rawQuery": "from:alice",
        "count": 20,
        "querySource": "typed_query",
        "product": "Top",
        "cursor": "SEARCH_CURSOR",
    }
    assert user_page.next_cursor == "NEXT"
    assert search_page.next_cursor == "NEXT"


def test_search_client_reads_cursor_from_replacement_instructions() -> None:
    asyncio.run(_exercise_replacement_cursor())


async def _exercise_replacement_cursor() -> None:
    class ReplacementCursorGraphQL:
        async def gql_post(self, url: str, variables: dict, features: dict):
            assert variables["cursor"] == "PREVIOUS"
            return {
                "data": {
                    "search_by_raw_query": {
                        "search_timeline": {
                            "timeline": {
                                "instructions": [
                                    {"type": "TimelineAddEntries", "entries": []},
                                    {
                                        "type": "TimelineReplaceEntry",
                                        "entry_id_to_replace": "cursor-top-0",
                                        "entry": {
                                            "entryId": "cursor-top-0",
                                            "content": {
                                                "entryType": "TimelineTimelineCursor",
                                                "cursorType": "Top",
                                                "value": "TOP",
                                            },
                                        },
                                    },
                                    {
                                        "type": "TimelineReplaceEntry",
                                        "entry_id_to_replace": "cursor-bottom-0",
                                        "entry": {
                                            "entryId": "cursor-bottom-0",
                                            "content": {
                                                "entryType": "TimelineTimelineCursor",
                                                "cursorType": "Bottom",
                                                "value": "NEXT-PAGE",
                                            },
                                        },
                                    },
                                ]
                            }
                        }
                    }
                }
            }, SimpleNamespace()

    client = FakeClient()
    client.gql = ReplacementCursorGraphQL()
    adapter = XClient(
        Settings(TWIKIT_AUTH_TOKEN="AUTH", TWIKIT_CT0="CT0"),
        client_factory=lambda _: client,
    )

    result = await adapter.search_tweets(
        "AI",
        product="Latest",
        limit=20,
        cursor="PREVIOUS",
    )

    assert result.items == []
    assert result.next_cursor == "NEXT-PAGE"
    assert result.cursor_candidates == (
        ("top", "07b4ed8e4e4e"),
        ("bottom", "7104a1ff7f50"),
    )
    assert "NEXT-PAGE" not in repr(result)


def test_search_client_preserves_terminal_instruction_alongside_cursor() -> None:
    asyncio.run(_exercise_terminal_instruction())


async def _exercise_terminal_instruction() -> None:
    class TerminalGraphQL:
        async def gql_post(self, url: str, variables: dict, features: dict):
            return {
                "data": {
                    "timeline": {
                        "instructions": [
                            {
                                "type": "TimelineAddEntries",
                                "entries": [
                                    {
                                        "entryId": "cursor-bottom-0",
                                        "content": {
                                            "entryType": "TimelineTimelineCursor",
                                            "cursorType": "Bottom",
                                            "value": "OPAQUE-NEXT",
                                        },
                                    }
                                ],
                            },
                            {"type": "TimelineTerminateTimeline"},
                        ]
                    }
                }
            }, SimpleNamespace()

    client = FakeClient()
    client.gql = TerminalGraphQL()
    adapter = XClient(
        Settings(TWIKIT_AUTH_TOKEN="AUTH", TWIKIT_CT0="CT0"),
        client_factory=lambda _: client,
    )
    page = await adapter.search_tweets(
        "AI",
        product="Latest",
        limit=20,
        cursor=None,
    )

    assert page.next_cursor == "OPAQUE-NEXT"
    assert page.terminal_reason == "terminate_instruction"
    assert "TimelineTerminateTimeline" in page.instruction_types
    assert "OPAQUE-NEXT" not in repr(page)


def test_search_client_treats_cursor_only_replacement_as_terminal() -> None:
    asyncio.run(_exercise_cursor_only_replacement())


async def _exercise_cursor_only_replacement() -> None:
    class CursorOnlyGraphQL:
        async def gql_post(self, url: str, variables: dict, features: dict):
            return {
                "data": {
                    "timeline": {
                        "instructions": [
                            {
                                "type": "TimelineReplaceEntry",
                                "entry_id_to_replace": "cursor-top-0",
                                "entry": {
                                    "entryId": "cursor-top-0",
                                    "content": {
                                        "entryType": "TimelineTimelineCursor",
                                        "cursorType": "Top",
                                        "value": "OPAQUE-TOP",
                                    },
                                },
                            },
                            {
                                "type": "TimelineReplaceEntry",
                                "entry_id_to_replace": "cursor-bottom-0",
                                "entry": {
                                    "entryId": "cursor-bottom-0",
                                    "content": {
                                        "entryType": "TimelineTimelineCursor",
                                        "cursorType": "Bottom",
                                        "value": "OPAQUE-BOTTOM",
                                    },
                                },
                            },
                        ]
                    }
                }
            }, SimpleNamespace()

    client = FakeClient()
    client.gql = CursorOnlyGraphQL()
    adapter = XClient(
        Settings(TWIKIT_AUTH_TOKEN="AUTH", TWIKIT_CT0="CT0"),
        client_factory=lambda _: client,
    )
    page = await adapter.search_tweets("AI", product="Latest", limit=20, cursor="PREVIOUS")

    assert page.items == []
    assert page.raw_entries_count == 2
    assert page.raw_tweet_count == 0
    assert page.terminal_reason == "cursor_only_replacement"
    assert page.next_cursor == "OPAQUE-BOTTOM"
