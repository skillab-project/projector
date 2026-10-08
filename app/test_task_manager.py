import threading
import time

import pytest

from app.core.task_manager import TaskManager, TaskQueueFull


def _wait_for_status(manager: TaskManager, task_id: str, expected: str, timeout: float = 2) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        record = manager.get(task_id)
        if record and record["status"] == expected:
            return record
        time.sleep(0.001)
    raise AssertionError(f"Task {task_id} did not reach {expected}")


def test_concurrency_above_one_is_rejected_for_shared_engine_safety():
    with pytest.raises(ValueError, match="concurrency must remain 1"):
        TaskManager(max_concurrency=2)


def test_blocking_operation_runs_outside_the_caller_thread():
    manager = TaskManager(max_concurrency=1, max_pending=2, max_records=2)
    started = threading.Event()
    release = threading.Event()

    def blocking_operation():
        started.set()
        release.wait(timeout=2)
        return {"answer": 42}

    record = manager.submit("/test", blocking_operation)
    assert started.wait(timeout=1)

    before = time.monotonic()
    running = manager.get(record.task_id)
    elapsed = time.monotonic() - before

    assert elapsed < 0.1
    assert running["status"] == "running"
    release.set()
    completed = _wait_for_status(manager, record.task_id, "completed")
    assert completed["result"] == {"answer": 42}


def test_pending_queue_is_bounded():
    manager = TaskManager(max_concurrency=1, max_pending=1, max_records=1)
    release = threading.Event()
    first = manager.submit("/test", lambda: release.wait(timeout=2))

    with pytest.raises(TaskQueueFull):
        manager.submit("/test", lambda: None)

    release.set()
    _wait_for_status(manager, first.task_id, "completed")


def test_old_terminal_records_are_evicted_at_capacity():
    manager = TaskManager(max_concurrency=1, max_pending=1, max_records=1)
    first = manager.submit("/test", lambda: {"sequence": 1})
    _wait_for_status(manager, first.task_id, "completed")

    deadline = time.monotonic() + 1
    while manager.pending_count() and time.monotonic() < deadline:
        time.sleep(0.001)

    second = manager.submit("/test", lambda: {"sequence": 2})

    assert manager.get(first.task_id) is None
    assert _wait_for_status(manager, second.task_id, "completed")["result"] == {"sequence": 2}
