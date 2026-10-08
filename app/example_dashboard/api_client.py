"""Small polling client for the Projector asynchronous HTTP contract."""

import time
from urllib.parse import urljoin

import requests


class TaskFailedError(RuntimeError):
    pass


def _status_url(api_base_url: str, status_url: str) -> str:
    return urljoin(f"{api_base_url.rstrip('/')}/", status_url)


def post_task(api_base_url: str, endpoint: str, payload: dict, timeout_seconds: int) -> dict:
    """Submit an analysis task and poll until it completes or the UI timeout expires."""
    timeout_seconds = max(int(timeout_seconds), 1)
    request_timeout = min(timeout_seconds, 60)
    submitted = requests.post(
        f"{api_base_url.rstrip('/')}/{endpoint.lstrip('/')}",
        data=payload,
        timeout=request_timeout,
    )
    submitted.raise_for_status()
    accepted = submitted.json()
    task_id = accepted.get("task_id")
    status_url = accepted.get("status_url")
    if submitted.status_code != 202 or not task_id or not status_url:
        raise ValueError("The backend returned an invalid asynchronous task response.")

    deadline = time.monotonic() + timeout_seconds
    polling_url = _status_url(api_base_url, status_url)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise requests.Timeout(f"Task {task_id} did not complete within {timeout_seconds} seconds.")

        response = requests.get(polling_url, timeout=min(max(remaining, 1), 30))
        response.raise_for_status()
        task = response.json()
        task_status = task.get("status")
        if task_status == "completed":
            return task.get("result") or {}
        if task_status == "failed":
            error = task.get("error") or {}
            raise TaskFailedError(error.get("message") or f"Task {task_id} failed.")
        if task_status not in {"queued", "running"}:
            raise ValueError(f"Unknown task status: {task_status!r}")
        time.sleep(min(0.25, max(remaining, 0)))
