"""Simulation jobs: a run in a background thread, polled for progress, kept a while for route details.

The engine answers a run in one piece; a job lets the page show how many trajectories are done (the engine runs in
batches) and later ask for the detail of any route without sending every route's trajectories up front.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..engines.run import run, total_trajectories

KEPT = 3     # finished jobs kept for route details; each holds about 36 MB of path codes per 100,000 trajectories


@dataclass
class Job:
    id: str
    profile: str
    total: int
    done: int = 0
    status: str = "running"            # running, done, failed
    result: dict | None = None
    error: str | None = None
    raw: list = field(default_factory=list)

    def view(self) -> dict[str, Any]:
        return {"id": self.id, "status": self.status, "done": self.done, "total": self.total,
                "result": self.result, "error": self.error}


class Jobs:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def start(self, request: dict, default_state: str, device: str, tracks: int) -> Job:
        job = Job(uuid.uuid4().hex, request["profile"], total_trajectories(request))
        with self._lock:
            self._jobs[job.id] = job
            self._forget_old()
        threading.Thread(target=self._work, args=(job, request, default_state, device, tracks), daemon=True).start()
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def _work(self, job: Job, request: dict, default_state: str, device: str, tracks: int) -> None:
        def progress(done: int) -> None:
            job.done = done
        try:
            job.result = run(request, default_state, device, tracks, progress=progress, raw=job.raw)
            job.status = "done"
        except Exception as error:      # reported to the page, which shows it instead of a result
            job.error, job.status, job.raw = str(error), "failed", []

    def _forget_old(self) -> None:
        finished = [job_id for job_id, job in self._jobs.items() if job.status != "running"]
        for job_id in finished[: max(0, len(finished) - KEPT)]:
            del self._jobs[job_id]
