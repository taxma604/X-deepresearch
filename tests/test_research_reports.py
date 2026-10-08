from app.services.research_reports import compare, report, summarize


def _make(query, counts, complete=True):
    return {
        "query": query,
        "period": {"start": "2026-09-01", "end": "2026-09-03", "timezone": "Asia/Tokyo"},
        "daily": [
            {"date": f"2026-09-{i + 1:02}", "count": count}
            for i, count in enumerate(counts)
        ],
        "coverage_complete": complete,
        "incomplete_ranges": [] if complete else [{"reason": "cursor_cycle"}],
    }


def test_summary_discloses_coverage_and_peak():
    r = summarize(_make("AI", [2, 7, 3], complete=False))
    assert r["total_posts"] == 12
    assert r["peak_day"] == {"date": "2026-09-02", "count": 7}
    assert r["coverage_complete"] is False
    assert len(r["incomplete_ranges"]) == 1


def test_compare_observations_and_ratios():
    r = compare(_make("A", [2, 0, 1]), _make("B", [4, 1, 1]))
    assert r["difference_b_minus_a"] == 3
    assert r["ratio_b_to_a"] == 2.0
    assert r["coverage_complete_both"] is True


def test_report_renders_consistent_markdown_and_csv():
    x = _make("AI", [2, 7, 3])
    assert "2026-09-02,7" in report(x, "csv")
    assert "Total posts observed: 12" in report(x, "markdown")
    assert '"total_posts": 12' in report(x, "json")
