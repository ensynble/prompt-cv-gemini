import time, uuid, asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Deque
from collections import deque

from .models import QAResult


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class Job:
    job_id: str
    prompt: str
    image_bytes: bytes
    mime_type: str
    created_at: float


@dataclass
class JobRecord:
    status: JobStatus
    created_at: float
    done_event: asyncio.Event

    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    model: Optional[str] = None
    result: Optional[QAResult] = None
    error: Optional[str] = None


class JobManager:
    """
    In-memory job queue + job records.

    Goals:
    - Bound queue size (max_queue)
    - Never evict active jobs (QUEUED/RUNNING)
    - Keep a bounded history of completed jobs (keep_last)
    """

    def __init__(self, max_queue: int = 100, keep_last: int = 100):
        self.queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=max_queue)
        self.records: dict[str, JobRecord] = {}
        self._order: Deque[str] = deque()
        self.keep_last = max(1, int(keep_last))

    def submit(self, *, prompt: str, image_bytes: bytes, mime_type: str) -> str:
        job_id = uuid.uuid4().hex
        now = time.monotonic()

        # Create record first
        self.records[job_id] = JobRecord(
            status=JobStatus.QUEUED,
            created_at=now,
            done_event=asyncio.Event(),
        )
        self._order.append(job_id)

        # Enqueue job; if queue is full, rollback record
        try:
            self.queue.put_nowait(Job(job_id, prompt, image_bytes, mime_type, now))
        except asyncio.QueueFull:
            self.records.pop(job_id, None)
            try:
                self._order.remove(job_id)
            except ValueError:
                pass
            raise

        # Prune only after job is safely enqueued
        self._prune()
        return job_id

    def get(self, job_id: str) -> Optional[JobRecord]:
        return self.records.get(job_id)

    def _prune(self) -> None:
        """
        Evict finished jobs until the tracked id list is <= keep_last.

        Important properties:
        - Never evict active jobs (QUEUED/RUNNING)
        - Never "lose" active jobs from _order (rotate them instead of dropping)
        - If too many jobs are active, pruning stops (cannot satisfy keep_last without evicting active)
        """
        active = (JobStatus.QUEUED, JobStatus.RUNNING)
        finished = (JobStatus.SUCCEEDED, JobStatus.FAILED)

        # Safety: avoid infinite rotate loops
        rotations = 0
        max_rotations = len(self._order) + 1

        while len(self._order) > self.keep_last:
            if not self._order:
                break

            jid = self._order[0]
            rec = self.records.get(jid)

            # Record already missing -> drop id from order
            if rec is None:
                self._order.popleft()
                rotations = 0
                continue

            # Active job: rotate it to the end and try next id
            if rec.status in active:
                self._order.rotate(-1)
                rotations += 1
                if rotations >= max_rotations:
                    # Everything we're seeing is active; can't prune further safely
                    break
                continue

            # Finished job: evict it
            if rec.status in finished:
                self._order.popleft()
                self.records.pop(jid, None)
                rotations = 0
                continue

            # Unknown/other status: treat as active (conservative)
            self._order.rotate(-1)
            rotations += 1
            if rotations >= max_rotations:
                break
