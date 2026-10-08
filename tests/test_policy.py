from app.config import Settings
from app.x.policy import search_query_is_allowed


def test_search_policy_accepts_only_configured_from_users_by_default() -> None:
    settings = Settings(
        _env_file=None,
        ALLOWED_USERS="alice,bob_2",
        ALLOW_ARBITRARY_SEARCH=False,
    )
    assert search_query_is_allowed("from:alice since:2025-01-01", settings)
    assert search_query_is_allowed("from:bob_2", settings)
    assert not search_query_is_allowed("from:someone_else", settings)
    assert not search_query_is_allowed("x research", settings)


def test_search_policy_can_be_explicitly_opened() -> None:
    settings = Settings(_env_file=None, ALLOW_ARBITRARY_SEARCH=True)
    assert search_query_is_allowed("x research", settings)


def test_rejects_multiple_authors_if_one_is_not_allowed() -> None:
    settings = Settings(_env_file=None, ALLOWED_USERS="alice", ALLOW_ARBITRARY_SEARCH=False)
    assert not search_query_is_allowed("from:alice from:bob", settings)


def test_search_rejects_boolean_bypass_and_negated_authors():
    settings = Settings(_env_file=None, ALLOWED_USERS="alice")
    for query in (
        "from:alice OR python",
        "python OR from:alice",
        "from:alice | python",
        "(from:alice) OR bitcoin",
        "-from:alice AI",
        "from:alice from:alice",
    ):
        assert not search_query_is_allowed(query, settings)
    assert search_query_is_allowed("from:alice since:2026-09-01 lang:ja", settings)
