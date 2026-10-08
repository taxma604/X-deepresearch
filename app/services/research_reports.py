"""Summaries of completed research jobs; never infer unavailable X data."""
from __future__ import annotations

import csv
import io
import json
from typing import Any


def summarize(result: dict[str, Any]) -> dict[str, Any]:
    daily = result.get("daily") or []
    values = [{"date": str(row["date"]), "count": int(row["count"])} for row in daily]
    total = sum(row["count"] for row in values)
    peak = max(values, key=lambda row: row["count"]) if values else None
    return {
        "query": result.get("query"),
        "period": result.get("period"),
        "days": len(values),
        "total_posts": total,
        "average_per_day": round(total / len(values), 2) if values else 0.0,
        "peak_day": peak,
        "coverage_complete": result.get("coverage_complete", result.get("pagination_complete", False)),
        "incomplete_ranges": result.get("incomplete_ranges", []),
        "pagination_issue": result.get("pagination_issue"),
        "note": "Counts are limited to results returned by X; completeness cannot be guaranteed.",
    }


def compare(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    a_days = {row["date"]: int(row["count"]) for row in a.get("daily", [])}
    b_days = {row["date"]: int(row["count"]) for row in b.get("daily", [])}
    if set(a_days) != set(b_days):
        raise ValueError("Comparisons require identical daily date ranges.")
    total_a, total_b = sum(a_days.values()), sum(b_days.values())
    complete_a = summarize(a)["coverage_complete"]
    complete_b = summarize(b)["coverage_complete"]
    return {
        "query_a": a.get("query"),
        "query_b": b.get("query"),
        "total_a": total_a,
        "total_b": total_b,
        "difference_b_minus_a": total_b - total_a,
        "ratio_b_to_a": round(total_b / total_a, 3) if total_a else None,
        "coverage_complete_both": bool(complete_a and complete_b),
        "daily": [
            {"date": day, "count_a": a_days[day], "count_b": b_days[day]}
            for day in sorted(a_days)
        ],
        "note": "A relative comparison of observed upstream results, not global X volume.",
    }


def report(result: dict[str, Any], fmt: str) -> str:
    daily = result.get("daily") or []
    if fmt == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["date", "count"])
        for row in daily:
            writer.writerow([row["date"], int(row["count"])])
        return buffer.getvalue()
    if fmt == "json":
        return json.dumps({"summary": summarize(result), "daily": daily},
                          ensure_ascii=False, indent=2)
    if fmt != "markdown":
        raise ValueError("format must be markdown, csv, or json.")
    info = summarize(result)
    lines = [
        "# X Research Daily Report",
        "",
        "Query: " + json.dumps(info["query"], ensure_ascii=False),
        "Period: " + json.dumps(info["period"], ensure_ascii=False),
        f"Total posts observed: {info['total_posts']}",
        f"Peak day: {info['peak_day']}",
        f"Coverage complete within observed pagination: {info['coverage_complete']}",
        f"Incomplete ranges: {len(info['incomplete_ranges'])}",
        "",
        "| Date | Observed posts |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {row['date']} | {int(row['count'])} |" for row in daily)
    lines.extend(["", info["note"]])
    return "\n".join(lines)
