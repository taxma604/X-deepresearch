"""SQLite durability and window-level checkpoint behavior."""
import asyncio
from types import SimpleNamespace

from app.config import Settings
from app.services.daily_stats_jobs import DailyStatsJobManager
from app.services.x_service import XService


async def test_job_survives_restart_and_completes(tmp_path):
    path = str(tmp_path / "jobs.sqlite3")
    gate = asyncio.Event()

    class FakeService:
        settings = SimpleNamespace(retry_base_seconds=1, retry_max_seconds=30, max_results=2000)

        async def search_daily_stats_complete(self, **kwargs):
            if kwargs.get("checkpoint"):
                assert kwargs["checkpoint"]["pending"] == [["2026-09-03", "2026-09-03"]]
            kwargs["checkpoint_callback"]({
                "query": kwargs["query"],
                "product": kwargs["product"],
                "start_date": kwargs["start_date"],
                "end_date": kwargs["end_date"],
                "limit": kwargs["limit"],
                "pending": [["2026-09-03", "2026-09-03"]],
                "counts": {"2026-09-01": 2, "2026-09-02": 1},
                "pages_fetched": 2,
                "scanned_posts": 3,
                "segments_fetched": 1,
                "incomplete_ranges": [],
            })
            await gate.wait()
            return {"query": "AI", "daily": [{"date": "2026-09-01", "count": 2}]}

    svc = FakeService()
    manager = DailyStatsJobManager(db_path=path)
    item = manager.start(svc, query="AI", product="Latest", start_date="2026-09-01",
                         end_date="2026-09-03", limit=20, complete_range=True)
    await asyncio.sleep(0)
    assert manager.get(item["job_id"])["status"] == "running"
    restored = DailyStatsJobManager(db_path=path)
    assert restored.get(item["job_id"])["status"] == "queued"
    assert restored._jobs[item["job_id"]].checkpoint["counts"]["2026-09-01"] == 2
    # Stop the old task (a process restart would do the same).
    manager._tasks[item["job_id"]].cancel()
    await asyncio.gather(*manager._tasks.values(), return_exceptions=True)
    await restored.resume_pending(svc)
    await asyncio.sleep(0)
    gate.set()
    await asyncio.gather(*restored._tasks.values())
    assert restored.get(item["job_id"])["status"] == "completed"
    assert DailyStatsJobManager(db_path=path).get(item["job_id"])["status"] == "completed"


async def test_window_checkpoint_resume_skips_completed_upstream_calls():
    class FakeSearchClient:
        def __init__(self):
            self.calls = []

        async def search_tweets(self, query, **kwargs):
            self.calls.append(query)
            # This returns an empty terminal page, so each two-day window is final.
            from app.x.client import XPage
            return XPage(items=[], next_cursor=None)

    settings = Settings(
        _env_file=None, ALLOW_ARBITRARY_SEARCH=True,
        X_MIN_REQUEST_INTERVAL_SECONDS=0, X_RATE_LIMIT_PER_MINUTE=600,
    )
    client = FakeSearchClient()
    svc = XService(client, settings)
    checkpoints = []
    data = await svc.search_daily_stats_complete(
        query="AI", product="Latest", start_date="2026-07-01",
        end_date="2026-09-28", limit=20, checkpoint_callback=checkpoints.append,
    )
    assert data["coverage_complete"] is True
    assert len(data["daily"]) == 90
    assert len(checkpoints) == 45
    assert len(client.calls) == 45
    other = FakeSearchClient()
    resumed = await XService(other, settings).search_daily_stats_complete(
        query="AI", product="Latest", start_date="2026-07-01",
        end_date="2026-09-28", limit=20, checkpoint=checkpoints[0],
    )
    assert resumed["daily"] == data["daily"]
    assert len(other.calls) == 44
