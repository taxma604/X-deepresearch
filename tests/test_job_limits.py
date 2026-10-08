import asyncio
from types import SimpleNamespace

import pytest

from app.services.daily_stats_jobs import DailyStatsJobManager
from app.x.exceptions import XRateLimitError


async def test_queue_limit_rejects_distinct_jobs_and_deduplicates():
    gate = asyncio.Event()

    class Service:
        settings = SimpleNamespace(retry_base_seconds=1, retry_max_seconds=30, max_results=2000)

        async def search_daily_stats(self, **kwargs):
            await gate.wait()
            return {"total_posts": 0}

    manager = DailyStatsJobManager()
    service = Service()
    def start(q):
        return manager.start(service, query=q, product="Latest",
                             start_date="2026-09-01", end_date="2026-09-02", limit=20)
    try:
        first = start("AI")
        assert start("AI")["job_id"] == first["job_id"]
        start("MCP")
        start("Claude")
        with pytest.raises(XRateLimitError):
            start("Codex")
    finally:
        gate.set()
        await asyncio.gather(*list(manager._tasks.values()))


async def test_validate_dates_and_query_before_queuing():
    manager = DailyStatsJobManager()
    service = SimpleNamespace(settings=SimpleNamespace(max_results=2000))
    params = {"query": "x", "product": "Latest", "start_date": "2026-09-01",
              "end_date": "2026-09-02", "limit": 20}
    for patch in ({"query": ""}, {"query": "x" * 513}, {"limit": 2001},
                  {"start_date": "2026-09-99"}, {"end_date": "2027-09-01"}):
        with pytest.raises(ValueError):
            manager.start(service, **(params | patch))
    assert manager._tasks == {}
