import asyncio
import inspect
import logging
import threading
from concurrent.futures import Future
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Literal, Optional, Type
from uuid import uuid4

from pydantic import BaseModel

from app.core.config import (
    PROJECTOR_TASK_MAX_PENDING,
    PROJECTOR_TASK_MAX_RECORDS,
)


logger = logging.getLogger("SKILLAB-Projector")

TaskState = Literal["queued", "running", "completed", "failed"]
TaskOperation = Callable[[], Awaitable[Any] | Any]


class TaskQueueFull(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TaskRecord:
    task_id: str
    endpoint: str
    status: TaskState
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[dict[str, str]] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "endpoint": self.endpoint,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
        }


class TaskManager:
    """Bounded in-process task registry backed by a dedicated asyncio worker loop."""

    def __init__(
            self,
            max_concurrency: int = 1,
            max_pending: int = PROJECTOR_TASK_MAX_PENDING,
            max_records: int = PROJECTOR_TASK_MAX_RECORDS,
    ):
        if int(max_concurrency) != 1:
            raise ValueError("Task concurrency must remain 1 while ProjectorEngine state is shared.")
        self.max_concurrency = 1
        self.max_pending = max(int(max_pending), 1)
        self.max_records = max(int(max_records), self.max_pending)
        self._records: dict[str, TaskRecord] = {}
        self._futures: dict[str, Future] = {}
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._thread = threading.Thread(
            target=self._run_worker_loop,
            name="projector-task-worker",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=5):
            raise RuntimeError("Projector task worker did not start.")

    def _run_worker_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        self._ready.set()
        loop.run_forever()

    def submit(
            self,
            endpoint: str,
            operation: TaskOperation,
            result_model: Optional[Type[BaseModel]] = None,
            exclude_none: bool = False,
    ) -> TaskRecord:
        task_id = str(uuid4())
        record = TaskRecord(
            task_id=task_id,
            endpoint=endpoint,
            status="queued",
            created_at=_now(),
        )
        with self._lock:
            self._discard_done_futures_locked()
            if len(self._futures) >= self.max_pending:
                raise TaskQueueFull("The Projector task queue is full.")
            self._prune_terminal_records_locked()
            self._records[task_id] = record
            future = asyncio.run_coroutine_threadsafe(
                self._execute(record, operation, result_model, exclude_none),
                self._loop,
            )
            self._futures[task_id] = future
            future.add_done_callback(lambda _: self._discard_future(task_id))
        return record

    def get(self, task_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            record = self._records.get(task_id)
            return record.as_dict() if record is not None else None

    def pending_count(self) -> int:
        with self._lock:
            return len(self._futures)

    def _discard_future(self, task_id: str) -> None:
        with self._lock:
            self._futures.pop(task_id, None)

    def _discard_done_futures_locked(self) -> None:
        for task_id, future in list(self._futures.items()):
            if future.done():
                self._futures.pop(task_id, None)

    def _prune_terminal_records_locked(self) -> None:
        removable = [
            task_id
            for task_id, record in self._records.items()
            if record.status in {"completed", "failed"} and task_id not in self._futures
        ]
        while len(self._records) >= self.max_records and removable:
            self._records.pop(removable.pop(0), None)

    async def _execute(
            self,
            record: TaskRecord,
            operation: TaskOperation,
            result_model: Optional[Type[BaseModel]],
            exclude_none: bool,
    ) -> None:
        if self._semaphore is None:
            raise RuntimeError("Projector task worker is unavailable.")
        async with self._semaphore:
            with self._lock:
                record.status = "running"
                record.started_at = _now()
            try:
                result = operation()
                if inspect.isawaitable(result):
                    result = await result
                if result_model is not None:
                    result = result_model.model_validate(result).model_dump(
                        mode="json",
                        exclude_none=exclude_none,
                    )
                with self._lock:
                    record.result = result
                    record.status = "completed"
                    record.completed_at = _now()
            except asyncio.CancelledError:
                with self._lock:
                    record.status = "failed"
                    record.error = {
                        "type": "TaskCancelled",
                        "message": "Task cancelled before completion.",
                    }
                    record.completed_at = _now()
                raise
            except Exception:  # noqa: BLE001 - full details are logged, not exposed
                with self._lock:
                    record.status = "failed"
                    record.error = {
                        "type": "TaskExecutionError",
                        "message": "Task execution failed. Contact support with the task_id for details.",
                    }
                    record.completed_at = _now()
                logger.exception("Projector task %s failed", record.task_id)


task_manager = TaskManager()
