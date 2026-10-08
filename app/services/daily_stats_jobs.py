from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from app.services.job_store import SQLiteJobStore
from app.services.rate_limiter import RetryPolicy
from app.x.exceptions import XApiError, XRateLimitError

if TYPE_CHECKING:
    from app.services.x_service import XService

JobStatus = Literal["queued", "running", "waiting_for_rate_limit", "completed", "failed"]
JOB_TTL_SECONDS = 3600
MAX_ACTIVE_JOBS = 3
MAX_STORED_JOBS = 32
MAX_JOB_RANGE_DAYS = 90


@dataclass
class _DailyStatsJob:
    job_id: str
    request_key: str
    status: JobStatus = "queued"
    pages_fetched: int = 0
    fetched_posts: int = 0
    retry_after_seconds: float | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    updated_at: float = field(default_factory=time.monotonic)
    params: dict[str, Any] = field(default_factory=dict)
    checkpoint: dict[str, Any] | None = None


class DailyStatsJobManager:
    """Keep long daily-stat searches running across separate MCP tool calls."""

    def __init__(self, *, ttl_seconds: int = JOB_TTL_SECONDS, db_path: str | None = None) -> None:
        self.ttl_seconds = ttl_seconds
        self._store = SQLiteJobStore(db_path) if db_path else None
        self._jobs: dict[str, _DailyStatsJob] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._active_by_key: dict[str, str] = {}
        self._run_lock = asyncio.Lock()
        if self._store is not None:
            for item in self._store.load_all():
                status = item["status"]
                if status in {"running", "waiting_for_rate_limit"}:
                    status = "queued"
                job = _DailyStatsJob(
                    job_id=item["job_id"],
                    request_key=item["request_key"],
                    status=status,
                    params=item.get("params") or {},
                    checkpoint=item.get("checkpoint"),
                    pages_fetched=item.get("pages_fetched", 0),
                    fetched_posts=item.get("fetched_posts", 0),
                    result=item.get("result"),
                    error=item.get("error"),
                )
                self._jobs[job.job_id] = job
                if status == "queued":
                    self._active_by_key[job.request_key] = job.job_id

    def _persist(self, job: _DailyStatsJob) -> None:
        if self._store is not None:
            self._store.save({
                "job_id": job.job_id,
                "request_key": job.request_key,
                "status": job.status,
                "params": job.params,
                "checkpoint": job.checkpoint,
                "pages_fetched": job.pages_fetched,
                "fetched_posts": job.fetched_posts,
                "result": job.result,
                "error": job.error,
            })

    async def resume_pending(self, service: XService) -> None:
        """Resume unfinished jobs from SQLite when an MCP process starts."""
        for job in list(self._jobs.values()):
            if job.status == "queued" and job.job_id not in self._tasks and job.params:
                task = asyncio.create_task(self._run(job, service, dict(job.params)))
                self._tasks[job.job_id] = task
                task.add_done_callback(
                    lambda _, job_id=job.job_id: self._tasks.pop(job_id, None)
                )


    def start(
        self,
        service: XService,
        *,
        query: str,
        product: str,
        start_date: str,
        end_date: str,
        limit: int,
        complete_range: bool = False,
    ) -> dict[str, Any]:
        if not query.strip() or len(query) > 512:
            raise ValueError("query must be 1-512 non-whitespace characters.")
        if limit < 1 or limit > getattr(service.settings, "max_results", 2000):
            raise ValueError("limit exceeds the configured per-batch result cap.")
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError as exc:
            raise ValueError("start_date and end_date must be ISO dates.") from exc
        if start > end or (end - start).days + 1 > MAX_JOB_RANGE_DAYS:
            raise ValueError("date range must be 1-90 days.")

        self._prune()
        params = {
            "query": query,
            "product": product,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "complete_range": complete_range,
        }
        request_key = hashlib.sha256(
            json.dumps(params, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        active_job_id = self._active_by_key.get(request_key)
        active_job = self._jobs.get(active_job_id or "")
        if active_job is not None and active_job.status in {
            "queued",
            "running",
            "waiting_for_rate_limit",
        }:
            return self._to_dict(active_job)

        active = sum(
            job.status in {"queued", "running", "waiting_for_rate_limit"}
            for job in self._jobs.values()
        )
        if active >= MAX_ACTIVE_JOBS or len(self._jobs) >= MAX_STORED_JOBS:
            raise XRateLimitError("Research job queue is full; retry later.")

        job = _DailyStatsJob(job_id=uuid4().hex, request_key=request_key, params=dict(params))
        self._jobs[job.job_id] = job
        self._active_by_key[request_key] = job.job_id
        self._persist(job)
        task = asyncio.create_task(self._run(job, service, params))
        self._tasks[job.job_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(job.job_id, None))
        return self._to_dict(job)

    def get(self, job_id: str) -> dict[str, Any] | None:
        self._prune()
        job = self._jobs.get(job_id)
        return self._to_dict(job) if job is not None else None

    async def _run(
        self,
        job: _DailyStatsJob,
        service: XService,
        params: dict[str, Any],
    ) -> None:
        async with self._run_lock:
            await self._run_serialized(job, service, params)

    async def _run_serialized(
        self,
        job: _DailyStatsJob,
        service: XService,
        params: dict[str, Any],
    ) -> None:
        job.status = "running"
        job.updated_at = time.monotonic()
        self._persist(job)

        def update_progress(pages_fetched: int, fetched_posts: int, _has_more: bool) -> None:
            job.status = "running"
            job.retry_after_seconds = None
            job.pages_fetched = pages_fetched
            job.fetched_posts = fetched_posts
            job.updated_at = time.monotonic()

        def update_retry_wait(delay: float) -> None:
            job.status = "waiting_for_rate_limit"
            job.retry_after_seconds = delay
            job.updated_at = time.monotonic()

        retry_policy = RetryPolicy(
            max_retries=5,
            base_seconds=max(service.settings.retry_base_seconds, 30.0),
            max_seconds=max(service.settings.retry_max_seconds, 3600.0),
            on_wait=update_retry_wait,
        )

        try:
            params = dict(params)
            complete_range = params.pop("complete_range", False)
            search_method = (
                service.search_daily_stats_complete
                if complete_range
                else service.search_daily_stats
            )
            extra: dict[str, Any] = {}
            if complete_range and self._store is not None:
                def save_checkpoint(state: dict[str, Any]) -> None:
                    job.checkpoint = state
                    self._persist(job)

                extra = {
                    "checkpoint": job.checkpoint,
                    "checkpoint_callback": save_checkpoint,
                }
            job.result = await search_method(
                **params,
                progress_callback=update_progress,
                retry_policy=retry_policy,
                **extra,
            )
            job.status = "completed"
            job.retry_after_seconds = None
        except XApiError as error:
            job.retry_after_seconds = error.retry_after
            job.error = {
                "code": error.code,
                "message": error.message,
                "retry_after_seconds": error.retry_after,
            }
            job.status = "failed"
        except ValueError as error:
            job.retry_after_seconds = None
            job.error = {"code": "invalid_request", "message": str(error)}
            job.status = "failed"
        except Exception:  # noqa: BLE001 - never expose upstream payloads or exception text
            job.retry_after_seconds = None
            job.error = {
                "code": "internal_error",
                "message": "The daily stats job failed.",
            }
            job.status = "failed"
        finally:
            job.updated_at = time.monotonic()
            self._persist(job)

    def _prune(self) -> None:
        cutoff = time.monotonic() - self.ttl_seconds
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if job.status in {"completed", "failed"} and job.updated_at < cutoff
        ]
        for job_id in expired:
            job = self._jobs.pop(job_id)
            if self._store is not None:
                self._store.delete(job_id)
            if self._active_by_key.get(job.request_key) == job_id:
                self._active_by_key.pop(job.request_key, None)

    @staticmethod
    def _to_dict(job: _DailyStatsJob) -> dict[str, Any]:
        return {
            "job_id": job.job_id,
            "status": job.status,
            "pages_fetched": job.pages_fetched,
            "fetched_posts": job.fetched_posts,
            "retry_after_seconds": job.retry_after_seconds,
            "result": job.result,
            "error": job.error,
        }
