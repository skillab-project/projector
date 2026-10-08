from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.routes.projector import task_manager
from app.core.container import service
from app.example_dashboard import api_client
from app.main import app


def _terminal_task(client: TestClient, status_url: str) -> dict:
    for _ in range(100):
        payload = client.get(status_url).json()
        if payload["status"] in {"completed", "failed"}:
            return payload
    raise AssertionError(f"Task at {status_url} did not reach a terminal state")


def test_endpoint_returns_202_and_result_is_retrievable_by_task_id():
    with TestClient(app) as client:
        submitted = client.post("/projector/statistical-comparison", data={
            "group_a_label": "A",
            "group_a_count": "4",
            "group_a_total": "10",
            "group_b_label": "B",
            "group_b_count": "7",
            "group_b_total": "10",
        })

        assert submitted.status_code == 202
        accepted = submitted.json()
        assert accepted["status"] == "queued"
        assert accepted["status_url"].endswith(accepted["task_id"])
        task = _terminal_task(client, accepted["status_url"])

    assert task["status"] == "completed"
    assert task["started_at"]
    assert task["completed_at"]
    assert task["result"]["method"] == "chi_square_2x2"


def test_endpoint_records_background_failure_and_unknown_task():
    with patch.object(service, "emerging_skills", new_callable=AsyncMock) as operation:
        operation.side_effect = RuntimeError("tracker unavailable")
        with TestClient(app) as client:
            submitted = client.post(
                "/projector/emerging-skills",
                data={"min_date": "2024-01-01", "max_date": "2024-01-31"},
            )
            task = _terminal_task(client, submitted.json()["status_url"])
            missing = client.get("/projector/tasks/unknown")

    assert task["status"] == "failed"
    assert task["completed_at"]
    assert task["error"] == {
        "type": "TaskExecutionError",
        "message": "Task execution failed. Contact support with the task_id for details.",
    }
    assert missing.status_code == 404
    assert missing.json()["detail"]["error"]["code"] == "task_not_found"


def test_endpoint_rejects_submission_when_task_queue_is_full():
    previous_limit = task_manager.max_pending
    task_manager.max_pending = 0
    try:
        with TestClient(app) as client:
            response = client.post("/projector/statistical-comparison", data={
                "group_a_label": "A",
                "group_a_count": "4",
                "group_a_total": "10",
                "group_b_label": "B",
                "group_b_count": "7",
                "group_b_total": "10",
            })
    finally:
        task_manager.max_pending = previous_limit

    assert response.status_code == 503
    assert response.json()["detail"]["error"]["code"] == "task_queue_full"


class _Response:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_dashboard_client_submits_polls_and_unwraps_result(monkeypatch):
    submitted = _Response(202, {
        "task_id": "task-1",
        "status": "queued",
        "status_url": "/projector/tasks/task-1",
    })
    statuses = iter([
        _Response(200, {"task_id": "task-1", "status": "running"}),
        _Response(200, {"task_id": "task-1", "status": "completed", "result": {"answer": 42}}),
    ])
    post = lambda *args, **kwargs: submitted
    get = lambda *args, **kwargs: next(statuses)
    monkeypatch.setattr(api_client.requests, "post", post)
    monkeypatch.setattr(api_client.requests, "get", get)
    monkeypatch.setattr(api_client.time, "sleep", lambda _: None)

    result = api_client.post_task(
        "http://localhost:8000/projector",
        "analyze-skills",
        {"min_date": "2024-01-01", "max_date": "2024-01-31"},
        10,
    )

    assert result == {"answer": 42}


def test_dashboard_client_surfaces_task_failure(monkeypatch):
    monkeypatch.setattr(api_client.requests, "post", lambda *args, **kwargs: _Response(202, {
        "task_id": "task-2",
        "status": "queued",
        "status_url": "/projector/tasks/task-2",
    }))
    monkeypatch.setattr(api_client.requests, "get", lambda *args, **kwargs: _Response(200, {
        "task_id": "task-2",
        "status": "failed",
        "error": {"type": "RuntimeError", "message": "boom"},
    }))

    with pytest.raises(api_client.TaskFailedError, match="boom"):
        api_client.post_task("http://localhost:8000/projector", "analyze-skills", {}, 10)
