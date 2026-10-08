from app.x.client import _cursor_from_entries, _cursor_from_payload, extract_cursor_value


def test_cursor_supports_old_content_shape() -> None:
    entry = {"content": {"itemContent": {"value": "OLD"}}}
    assert extract_cursor_value(entry) == "OLD"


def test_cursor_supports_new_content_shape() -> None:
    entry = {"content": {"value": "NEW"}}
    assert extract_cursor_value(entry) == "NEW"


def test_cursor_supports_nested_item_shape() -> None:
    entry = {"item": {"value": "NESTED"}}
    assert extract_cursor_value(entry) == "NESTED"


def test_cursor_falls_through_empty_old_shape() -> None:
    entry = {"content": {"itemContent": {}, "value": "NEW"}}
    assert extract_cursor_value(entry) == "NEW"


def test_search_page_cursor_is_read_from_timeline_replace_entry() -> None:
    payload = {
        "data": {
            "search_by_raw_query": {
                "search_timeline": {
                    "timeline": {
                        "instructions": [
                            {"type": "TimelineAddEntries", "entries": [{"entryId": "tweet-1"}]},
                            {
                                "type": "TimelineReplaceEntry",
                                "entry_id_to_replace": "cursor-top-9223372036854775807",
                                "entry": {
                                    "entryId": "cursor-top-9223372036854775807",
                                    "content": {
                                        "entryType": "TimelineTimelineCursor",
                                        "cursorType": "Top",
                                        "value": "TOP-CURSOR",
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
                                        "value": "BOTTOM-CURSOR",
                                    },
                                },
                            },
                        ]
                    }
                }
            }
        }
    }

    assert _cursor_from_payload(payload) == "BOTTOM-CURSOR"


def test_cursor_prefers_bottom_over_top_even_if_top_is_last() -> None:
    entries = [
        {"entryId": "cursor-bottom-0", "content": {"value": "BOTTOM"}},
        {"entryId": "cursor-top-0", "content": {"value": "TOP"}},
    ]

    assert _cursor_from_entries(entries) == "BOTTOM"


def test_top_cursor_alone_is_not_a_next_page_cursor() -> None:
    payload = {
        "instructions": [
            {
                "type": "TimelineReplaceEntry",
                "entry": {"entryId": "cursor-top-0", "content": {"value": "TOP"}},
            }
        ]
    }

    assert _cursor_from_payload(payload) is None


def test_show_more_cursor_is_used_when_bottom_cursor_is_absent() -> None:
    entries = [
        {"entryId": "cursor-showmore-0", "content": {"value": "SHOW-MORE"}}
    ]

    assert _cursor_from_entries(entries) == "SHOW-MORE"


def test_cursor_value_can_be_nested_under_operation() -> None:
    entry = {
        "entryId": "cursor-bottom-0",
        "content": {"operation": {"cursor": {"value": "NESTED-BOTTOM"}}},
    }

    assert extract_cursor_value(entry) == "NESTED-BOTTOM"
