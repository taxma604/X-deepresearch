import asyncio
from types import SimpleNamespace

from app.services.daily_stats_jobs import DailyStatsJobManager


async def test_daily_stats_job_reports_progress_and_result() -> None:
    class StubService:
        settings = SimpleNamespace(retry_base_seconds=1, retry_max_seconds=30)

        async def search_daily_stats(self, **kwargs):
            kwargs["progress_callback"](3, 60, True)
            assert kwargs["retry_policy"].max_seconds == 3600
            assert kwargs["retry_policy"].max_retries == 5
            assert kwargs["retry_policy"].base_seconds == 30
            await asyncio.sleep(0)
            return {"total_posts": 60}

    manager = DailyStatsJobManager()
    started = manager.start(
        StubService(),
        query="AI",
        product="Latest",
        start_date="2026-09-16",
        end_date="2026-09-23",
        limit=600,
    )
    assert started["status"] == "queued"

    await asyncio.sleep(0)
    await asyncio.sleep(0)
    result = manager.get(started["job_id"])

    assert result is not None
    assert result["status"] == "completed"
    assert result["pages_fetched"] == 3
    assert result["fetched_posts"] == 60
    assert result["result"] == {"total_posts": 60}


async def test_daily_stats_job_dispatches_complete_range_mode() -> None:
    class StubService:
        settings = SimpleNamespace(retry_base_seconds=1, retry_max_seconds=30)

        async def search_daily_stats_complete(self, **kwargs):
            kwargs["progress_callback"](4, 80, False)
            return {"coverage_complete": True, "total_posts": 80}

        async def search_daily_stats(self, **kwargs):
            raise AssertionError("complete_range must select the split-window search")

    manager = DailyStatsJobManager()
    started = manager.start(
        StubService(),
        query="Qwen",
        product="Latest",
        start_date="2026-08-28",
        end_date="2026-09-26",
        limit=2000,
        complete_range=True,
    )

    await asyncio.sleep(0)
    await asyncio.sleep(0)
    result = manager.get(started["job_id"])

    assert result is not None
    assert result["status"] == "completed"
    assert result["pages_fetched"] == 4
    assert result["fetched_posts"] == 80
    assert result["result"] == {"coverage_complete": True, "total_posts": 80}


async def test_daily_stats_job_deduplicates_active_identical_requests() -> None:
    gate = asyncio.Event()

    class StubService:
        settings = SimpleNamespace(retry_base_seconds=1, retry_max_seconds=30)

        async def search_daily_stats(self, **kwargs):
            kwargs["retry_policy"].on_wait(45)
            await gate.wait()
            kwargs["progress_callback"](0, 0, False)
            return {"total_posts": 0}

    manager = DailyStatsJobManager()
    params = {
        "query": "AI",
        "product": "Latest",
        "start_date": "2026-09-16",
        "end_date": "2026-09-23",
        "limit": 600,
    }
    service = StubService()
    first = manager.start(service, **params)
    await asyncio.sleep(0)
    waiting = manager.get(first["job_id"])
    second = manager.start(service, **params)

    assert waiting is not None
    assert waiting["status"] == "waiting_for_rate_limit"
    assert waiting["retry_after_seconds"] == 45
    assert first["job_id"] == second["job_id"]
    gate.set()
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert manager.get(first["job_id"])["status"] == "completed"


async def test_daily_stats_job_hides_unexpected_exception_details() -> None:
    class StubService:
        settings = SimpleNamespace(retry_base_seconds=1, retry_max_seconds=30)

        async def search_daily_stats(self, **kwargs):
            raise RuntimeError("sensitive upstream response text")

    manager = DailyStatsJobManager()
    started = manager.start(
        StubService(),
        query="AI",
        product="Latest",
        start_date="2026-09-16",
        end_date="2026-09-23",
        limit=600,
    )
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    result = manager.get(started["job_id"])

    assert result is not None
    assert result["status"] == "failed"
    assert result["error"] == {
        "code": "internal_error",
        "message": "The daily stats job failed.",
    }


async def test_daily_stats_jobs_run_serially() -> None:
    first_job_gate = asyncio.Event()
    started_queries: list[str] = []
    active_jobs = 0
    max_active_jobs = 0

    class StubService:
        settings = SimpleNamespace(retry_base_seconds=1, retry_max_seconds=30)

        async def search_daily_stats(self, **kwargs):
            nonlocal active_jobs, max_active_jobs
            active_jobs += 1
            max_active_jobs = max(max_active_jobs, active_jobs)
            started_queries.append(kwargs["query"])
            kwargs["progress_callback"](1, 20, True)
            if kwargs["query"] == "Qwen":
                await first_job_gate.wait()
            active_jobs -= 1
            return {"total_posts": 20}

    manager = DailyStatsJobManager()
    service = StubService()
    first = manager.start(
        service,
        query="Qwen",
        product="Latest",
        start_date="2026-08-28",
        end_date="2026-09-26",
        limit=2000,
    )
    second = manager.start(
        service,
        query="DeepSeek",
        product="Latest",
        start_date="2026-08-28",
        end_date="2026-09-26",
        limit=2000,
    )
    tasks = list(manager._tasks.values())

    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert started_queries == ["Qwen"]
    assert manager.get(second["job_id"])["status"] == "queued"

    first_job_gate.set()
    await asyncio.gather(*tasks)

    assert started_queries == ["Qwen", "DeepSeek"]
    assert max_active_jobs == 1
    assert manager.get(first["job_id"])["status"] == "completed"
    assert manager.get(second["job_id"])["status"] == "completed"
