import hashlib
import importlib
import os
import json
import sys
import tempfile
from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.container import ProjectorEngine
from app.core.container import engine, tracker, loader, occupations, regional, market, trends, sectoral, service
from app.main import  app
from app.services.esco_loader import EscoLoader
from app.services.analytics.occupations import OccupationAnalytics
from app.services.analytics.sectoral import SectoralAnalytics
from app.services.projector_service import ProjectorService
from scripts import backfill_sectoral_snapshots as backfill_script
from scripts import refresh_sectoral_snapshot as refresh_script
from scripts import schedule_sectoral_snapshot_refresh as scheduler_script
from scripts.schedule_sectoral_snapshot_refresh import due_targets

from dotenv import load_dotenv
load_dotenv()

client = TestClient(app)


class _FakeServiceEngine:
    def __init__(self):
        self.stop_requested = False

    def request_stop(self):
        self.stop_requested = True


class _FakeServiceTracker:
    def __init__(self, jobs):
        self.jobs = jobs
        self.fetch_payload = None
        self.fetch_payloads = []
        self.skill_names_requested = None

    async def fetch_all_jobs(self, payload):
        self.fetch_payload = payload
        self.fetch_payloads.append(payload)
        return self.jobs

    async def fetch_skill_names(self, skill_ids):
        self.skill_names_requested = skill_ids


class _FakeServiceMarket:
    def _empty_insights_p1(self):
        return {"ranking": [], "sectors": [], "job_titles": [], "employers": []}

    async def analyze_market_data(self, jobs):
        return {
            "total_jobs": len(jobs),
            "geo": [{"name": "IT", "count": len(jobs)}],
            "rankings": {
                "skills": [
                    {"id": "skill-python", "name": "Python"},
                    {"id": "skill-sql", "name": "SQL"},
                ],
                "sectors": [{"name": "Education", "count": 1}],
                "job_titles": [{"name": "Data Scientist", "count": 1}],
                "employers": [{"name": "ACME", "count": 1}],
            },
        }


class _FakeServiceTrends:
    async def calculate_trends_from_data(self, jobs, min_date, max_date):
        return [{"name": "Python", "growth": 10.0, "window": [min_date, max_date]}]

    async def calculate_smart_trends(self, filters, min_date, max_date):
        return {"filters": filters, "market_health": {"status": "stable"}, "trends": []}


class _FakeServiceRegional:
    def get_regional_projections(self, jobs, demo=False):
        return [{"location": "IT", "demo": demo, "count": len(jobs)}]


class _FakeServiceSectoral:
    def __init__(self):
        self.kwargs = None

    def build_sectoral_intelligence(self, **kwargs):
        self.kwargs = kwargs
        job = (kwargs.get("jobs") or [{"sectors": ["Education"]}])[0]
        sector = (job.get("sectors") or ["Education"])[0]
        return [{
            "sector": sector,
            "sector_label": sector,
            "observed_skills": {
                "sector": sector,
                "total_skill_mentions": 1,
                "unique_skills": 1,
                "top_skills": [{"skill_id": "skill-python", "count": 1, "frequency": 1.0}],
            },
        }]


class _FakeSectorSnapshotStore:
    enabled = True

    def __init__(self, payload=None):
        self.payload = payload
        self.requests = []

    def read_latest(self, year, location_code=None):
        self.requests.append((year, location_code))
        if isinstance(self.payload, dict) and "by_year" in self.payload:
            return self.payload["by_year"].get(year)
        return self.payload


class _FakeSchedulerSnapshotStore:
    def __init__(self, completed_at_by_key):
        self.completed_at_by_key = completed_at_by_key

    def latest_completed_at(self, year, location_code=None):
        return self.completed_at_by_key.get((year, location_code))


def test_scheduler_due_targets_returns_missing_snapshots():
    store = _FakeSchedulerSnapshotStore({})
    now = datetime(2026, 6, 5, tzinfo=timezone.utc)

    due = due_targets(store, 2024, 2024, ["IT"], True, 3, now)

    assert due == [(2024, "GLOBAL"), (2024, "IT")]


def test_scheduler_due_targets_skips_recent_snapshots():
    now = datetime(2026, 6, 5, tzinfo=timezone.utc)
    store = _FakeSchedulerSnapshotStore({
        (2024, None): now - timedelta(days=20),
        (2024, "IT"): now - timedelta(days=20),
    })

    due = due_targets(store, 2024, 2024, ["IT"], True, 3, now)

    assert due == []


def test_scheduler_due_targets_returns_elapsed_snapshots():
    now = datetime(2026, 6, 5, tzinfo=timezone.utc)
    store = _FakeSchedulerSnapshotStore({
        (2024, None): now - timedelta(days=120),
        (2024, "IT"): now - timedelta(days=20),
    })

    due = due_targets(store, 2024, 2024, ["IT"], True, 3, now)

    assert due == [(2024, "GLOBAL")]


def test_scheduler_refresh_plan_explains_refresh_state():
    now = datetime(2026, 6, 5, tzinfo=timezone.utc)
    old_completed = now - timedelta(days=120)
    recent_completed = now - timedelta(days=20)
    store = _FakeSchedulerSnapshotStore({
        (2024, None): old_completed,
        (2024, "IT"): recent_completed,
    })

    plan = scheduler_script.refresh_plan(store, 2024, 2024, ["IT", "DE"], True, 3, now)

    assert plan[0] == {
        "year": 2024,
        "location_code": None,
        "due": True,
        "last_completed_at": old_completed,
        "next_refresh_at": old_completed + timedelta(seconds=3 * scheduler_script.SECONDS_PER_MONTH),
        "reason": "interval elapsed",
    }
    assert plan[1]["due"] is False
    assert plan[1]["reason"] == "interval not elapsed"
    assert plan[1]["last_completed_at"] == recent_completed
    assert plan[2]["due"] is True
    assert plan[2]["reason"] == "never refreshed"
    assert plan[2]["last_completed_at"] is None
    assert plan[2]["next_refresh_at"] is None


def test_refresh_script_helpers_filter_jobs_and_years():
    jobs = [
        {"id": 1, "location_code": "IT"},
        {"id": 2, "location_code": " DE "},
        {"id": 3, "location_code": ""},
        {"id": 4},
    ]

    assert refresh_script.year_window(2024) == ("2024-01-01", "2024-12-31")
    assert [job["id"] for job in refresh_script.filter_jobs_by_location(jobs, None)] == [1, 2, 3, 4]
    assert [job["id"] for job in refresh_script.filter_jobs_by_location(jobs, "IT")] == [1]
    assert refresh_script.filter_jobs_by_location(jobs, "XXXX") == []
    assert refresh_script.available_location_codes(jobs) == ["DE", "IT"]


def test_script_import_bootstrap_inserts_repo_root(monkeypatch):
    module_names = [
        "scripts.backfill_sectoral_snapshots",
        "scripts.refresh_sectoral_snapshot",
        "scripts.schedule_sectoral_snapshot_refresh",
    ]
    originals = {name: sys.modules.get(name) for name in module_names}
    original_path = list(sys.path)
    repo_root = str(refresh_script.REPO_ROOT)

    try:
        for name in module_names:
            sys.path[:] = [path for path in sys.path if path != repo_root]
            monkeypatch.delitem(sys.modules, name, raising=False)
            importlib.import_module(name)
            assert repo_root in sys.path
    finally:
        sys.path[:] = original_path
        for name, module in originals.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


@pytest.mark.asyncio
async def test_refresh_script_fetch_jobs_for_year_adds_location(monkeypatch):
    fake_fetch = AsyncMock(return_value=[{"id": 1}])
    monkeypatch.setattr(refresh_script.tracker, "fetch_all_jobs", fake_fetch)

    result = await refresh_script.fetch_jobs_for_year(2024, "IT")

    assert result == [{"id": 1}]
    assert fake_fetch.await_args.args[0] == {
        "min_upload_date": "2024-01-01",
        "max_upload_date": "2024-12-31",
        "location_code": ["IT"],
    }


@pytest.mark.asyncio
async def test_refresh_script_fetch_jobs_for_year_without_location(monkeypatch):
    fake_fetch = AsyncMock(return_value=[])
    monkeypatch.setattr(refresh_script.tracker, "fetch_all_jobs", fake_fetch)

    await refresh_script.fetch_jobs_for_year(2024)

    assert fake_fetch.await_args.args[0] == {
        "min_upload_date": "2024-01-01",
        "max_upload_date": "2024-12-31",
    }


@pytest.mark.asyncio
async def test_refresh_script_write_snapshot_from_jobs():
    store = MagicMock()
    store.write_snapshot.return_value = 42
    service = SimpleNamespace(
        sector_snapshot_store=store,
        _ensure_skill_labels=AsyncMock(),
        _build_sector_snapshot_rows=MagicMock(return_value=[{"sector": "Education"}]),
    )
    jobs = [{"id": 1, "skills": ["skill-a"], "sectors": ["Education"]}]

    result = await refresh_script.write_snapshot_from_jobs(service, 2024, jobs, "IT")

    assert result == (42, 1, 1)
    service._ensure_skill_labels.assert_awaited_once_with(jobs)
    service._build_sector_snapshot_rows.assert_called_once_with(jobs)
    store.write_snapshot.assert_called_once_with(
        year=2024,
        location_code="IT",
        period_start="2024-01-01",
        period_end="2024-12-31",
        total_jobs=1,
        sectors=[{"sector": "Education"}],
    )


@pytest.mark.asyncio
async def test_refresh_script_refresh_snapshot_composes_steps(monkeypatch):
    service = object()
    monkeypatch.setattr(refresh_script, "build_projector_service", lambda: service)
    fetch_jobs = AsyncMock(return_value=[{"id": 1}])
    write_jobs = AsyncMock(return_value=(7, 1, 1))
    monkeypatch.setattr(refresh_script, "fetch_jobs_for_year", fetch_jobs)
    monkeypatch.setattr(refresh_script, "write_snapshot_from_jobs", write_jobs)

    result = await refresh_script.refresh_snapshot(2024, "IT")

    assert result == (7, 1, 1)
    fetch_jobs.assert_awaited_once_with(2024, "IT")
    write_jobs.assert_awaited_once_with(service, 2024, [{"id": 1}], "IT")


def test_refresh_script_build_projector_service_requires_database(monkeypatch):
    class FakeStore:
        enabled = False

        def __init__(self, database_url):
            self.database_url = database_url

    monkeypatch.setattr(refresh_script, "DATABASE_URL", "")
    monkeypatch.setattr(refresh_script, "SectorSnapshotStore", FakeStore)

    with pytest.raises(RuntimeError) as exc_info:
        refresh_script.build_projector_service()
    assert str(exc_info.value) == "DATABASE_URL not configured"


def test_refresh_script_build_projector_service_returns_service(monkeypatch):
    class FakeStore:
        enabled = True

        def __init__(self, database_url):
            self.database_url = database_url

    created = {}

    class FakeProjectorService:
        def __init__(self, *args):
            created["args"] = args

    monkeypatch.setattr(refresh_script, "DATABASE_URL", "postgresql://db")
    monkeypatch.setattr(refresh_script, "SectorSnapshotStore", FakeStore)
    monkeypatch.setattr(refresh_script, "ProjectorService", FakeProjectorService)

    service_obj = refresh_script.build_projector_service()

    assert isinstance(service_obj, FakeProjectorService)
    assert created["args"][:-1] == (
        refresh_script.engine,
        refresh_script.tracker,
        refresh_script.occupations,
        refresh_script.regional,
        refresh_script.market,
        refresh_script.trends,
        refresh_script.sectoral,
    )
    assert created["args"][-1].database_url == "postgresql://db"


def test_refresh_script_main_prints_summary(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["refresh", "--year", "2024", "--location-code", "IT"])
    monkeypatch.setattr(refresh_script, "refresh_snapshot", AsyncMock(return_value=(9, 10, 3)))

    refresh_script.main()

    out = capsys.readouterr().out
    assert "sector snapshot refreshed: run_id=9 year=2024 jobs=10 sectors=3" in out


def test_backfill_script_helpers(tmp_path, monkeypatch):
    monkeypatch.setattr(backfill_script, "REPO_ROOT", tmp_path)
    backfill_script.setup_logging("logs/test.log", True)
    absolute_log = tmp_path / "absolute.log"
    backfill_script.setup_logging(str(absolute_log), False)

    assert (tmp_path / "logs" / "test.log").exists()
    assert absolute_log.exists()
    assert backfill_script.progress_bar(0, 0) == "[------------------------] 0/0"
    assert backfill_script.progress_bar(1, 1) == "[########################] 1/1"
    assert backfill_script.progress_bar(12, 24) == "[############------------] 12/24"
    assert backfill_script.progress_bar(5, 10, width=10) == "[#####-----] 5/10"
    assert backfill_script.parse_regions(None) is None
    assert backfill_script.parse_regions(["IT, DE", "IT"]) == ["DE", "IT"]


def test_backfill_script_fetch_progress_message(monkeypatch):
    monkeypatch.setattr(backfill_script.time, "perf_counter", lambda: 12.5)

    message = backfill_script.fetch_progress_message(
        2024,
        {"fetched": 5, "total": 10, "page": 2, "page_concurrency": 4, "source": "tracker_parallel"},
        10.0,
    )

    assert "year 2024: fetching Tracker jobs" in message
    assert "page=2" in message
    assert "concurrency=4" in message
    assert "elapsed=2.5s" in message


@pytest.mark.asyncio
async def test_backfill_script_fetch_jobs_with_progress(monkeypatch):
    callbacks = []
    info_messages = []

    class FakeTracker:
        async def fetch_all_jobs(
                self,
                filters,
                page_size,
                progress_callback,
                page_concurrency,
                max_retries,
                require_complete_cache,
        ):
            assert filters == {"min_upload_date": "2024-01-01", "max_upload_date": "2024-12-31"}
            assert page_size == 100
            assert page_concurrency == 4
            assert max_retries == 2
            assert require_complete_cache is True
            progress_callback({"fetched": 1, "total": 2, "page": 1, "done": False})
            progress_callback({"fetched": 2, "total": 2, "page": 2, "done": True})
            callbacks.append("called")
            return [{"id": 1}, {"id": 2}]

    monkeypatch.setattr(backfill_script.time, "perf_counter", lambda: 10.0)
    monkeypatch.setattr(backfill_script.logger, "info", lambda message, *args: info_messages.append(message % args if args else message))
    jobs, elapsed = await backfill_script.fetch_jobs_for_year_with_progress(
        SimpleNamespace(tracker=FakeTracker()),
        2024,
        page_size=100,
        page_concurrency=4,
        max_retries=2,
    )

    assert jobs == [{"id": 1}, {"id": 2}]
    assert elapsed == 0.0
    assert callbacks == ["called"]
    assert any("year 2024: fetching Tracker jobs" in message for message in info_messages)
    assert all(message is not None for message in info_messages)


@pytest.mark.asyncio
async def test_backfill_script_backfill_year_writes_global_and_regions(monkeypatch):
    service = object()
    jobs = [
        {"id": 1, "location_code": "IT"},
        {"id": 2, "location_code": "DE"},
    ]
    writes = []
    fetch_jobs = AsyncMock(return_value=(jobs, 1.5))

    monkeypatch.setattr(backfill_script, "build_projector_service", lambda: service)
    monkeypatch.setattr(
        backfill_script,
        "fetch_jobs_for_year_with_progress",
        fetch_jobs,
    )

    async def fake_write_snapshot_from_jobs(service_arg, year, selected_jobs, location_code):
        writes.append((service_arg, year, [job["id"] for job in selected_jobs], location_code))
        return len(writes), len(selected_jobs), 1

    monkeypatch.setattr(backfill_script, "write_snapshot_from_jobs", fake_write_snapshot_from_jobs)

    result = await backfill_script.backfill_year(
        2024,
        regions=None,
        include_global=True,
        page_size=100,
        page_concurrency=4,
        max_retries=2,
    )

    assert result == [
        (2024, "GLOBAL", 1, 2, 1),
        (2024, "DE", 2, 1, 1),
        (2024, "IT", 3, 1, 1),
    ]
    fetch_jobs.assert_awaited_once_with(service, 2024, 100, 4, 2)
    assert writes == [
        (service, 2024, [1, 2], None),
        (service, 2024, [2], "DE"),
        (service, 2024, [1], "IT"),
    ]


@pytest.mark.asyncio
async def test_backfill_script_backfill_year_cli_regions_without_global(monkeypatch):
    monkeypatch.setattr(backfill_script, "build_projector_service", lambda: object())
    monkeypatch.setattr(
        backfill_script,
        "fetch_jobs_for_year_with_progress",
        AsyncMock(return_value=([{"id": 1, "location_code": "IT"}], 1.0)),
    )
    monkeypatch.setattr(
        backfill_script,
        "write_snapshot_from_jobs",
        AsyncMock(return_value=(11, 1, 1)),
    )

    result = await backfill_script.backfill_year(
        2024,
        regions=["IT"],
        include_global=False,
        page_size=100,
        page_concurrency=4,
        max_retries=2,
    )

    assert result == [(2024, "IT", 11, 1, 1)]


@pytest.mark.asyncio
async def test_backfill_script_backfill_snapshots_success(monkeypatch):
    monkeypatch.setattr(backfill_script.logger, "handlers", [backfill_script.logging.NullHandler()])
    monkeypatch.setattr(backfill_script.time, "perf_counter", lambda: 10.0)
    monkeypatch.setattr(
        backfill_script,
        "backfill_year",
        AsyncMock(side_effect=[
            [(2023, "GLOBAL", 1, 2, 3)],
            [(2024, "GLOBAL", 2, 3, 4)],
        ]),
    )

    result = await backfill_script.backfill_snapshots(
        2023,
        2024,
        regions=["IT"],
        include_global=True,
        page_size=100,
        page_concurrency=4,
        max_retries=2,
    )

    assert result == [(2023, "GLOBAL", 1, 2, 3), (2024, "GLOBAL", 2, 3, 4)]


@pytest.mark.asyncio
async def test_backfill_script_backfill_snapshots_default_fetch_config(monkeypatch):
    monkeypatch.setattr(backfill_script.logger, "handlers", [backfill_script.logging.NullHandler()])
    backfill_year = AsyncMock(return_value=[])
    monkeypatch.setattr(backfill_script, "backfill_year", backfill_year)

    await backfill_script.backfill_snapshots(2024, 2024, regions=None, include_global=True)

    backfill_year.assert_awaited_once_with(2024, None, True, 500, 1, 5)


@pytest.mark.asyncio
async def test_backfill_script_backfill_snapshots_sets_logging_and_reraises(monkeypatch):
    monkeypatch.setattr(backfill_script.logger, "handlers", [])
    setup = MagicMock()
    monkeypatch.setattr(backfill_script, "setup_logging", setup)
    monkeypatch.setattr(backfill_script, "backfill_year", AsyncMock(side_effect=RuntimeError("boom")))

    with pytest.raises(RuntimeError, match="boom"):
        await backfill_script.backfill_snapshots(2024, 2024, None, True)

    setup.assert_called_once_with("logs/sector_snapshot_backfill.log", False)


def test_backfill_script_main_validates_args(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["backfill", "--start-year", "2025", "--end-year", "2024"])

    with pytest.raises(ValueError, match="--end-year"):
        backfill_script.main()

    for flag, value, message in [
        ("--page-size", "0", "--page-size"),
        ("--page-concurrency", "0", "--page-concurrency"),
        ("--max-retries", "0", "--max-retries"),
    ]:
        monkeypatch.setattr(sys, "argv", ["backfill", "--start-year", "2024", flag, value])
        with pytest.raises(ValueError, match=message):
            backfill_script.main()


def test_backfill_script_main_runs(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "backfill",
            "--start-year",
            "2024",
            "--end-year",
            "2024",
            "--regions",
            "IT,DE",
            "--skip-global",
            "--log-file",
            "custom.log",
            "--debug",
            "--page-size",
            "100",
            "--page-concurrency",
            "4",
            "--max-retries",
            "2",
        ],
    )
    setup = MagicMock()
    backfill = AsyncMock(return_value=[])
    monkeypatch.setattr(backfill_script, "setup_logging", setup)
    monkeypatch.setattr(backfill_script, "backfill_snapshots", backfill)

    backfill_script.main()

    setup.assert_called_once_with("custom.log", True)
    backfill.assert_awaited_once_with(
        start_year=2024,
        end_year=2024,
        regions=["DE", "IT"],
        include_global=False,
        page_size=100,
        page_concurrency=4,
        max_retries=2,
    )


def test_scheduler_env_helpers(monkeypatch):
    monkeypatch.delenv("SNAPSHOT_INT", raising=False)
    monkeypatch.setenv("SNAPSHOT_INT_VALUE", "5")
    monkeypatch.setenv("SNAPSHOT_BOOL_ONE", "1")
    monkeypatch.setenv("SNAPSHOT_BOOL_TRUE_WORD", "true")
    monkeypatch.setenv("SNAPSHOT_BOOL_ON", "on")
    monkeypatch.setenv("SNAPSHOT_BOOL_TRUE", "yes")
    monkeypatch.setenv("SNAPSHOT_BOOL_FALSE", "no")
    monkeypatch.setenv("SNAPSHOT_REGIONS_TEST", "IT, DE")

    assert scheduler_script.env_int("SNAPSHOT_INT", 3) == 3
    assert scheduler_script.env_int("SNAPSHOT_INT_VALUE", 3) == 5
    assert scheduler_script.env_bool("SNAPSHOT_BOOL_ONE", False) is True
    assert scheduler_script.env_bool("SNAPSHOT_BOOL_TRUE_WORD", False) is True
    assert scheduler_script.env_bool("SNAPSHOT_BOOL_ON", False) is True
    assert scheduler_script.env_bool("SNAPSHOT_BOOL_TRUE", False) is True
    assert scheduler_script.env_bool("SNAPSHOT_BOOL_FALSE", True) is False
    assert scheduler_script.env_regions("SNAPSHOT_REGIONS_TEST") == ["DE", "IT"]
    assert scheduler_script.env_regions("MISSING_REGIONS") is None


def test_scheduler_targets_and_time_normalization():
    naive = datetime(2024, 1, 1, 12, 0, 0)
    aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    plus_two = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=2)))

    assert scheduler_script.normalize_completed_at(None) is None
    assert scheduler_script.normalize_completed_at(naive).tzinfo == timezone.utc
    assert scheduler_script.normalize_completed_at(aware) == aware
    normalized_plus_two = scheduler_script.normalize_completed_at(plus_two)
    assert normalized_plus_two == datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    assert normalized_plus_two.tzinfo == timezone.utc
    assert scheduler_script.snapshot_targets(2024, 2025, ["IT"], True) == [
        (2024, None),
        (2024, "IT"),
        (2025, None),
        (2025, "IT"),
    ]
    assert scheduler_script.snapshot_targets(2024, 2024, None, False) == []


def test_scheduler_due_targets_without_targets():
    due = due_targets(_FakeSchedulerSnapshotStore({}), 2024, 2024, None, False, 3)
    plan = scheduler_script.refresh_plan(_FakeSchedulerSnapshotStore({}), 2024, 2024, None, False, 3)

    assert due == [("unknown", "auto")]
    assert plan[0]["reason"] == "no explicit targets configured"


def test_scheduler_due_targets_uses_current_time_and_interval_boundary():
    now = datetime.now(timezone.utc)
    store = _FakeSchedulerSnapshotStore({
        (2024, None): now,
    })

    assert due_targets(store, 2024, 2024, None, True, 3) == []

    boundary_now = datetime(2026, 6, 5, tzinfo=timezone.utc)
    boundary_store = _FakeSchedulerSnapshotStore({
        (2024, None): boundary_now - timedelta(seconds=3 * scheduler_script.SECONDS_PER_MONTH),
    })

    assert due_targets(boundary_store, 2024, 2024, None, True, 3, boundary_now) == [(2024, "GLOBAL")]


@pytest.mark.asyncio
async def test_scheduler_run_scheduled_refresh_due_then_stops(monkeypatch):
    monkeypatch.setattr(scheduler_script, "DATABASE_URL", "postgresql://db")
    monkeypatch.setattr(scheduler_script, "SectorSnapshotStore", lambda database_url: _FakeSchedulerSnapshotStore({}))
    monkeypatch.setattr(scheduler_script, "refresh_plan", MagicMock(return_value=[{
        "year": 2024,
        "location_code": None,
        "due": True,
        "last_completed_at": None,
        "next_refresh_at": None,
        "reason": "never refreshed",
    }]))
    backfill = AsyncMock(return_value=[])
    monkeypatch.setattr(scheduler_script, "backfill_snapshots", backfill)

    async def stop_sleep(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(scheduler_script.asyncio, "sleep", stop_sleep)

    with pytest.raises(KeyboardInterrupt):
        await scheduler_script.run_scheduled_refresh(
            start_year=2024,
            end_year=2024,
            interval_months=3,
            check_interval_days=1,
            regions=["IT"],
            include_global=True,
            run_immediately=True,
            page_size=100,
            page_concurrency=4,
            max_retries=2,
        )

    backfill.assert_awaited_once_with(
        start_year=2024,
        end_year=2024,
        regions=["IT"],
        include_global=True,
        page_size=100,
        page_concurrency=4,
        max_retries=2,
    )


@pytest.mark.asyncio
async def test_scheduler_run_scheduled_refresh_skip_and_initial_wait(monkeypatch):
    monkeypatch.setattr(scheduler_script, "DATABASE_URL", "postgresql://db")
    monkeypatch.setattr(scheduler_script, "SectorSnapshotStore", lambda database_url: _FakeSchedulerSnapshotStore({}))
    now = datetime(2026, 6, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(scheduler_script, "refresh_plan", MagicMock(return_value=[{
        "year": 2024,
        "location_code": None,
        "due": False,
        "last_completed_at": now,
        "next_refresh_at": now + timedelta(seconds=3 * scheduler_script.SECONDS_PER_MONTH),
        "reason": "interval not elapsed",
    }]))
    backfill = AsyncMock(return_value=[])
    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)
        if len(sleep_calls) == 2:
            raise KeyboardInterrupt

    monkeypatch.setattr(scheduler_script.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(scheduler_script, "backfill_snapshots", backfill)

    with pytest.raises(KeyboardInterrupt):
        await scheduler_script.run_scheduled_refresh(
            start_year=2024,
            end_year=2024,
            interval_months=3,
            check_interval_days=2,
            regions=None,
            include_global=False,
            run_immediately=False,
            page_size=100,
            page_concurrency=4,
            max_retries=2,
        )

    assert sleep_calls == [2 * scheduler_script.SECONDS_PER_DAY, 2 * scheduler_script.SECONDS_PER_DAY]
    backfill.assert_not_awaited()


@pytest.mark.asyncio
async def test_scheduler_run_scheduled_refresh_accepts_one_month_interval(monkeypatch):
    monkeypatch.setattr(scheduler_script, "DATABASE_URL", "postgresql://db")
    monkeypatch.setattr(scheduler_script, "SectorSnapshotStore", lambda database_url: _FakeSchedulerSnapshotStore({}))
    now = datetime(2026, 6, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(scheduler_script, "refresh_plan", MagicMock(return_value=[{
        "year": 2024,
        "location_code": None,
        "due": False,
        "last_completed_at": now,
        "next_refresh_at": now + timedelta(seconds=scheduler_script.SECONDS_PER_MONTH),
        "reason": "interval not elapsed",
    }]))

    async def stop_sleep(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(scheduler_script.asyncio, "sleep", stop_sleep)

    with pytest.raises(KeyboardInterrupt):
        await scheduler_script.run_scheduled_refresh(
            start_year=2024,
            end_year=2024,
            interval_months=1,
            check_interval_days=1,
            regions=None,
            include_global=False,
            run_immediately=True,
            page_size=100,
            page_concurrency=4,
            max_retries=2,
        )


@pytest.mark.asyncio
async def test_scheduler_run_scheduled_refresh_validates(monkeypatch):
    monkeypatch.setattr(scheduler_script, "DATABASE_URL", "postgresql://db")

    with pytest.raises(ValueError, match="--interval-months"):
        await scheduler_script.run_scheduled_refresh(2024, 2024, 0, 1, None, True, True, 100, 4, 2)
    with pytest.raises(ValueError, match="--check-interval-days"):
        await scheduler_script.run_scheduled_refresh(2024, 2024, 3, 0, None, True, True, 100, 4, 2)

    monkeypatch.setattr(scheduler_script, "DATABASE_URL", "")
    with pytest.raises(RuntimeError, match="DATABASE_URL not configured"):
        await scheduler_script.run_scheduled_refresh(2024, 2024, 3, 1, None, True, True, 100, 4, 2)


def test_scheduler_main_validates_args(monkeypatch):
    for args, message in [
        (["scheduler", "--start-year", "2025", "--end-year", "2024"], "--end-year"),
        (["scheduler", "--interval-months", "0"], "--interval-months"),
        (["scheduler", "--check-interval-days", "0"], "--check-interval-days"),
        (["scheduler", "--page-size", "0"], "--page-size"),
        (["scheduler", "--page-concurrency", "0"], "--page-concurrency"),
        (["scheduler", "--max-retries", "0"], "--max-retries"),
    ]:
        monkeypatch.setattr(sys, "argv", args)
        with pytest.raises(ValueError, match=message):
            scheduler_script.main()


def test_scheduler_main_runs_and_handles_keyboard_interrupt(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scheduler",
            "--interval-months",
            "3",
            "--check-interval-days",
            "1",
            "--start-year",
            "2024",
            "--end-year",
            "2024",
            "--regions",
            "IT,DE",
            "--skip-global",
            "--no-run-immediately",
            "--page-size",
            "100",
            "--page-concurrency",
            "4",
            "--max-retries",
            "2",
        ],
    )
    run_refresh = AsyncMock(side_effect=KeyboardInterrupt)
    monkeypatch.setattr(scheduler_script, "run_scheduled_refresh", run_refresh)

    scheduler_script.main()

    run_refresh.assert_awaited_once_with(
        start_year=2024,
        end_year=2024,
        interval_months=3,
        check_interval_days=1,
        regions=["DE", "IT"],
        include_global=False,
        run_immediately=False,
        page_size=100,
        page_concurrency=4,
        max_retries=2,
    )
    assert "scheduled sector snapshot refresh stopped" in capsys.readouterr().out


def _make_projector_service(jobs, sector_snapshot_store=None):
    fake_engine = _FakeServiceEngine()
    fake_tracker = _FakeServiceTracker(jobs)
    fake_sectoral = _FakeServiceSectoral()
    fake_service = ProjectorService(
        fake_engine,
        fake_tracker,
        occupations=None,
        regional=_FakeServiceRegional(),
        market=_FakeServiceMarket(),
        trends=_FakeServiceTrends(),
        sectoral=fake_sectoral,
        sector_snapshot_store=sector_snapshot_store,
    )
    return fake_service, fake_engine, fake_tracker, fake_sectoral



# ==========================================
# 1. TEST UNITARI (Engine & Intelligence)
# ==========================================

@pytest.mark.asyncio
async def test_projector_service_empty_jobs_returns_empty_insights():
    fake_service, _, fake_tracker, _ = _make_projector_service([])

    result = await fake_service.analyze_skills(
        keywords=["data"],
        locations=["IT"],
        min_date="2024-01-01",
        max_date="2024-01-31",
        page=1,
        page_size=50,
        include_sectoral=False,
    )

    assert result["status"] == "completed"
    assert result["dimension_summary"]["jobs_analyzed"] == 0
    assert result["insights"]["ranking"] == []
    assert fake_tracker.fetch_payload == {
        "keywords": ["data"],
        "location_code": ["IT"],
        "min_upload_date": "2024-01-01",
        "max_upload_date": "2024-01-31",
    }


@pytest.mark.asyncio
async def test_projector_service_analyze_skills_paginates_and_enriches_api_skills():
    jobs = [
        {"skills": ["skill-python", "skill-sql"], "sectors": ["Education"]},
        {"skills": ["skill-python"], "sectors": ["Research"]},
    ]
    fake_service, _, fake_tracker, _ = _make_projector_service(jobs)

    result = await fake_service.analyze_skills(
        min_date="2024-01-01",
        max_date="2024-01-31",
        page=2,
        page_size=1,
        demo=True,
        include_sectoral=False,
    )

    assert result["status"] == "completed"
    assert result["dimension_summary"]["jobs_analyzed"] == 2
    assert result["insights"]["ranking"] == [{"id": "skill-sql", "name": "SQL"}]
    assert result["insights"]["regional"] == [{"location": "IT", "demo": True, "count": 2}]
    assert result["insights"]["sectoral"] is None
    assert set(fake_tracker.skill_names_requested) == {"skill-python", "skill-sql"}


@pytest.mark.asyncio
async def test_projector_service_sectoral_uses_tracker_sectors_view():
    jobs = [{"skills": ["skill-python"], "sectors": ["Education"]}]
    fake_service, _, _, fake_sectoral = _make_projector_service(jobs)

    result = await fake_service.analyze_skills(
        min_date="2024-01-01",
        max_date="2024-01-31",
        page=1,
        page_size=50,
        include_sectoral=True,
        sector_system="isco",
        sector_level="nace_class",
        skill_group_level=2,
        occupation_level=3,
    )

    assert result["insights"]["sectoral_mode"] == "nace"
    assert result["insights"]["sectoral_views"] == {
        "nace": {
            "sector_level": "tracker_sector",
            "time_mode": "latest",
            "window": {
                "label": "Last six months",
                "min_date": result["insights"]["sectoral_views"]["nace"]["window"]["min_date"],
                "max_date": result["insights"]["sectoral_views"]["nace"]["window"]["max_date"],
            },
            "items": [{
                "sector": "Education",
                "sector_label": "Education",
                "observed_skills": {
                    "sector": "Education",
                    "total_skill_mentions": 1,
                    "unique_skills": 1,
                    "top_skills": [{"skill_id": "skill-python", "count": 1, "frequency": 1.0}],
                },
            }],
        }
    }
    assert result["insights"]["sector_view_names"]["nace"]["observed"] == "Observed"
    assert result["insights"]["sector_view_names"]["nace"]["latest"] == "Last six months"
    assert fake_sectoral.kwargs["jobs"] == jobs
    assert fake_sectoral.kwargs["sector_level"] == "nace_section"
    assert fake_sectoral.kwargs["skill_group_level"] == 2
    assert fake_sectoral.kwargs["occupation_level"] == 3
    assert fake_sectoral.kwargs["reset"] is True


@pytest.mark.asyncio
async def test_projector_service_sectoral_selected_period_reuses_main_jobs():
    jobs = [{"skills": ["skill-python"], "sectors": ["Education"]}]
    fake_service, _, fake_tracker, fake_sectoral = _make_projector_service(jobs)

    result = await fake_service.analyze_skills(
        min_date="2024-01-01",
        max_date="2024-01-31",
        page=1,
        page_size=50,
        include_sectoral=True,
        sectoral_time_mode="selected_period",
    )

    view = result["insights"]["sectoral_views"]["nace"]
    assert view["time_mode"] == "selected_period"
    assert view["window"] == {
        "label": "Selected period",
        "min_date": "2024-01-01",
        "max_date": "2024-01-31",
    }
    assert len(fake_tracker.fetch_payloads) == 1
    assert fake_sectoral.kwargs["jobs"] == jobs


@pytest.mark.asyncio
async def test_projector_service_sectoral_comparison_fetches_independent_periods():
    jobs = [{"skills": ["skill-python"], "sectors": ["Education"]}]
    fake_service, _, fake_tracker, _ = _make_projector_service(jobs)

    result = await fake_service.analyze_skills(
        keywords=["data"],
        min_date="2024-01-01",
        max_date="2024-01-31",
        page=1,
        page_size=50,
        include_sectoral=True,
        sectoral_time_mode="comparison",
        sectoral_compare_a_min_date="2023-01-01",
        sectoral_compare_a_max_date="2023-06-30",
        sectoral_compare_b_min_date="2024-01-01",
        sectoral_compare_b_max_date="2024-06-30",
    )

    view = result["insights"]["sectoral_views"]["nace"]
    assert view["time_mode"] == "comparison"
    assert view["comparison"]["period_a"]["min_date"] == "2023-01-01"
    assert view["comparison"]["period_b"]["max_date"] == "2024-06-30"
    assert "period_a" in view["snapshots"]
    assert "period_b" in view["snapshots"]
    assert fake_tracker.fetch_payloads[1]["min_upload_date"] == "2023-01-01"
    assert fake_tracker.fetch_payloads[2]["max_upload_date"] == "2024-06-30"


@pytest.mark.asyncio
async def test_projector_service_sectoral_intelligence_endpoint_contract():
    jobs = [{"skills": ["skill-python"], "sectors": ["Education"]}]
    fake_service, _, fake_tracker, _ = _make_projector_service(jobs)

    result = await fake_service.sectoral_intelligence(
        keywords=["data"],
        mode="selected_period",
        min_date="2024-01-01",
        max_date="2024-01-31",
    )

    assert result["status"] == "completed"
    assert result["mode"] == "selected_period"
    assert result["sector_level"] == "tracker_sector"
    assert result["window"] == {
        "label": "Selected period",
        "min_date": "2024-01-01",
        "max_date": "2024-01-31",
    }
    assert result["items"][0]["sector"] == "Education"
    assert result["sector_view_names"]["comparison"] == "Period comparison"
    assert fake_tracker.fetch_payloads == [{
        "keywords": ["data"],
        "min_upload_date": "2024-01-01",
        "max_upload_date": "2024-01-31",
    }]


@pytest.mark.asyncio
async def test_projector_service_sectoral_intelligence_filters_by_sector():
    jobs = [
        {"skills": ["skill-python"], "sectors": ["Education"]},
        {"skills": ["skill-sql"], "sectors": ["Manufacturing"]},
    ]
    fake_service, _, _, _ = _make_projector_service(jobs)

    result = await fake_service.sectoral_intelligence(
        data_source="live",
        mode="selected_period",
        min_date="2024-01-01",
        max_date="2024-01-31",
        sectors=["Education"],
    )

    assert result["data_source"] == "live"
    assert result["sector_filter"] == ["Education"]
    assert [item["sector"] for item in result["items"]] == ["Education"]


@pytest.mark.asyncio
async def test_projector_service_sectoral_snapshot_aggregates_year():
    jobs = [
        {
            "title": "Data Scientist",
            "skills": ["skill-python", "skill-sql"],
            "sectors": ["Education"],
        },
        {
            "title": "Data Scientist",
            "skills": ["skill-python"],
            "sectors": ["Education", "Manufacturing"],
        },
    ]
    fake_service, _, fake_tracker, _ = _make_projector_service(jobs)

    result = await fake_service.sectoral_snapshot(
        year=2024,
        data_source="live",
        sectors=["Education"],
    )

    assert result["status"] == "completed"
    assert result["year"] == 2024
    assert result["reference_year"] == 2023
    assert result["data_source"] == "live"
    assert result["window"]["min_date"] == "2024-01-01"
    assert result["sector_filter"] == ["Education"]
    assert fake_tracker.fetch_payloads == [{
        "min_upload_date": "2024-01-01",
        "max_upload_date": "2024-12-31",
    }]

    assert len(result["sectors"]) == 1
    sector = result["sectors"][0]
    assert sector["sector"] == "Education"
    assert sector["job_count"] == 2
    assert sector["total_skill_mentions"] == 3
    assert sector["unique_skills"] == 2
    assert sector["top_skills"][0]["skill_id"] == "skill-python"
    assert sector["top_skills"][0]["share_in_sector"] == round(2 / 3, 6)
    assert sector["top_skills"][0]["rank"] == 1
    assert sector["top_skills"][0]["growth_vs_reference_year"] == "new_entry"
    assert sector["top_skills"][0]["sector_breadth"] == 1
    assert sector["all_skills"][0]["skill_id"] == "skill-python"
    assert len(sector["all_skills"]) == 2
    assert sector["evolution"]["job_count_current"] == 2
    assert sector["evolution"]["job_count_reference"] == 0
    assert sector["evolution"]["job_growth_percentage"] == "new_entry"
    assert sector["evolution"]["new_skill_count"] == 2
    assert sector["top_job_titles"] == [{"name": "Data Scientist", "count": 2}]


@pytest.mark.asyncio
async def test_projector_service_sectoral_snapshot_prefers_static_store():
    store_payload = {
        "by_year": {
            2023: {
                "status": "completed",
                "year": 2023,
                "data_source": "postgres",
                "window": {"label": "2023 snapshot", "min_date": "2023-01-01", "max_date": "2023-12-31"},
                "total_jobs": 8,
                "sector_filter": [],
                "sectors": [{
                    "sector": "Education",
                    "sector_label": "Education",
                    "job_count": 8,
                    "job_share": 1.0,
                    "total_skill_mentions": 12,
                    "unique_skills": 2,
                    "top_skills": [{"skill_id": "skill-python", "label": "Python", "count": 2, "frequency": 0.2}],
                    "all_skills": [
                        {"skill_id": "skill-python", "label": "Python", "count": 2, "frequency": 0.1667},
                        {"skill_id": "skill-legacy", "label": "Legacy systems", "count": 2, "frequency": 0.1667},
                    ],
                    "top_job_titles": [],
                }],
            },
            2024: {
                "status": "completed",
                "year": 2024,
                "data_source": "postgres",
                "window": {"label": "2024 snapshot", "min_date": "2024-01-01", "max_date": "2024-12-31"},
                "total_jobs": 10,
                "sector_filter": [],
                "sectors": [{
                    "sector": "Education",
                    "sector_label": "Education",
                    "job_count": 10,
                    "job_share": 1.0,
                    "total_skill_mentions": 20,
                    "unique_skills": 1,
                    "top_skills": [{"skill_id": "skill-python", "label": "Python", "count": 4, "frequency": 0.2}],
                    "all_skills": [{"skill_id": "skill-python", "label": "Python", "count": 4, "frequency": 0.2}],
                    "top_job_titles": [],
                }],
            },
        }
    }
    store = _FakeSectorSnapshotStore(store_payload)
    fake_service, _, fake_tracker, _ = _make_projector_service([], sector_snapshot_store=store)

    result = await fake_service.sectoral_snapshot(year=2024, reference_year=2023, locations=["IT"])

    assert result["reference_year"] == 2023
    assert result["sectors"][0]["top_skills"][0]["growth_vs_reference_year"] == 1.0
    evolution = result["sectors"][0]["evolution"]
    assert evolution["job_count_current"] == 10
    assert evolution["job_count_reference"] == 8
    assert evolution["job_delta"] == 2
    assert evolution["job_growth_percentage"] == 0.25
    assert evolution["growing_skill_count"] == 1
    assert evolution["disappeared_skill_count"] == 1
    assert evolution["top_growing_skills"][0]["skill_id"] == "skill-python"
    assert evolution["top_disappeared_skills"][0]["skill_id"] == "skill-legacy"
    assert store.requests == [(2024, "IT"), (2023, "IT")]
    assert fake_tracker.fetch_payloads == []


@pytest.mark.asyncio
async def test_projector_service_sectoral_snapshot_returns_not_available_without_static_data():
    fake_service, _, fake_tracker, _ = _make_projector_service([])

    result = await fake_service.sectoral_snapshot(year=2024)

    assert result["status"] == "not_available"
    assert result["year"] == 2024
    assert result["sectors"] == []
    assert "Run the snapshot refresh job" in result["message"]
    assert fake_tracker.fetch_payloads == [{
        "min_upload_date": "2024-01-01",
        "max_upload_date": "2024-12-31",
    }]


@pytest.mark.asyncio
async def test_projector_service_sectoral_snapshot_store_miss_does_not_fetch_tracker():
    store = _FakeSectorSnapshotStore(None)
    fake_service, _, fake_tracker, _ = _make_projector_service([], sector_snapshot_store=store)

    result = await fake_service.sectoral_snapshot(year=2024)

    assert result["status"] == "not_available"
    assert result["data_source"] == "postgres"
    assert fake_tracker.fetch_payloads == []


@pytest.mark.asyncio
async def test_projector_service_sector_skills_comparison_builds_matrix():
    store = _FakeSectorSnapshotStore({
        "by_year": {
            2023: {
                "status": "completed",
                "year": 2023,
                "data_source": "postgres",
                "window": {"label": "2023 snapshot", "min_date": "2023-01-01", "max_date": "2023-12-31"},
                "total_jobs": 10,
                "sector_filter": [],
                "sectors": [
                    {
                        "sector": "ICT",
                        "sector_label": "ICT",
                        "job_count": 10,
                        "job_share": 1.0,
                        "total_skill_mentions": 10,
                        "unique_skills": 1,
                        "top_skills": [{"skill_id": "skill-python", "label": "Python", "count": 2, "frequency": 0.2}],
                        "all_skills": [{"skill_id": "skill-python", "label": "Python", "count": 2, "frequency": 0.2}],
                        "top_job_titles": [],
                    }
                ],
            },
            2024: {
                "status": "completed",
                "year": 2024,
                "data_source": "postgres",
                "window": {"label": "2024 snapshot", "min_date": "2024-01-01", "max_date": "2024-12-31"},
                "total_jobs": 20,
                "sector_filter": [],
                "sectors": [
                    {
                        "sector": "ICT",
                        "sector_label": "ICT",
                        "job_count": 12,
                        "job_share": 0.6,
                        "total_skill_mentions": 20,
                        "unique_skills": 2,
                        "top_skills": [
                            {"skill_id": "skill-python", "label": "Python", "count": 6, "frequency": 0.3},
                            {"skill_id": "skill-sql", "label": "SQL", "count": 4, "frequency": 0.2},
                        ],
                        "all_skills": [
                            {"skill_id": "skill-python", "label": "Python", "count": 6, "frequency": 0.3},
                            {"skill_id": "skill-sql", "label": "SQL", "count": 4, "frequency": 0.2},
                        ],
                        "top_job_titles": [],
                    }
                ],
            },
        }
    })
    fake_service, _, fake_tracker, _ = _make_projector_service([], sector_snapshot_store=store)

    result = await fake_service.sector_skills_comparison(
        year=2024,
        reference_year=2023,
        locations=["IT"],
        sectors=["ICT"],
        skills=["skill-python"],
        metric="growth",
    )

    assert result["status"] == "completed"
    assert result["reference_year"] == 2023
    assert result["metric"] == "growth"
    assert store.requests == [(2024, "IT"), (2023, "IT")]
    assert fake_tracker.fetch_payloads == []
    assert result["sectors"] == ["ICT"]
    assert result["skills"] == ["Python"]
    cell = result["matrix"][0]
    assert cell["count"] == 6
    assert cell["share"] == 0.3
    assert cell["rank"] == 1
    assert cell["growth"] == 2.0
    assert cell["value"] == 2.0


@pytest.mark.asyncio
async def test_projector_service_emerging_skills_and_stop_status():
    fake_service, fake_engine, _, _ = _make_projector_service([])

    emerging = await fake_service.emerging_skills(
        min_date="2024-01-01",
        max_date="2024-01-31",
        keywords=["python"],
    )
    stop_result = fake_service.stop()

    assert emerging["status"] == "completed"
    assert emerging["insights"]["filters"] == {"keywords": ["python"]}
    assert stop_result == {"status": "signal_sent"}
    assert fake_engine.stop_requested is True


@pytest.mark.asyncio
async def test_engine_analyze_market_data_logic():
    """
    Verifica l'aggregazione corretta con la nuova struttura Phase 1.
    """
    mock_jobs = [
        {"organization_name": "Google", "title": "Dev", "location_code": "IT", "skills": ["s1"],
         "occupation_id": "occ_1", "sectors": ["Tech"]}
    ]
    # Prepariamo le mappe con la nuova struttura
    engine.sector_map = {"occ_1": "Tech"}
    engine.skill_map = {"s1": {"label": "Python", "is_green": False, "is_digital": True}}
    engine.stop_requested = False

    result = await market.analyze_market_data(mock_jobs)

    assert result["total_jobs"] == 1
    # Verifica campi Intelligence Phase 1
    skill_entry = result["rankings"]["skills"][0]
    assert skill_entry["name"] == "Python"
    assert skill_entry["is_digital"] is True
    assert skill_entry["sector_spread"] == 1
    assert result["rankings"]["sectors"][0]["name"] == "Tech"







@pytest.mark.asyncio
async def test_fetch_occupation_labels():
    """Verifica popolamento sector_map forzando il reset degli stati."""
    # 1. RESET TOTALE DELLO STATO
    engine.sector_map = {}
    engine.token = "fake_token"
    engine.stop_requested = False  # <--- CRUCIALE: se è True, il metodo ritorna subito!
    occ_uri = "occ_1"

    # 2. MOCKING COMPLETO
    with patch.object(engine.client, 'post', new_callable=AsyncMock) as mock_post:
        # Costruiamo l'oggetto risposta che httpx aspetta
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"id": occ_uri, "label": "Energy Sector"}]
        }
        mock_post.return_value = mock_response

        # 3. ESECUZIONE
        await tracker.fetch_occupation_labels([occ_uri])

        # 4. VERIFICA
        # Se fallisce qui, stamperà il contenuto della mappa per debuggare
        assert occ_uri in engine.sector_map, f"Mappa vuota! uris cercati erano {occ_uri}. Mappa: {engine.sector_map}"
        assert engine.sector_map[occ_uri] == "Energy Sector"


@pytest.mark.asyncio
async def test_fetch_occupation_labels_2():
    """Versione atomica: resetta tutto e forza il mock."""
    from app.core.container import engine

    # 1. Forza lo stato pulito
    engine.sector_map = {}
    engine.token = "fake_token"
    engine.stop_requested = False

    occ_uri = "occ_1"
    mock_data = {"items": [{"id": occ_uri, "label": "Energy Sector"}]}

    # 2. Mocking asincrono pulito
    with patch.object(engine.client, 'post') as mock_post:
        # Creiamo un oggetto che simula la risposta di httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data

        # Essendo una funzione async, il post deve ritornare una coroutine che risolve in mock_resp
        mock_post.return_value = mock_resp

        # 3. Esecuzione
        await tracker.fetch_occupation_labels([occ_uri])

    # 4. Diagnostica se fallisce
    assert occ_uri in engine.sector_map, f"Fallimento! Mappa attuale: {engine.sector_map}"
    assert engine.sector_map[occ_uri] == "Energy Sector"


# ==========================================
# 2. TEST DI INTEGRAZIONE (Endpoints)
# ==========================================

@pytest.mark.integration
def test_endpoint_analyze_skills_consistency():
    """Verifica che le chiavi per la Dashboard siano sempre presenti."""
    form_data = {"keywords": ["test"], "min_date": "2024-01-01", "max_date": "2024-01-02"}

    # Mockiamo le chiamate interne per velocità
    with patch.object(tracker, 'fetch_all_jobs', new_callable=AsyncMock) as m_fetch:
        m_fetch.return_value = []
        response = client.post("/projector/analyze-skills", data=form_data)

        assert response.status_code == 200
        data = response.json()
        assert "ranking" in data["insights"]
        assert "job_titles" in data["insights"]
        assert "employers" in data["insights"]
        assert "geo_breakdown" in data["dimension_summary"]


# ==========================================
# 3. RESILIENZA & UTILITY
# ==========================================

@pytest.mark.asyncio
async def test_engine_stop_signal():
    engine.request_stop()
    result = await market.analyze_market_data([{"skills": ["s1"]}] * 5)
    assert len(result["rankings"]["skills"]) == 0
    engine.stop_requested = False


def test_cache_hashing():
    f1 = {"k": "a"}
    f2 = {"k": "b"}
    h1 = hashlib.md5(json.dumps(f1, sort_keys=True).encode()).hexdigest()
    h2 = hashlib.md5(json.dumps(f2, sort_keys=True).encode()).hexdigest()
    assert h1 != h2


# ==========================================
# 4. COVERAGE BOOSTER: TRENDS & LOGIC
# ==========================================

@pytest.mark.asyncio
async def test_calculate_smart_trends_logic():
    """Testa la logica matematica dei trend (Volume e Skill Growth)."""
    # Periodo A: 1 Job con 1 Skill
    mock_jobs_a = [{"occupation_id": "occ_1", "skills": ["s1"]}]
    # Periodo B: 2 Job diversi, ognuno con la Skill (Volume raddoppiato)
    mock_jobs_b = [
        {"occupation_id": "occ_1", "skills": ["s1"]},
        {"occupation_id": "occ_1", "skills": ["s1"]}
    ]

    engine.token = "fake"
    engine.sector_map = {"occ_1": "Tech"}
    engine.skill_map = {"s1": {"label": "Python", "is_green": False, "is_digital": True}}

    with patch.object(tracker, 'fetch_all_jobs', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = [mock_jobs_a, mock_jobs_b]

        result = await trends.calculate_smart_trends({}, "2024-01-01", "2024-01-04")

        # 1. Verifica Volume (da 1 a 2 job = +100%)
        assert result["market_health"]["volume_growth_percentage"] == 100.0
        assert result["market_health"]["status"] == "expanding"

        # 2. Verifica Skill Growth (da 1 occorrenza a 2 = +100%)
        python_trend = next(t for t in result["trends"] if t["name"] == "Python")
        assert python_trend["growth"] == 100.0
        assert python_trend["trend_type"] == "emerging"


@pytest.mark.asyncio
async def test_fetch_all_jobs_read_timeout_resilience(tmp_path, monkeypatch):
    """Testa la gestione del ReadTimeout (Coverage del blocco except)."""
    monkeypatch.chdir(tmp_path)
    engine.token = "fake"
    with patch.object(engine.client, 'post', side_effect=httpx.ReadTimeout("Timeout")):
        with pytest.raises(RuntimeError, match="Checkpoint saved"):
            await tracker.fetch_all_jobs(
                {"kw": "test"},
                max_retries=1,
                retry_backoff_seconds=0,
            )


@pytest.mark.asyncio
async def test_fetch_all_jobs_retries_page_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine.token = "fake-token"
    engine.stop_requested = False

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "count": 1,
        "items": [{"id": 1, "skills": ["skill-a"], "sectors": ["Education"]}],
    }

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [httpx.ReadTimeout("Timeout"), response]
        result = await tracker.fetch_all_jobs(
            {"keywords": ["data"]},
            max_retries=2,
            retry_backoff_seconds=0,
        )

    assert result == [{"id": 1, "skills": ["skill-a"], "sectors": ["Education"]}]
    assert mock_post.await_count == 2


@pytest.mark.asyncio
async def test_fetch_all_jobs_checkpoint_resume_after_interruption(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine.token = "fake-token"
    engine.stop_requested = False

    first = MagicMock()
    first.status_code = 200
    first.json.return_value = {
        "count": 3,
        "items": [
            {"id": 1, "skills": ["skill-a"], "sectors": ["Education"]},
            {"id": 2, "skills": ["skill-b"], "sectors": ["Research"]},
        ],
    }
    second = MagicMock()
    second.status_code = 200
    second.json.return_value = {
        "count": 3,
        "items": [{"id": 3, "skills": ["skill-c"], "sectors": ["Manufacturing"]}],
    }

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [first, httpx.ReadTimeout("Timeout")]
        with pytest.raises(RuntimeError, match="page 2"):
            await tracker.fetch_all_jobs(
                {"keywords": ["data"]},
                page_size=2,
                max_retries=1,
                retry_backoff_seconds=0,
            )

    checkpoint_files = list((tmp_path / "cache_data").glob("search_*.partial.json"))
    assert len(checkpoint_files) == 1
    checkpoint = json.loads(checkpoint_files[0].read_text())
    assert checkpoint["next_page"] == 2
    assert [job["id"] for job in checkpoint["jobs"]] == [1, 2]

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = second
        result = await tracker.fetch_all_jobs(
            {"keywords": ["data"]},
            page_size=2,
            retry_backoff_seconds=0,
        )

    assert [job["id"] for job in result] == [1, 2, 3]
    assert mock_post.await_count == 1
    assert mock_post.await_args.kwargs["params"] == {"page": 2, "page_size": 2}
    assert not checkpoint_files[0].exists()


@pytest.mark.asyncio
async def test_fetch_all_jobs_rejects_empty_page_before_total(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine.token = "fake-token"
    engine.stop_requested = False

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"count": 3, "items": []}

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = response
        with pytest.raises(RuntimeError, match="empty page before completion"):
            await tracker.fetch_all_jobs(
                {"keywords": ["data"]},
                page_size=2,
                retry_backoff_seconds=0,
            )

    checkpoint_files = list((tmp_path / "cache_data").glob("search_*.partial.json"))
    assert len(checkpoint_files) == 1
    checkpoint = json.loads(checkpoint_files[0].read_text())
    assert checkpoint["jobs"] == []
    assert checkpoint["total"] == 3


@pytest.mark.asyncio
async def test_fetch_all_jobs_parallel_page_batches(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine.token = "fake-token"
    engine.stop_requested = False

    first = MagicMock()
    first.status_code = 200
    first.json.return_value = {
        "count": 4,
        "items": [
            {"id": 1, "skills": ["skill-a"], "sectors": ["Education"]},
            {"id": 2, "skills": ["skill-b"], "sectors": ["Research"]},
        ],
    }
    second = MagicMock()
    second.status_code = 200
    second.json.return_value = {
        "count": 4,
        "items": [
            {"id": 3, "skills": ["skill-c"], "sectors": ["Manufacturing"]},
            {"id": 4, "skills": ["skill-d"], "sectors": ["Technology"]},
        ],
    }

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [first, second]
        result = await tracker.fetch_all_jobs(
            {"keywords": ["data"]},
            page_size=2,
            page_concurrency=2,
            retry_backoff_seconds=0,
        )

    assert [job["id"] for job in result] == [1, 2, 3, 4]
    assert mock_post.await_count == 2
    requested_pages = [
        call.kwargs["params"]["page"]
        for call in mock_post.await_args_list
    ]
    assert requested_pages == [1, 2]


@pytest.mark.asyncio
async def test_fetch_skill_names_enriches_api_skills_and_requests_token():
    engine.skill_map = {}
    engine.token = None
    engine.stop_requested = False

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "items": [
            {"id": "skill-python", "label": "Python"},
            {"id": "skill-sql", "label": "SQL"},
        ]
    }

    async def fake_token():
        engine.token = "fresh-token"
        return engine.token

    with patch.object(tracker, "_get_token", new_callable=AsyncMock) as mock_token, \
         patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_token.side_effect = fake_token
        mock_post.return_value = response

        await tracker.fetch_skill_names(["skill-python", "skill-sql", "skill-python"])

    assert mock_token.await_count == 1
    assert mock_post.await_count == 1
    assert mock_post.await_args.kwargs["headers"] == {"Authorization": "Bearer fresh-token"}
    assert mock_post.await_args.kwargs["data"] == {
        "ids": ["skill-python", "skill-sql", "skill-python"],
        "keywords_logic": "or",
    }
    assert engine.skill_map["skill-python"] == {
        "label": "Python",
        "is_green": False,
        "is_digital": False,
    }
    assert engine.skill_map["skill-sql"]["label"] == "SQL"


@pytest.mark.asyncio
async def test_fetch_skill_names_skips_cached_and_stopped_requests():
    engine.skill_map = {"skill-python": {"label": "Python"}}
    engine.stop_requested = False

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        await tracker.fetch_skill_names(["skill-python"])
        mock_post.assert_not_awaited()

    engine.stop_requested = True
    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        await tracker.fetch_skill_names(["skill-sql"])
        mock_post.assert_not_awaited()

    engine.stop_requested = False


@pytest.mark.asyncio
async def test_fetch_all_jobs_paginates_and_writes_sector_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine.token = "fake-token"
    engine.stop_requested = False

    first = MagicMock()
    first.status_code = 200
    first.json.return_value = {
        "count": 3,
        "items": [
            {"id": 1, "skills": ["skill-a"], "sectors": ["Education"]},
            {"id": 2, "skills": ["skill-b"], "sectors": ["Research"]},
        ],
    }
    second = MagicMock()
    second.status_code = 200
    second.json.return_value = {
        "count": 3,
        "items": [{"id": 3, "skills": ["skill-c"], "sectors": ["Manufacturing"]}],
    }

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [first, second]
        result = await tracker.fetch_all_jobs({"keywords": ["data"]}, page_size=2)

    assert [job["id"] for job in result] == [1, 2, 3]
    assert mock_post.await_count == 2
    assert mock_post.await_args_list[0].kwargs["params"] == {"page": 1, "page_size": 2}
    assert mock_post.await_args_list[1].kwargs["params"] == {"page": 2, "page_size": 2}
    cache_files = list((tmp_path / "cache_data").glob("search_*.json"))
    data_cache_files = [path for path in cache_files if not path.name.endswith(".meta.json")]
    meta_cache_files = [path for path in cache_files if path.name.endswith(".meta.json")]
    assert len(data_cache_files) == 1
    assert len(meta_cache_files) == 1
    assert json.loads(data_cache_files[0].read_text()) == result
    metadata = json.loads(meta_cache_files[0].read_text())
    assert metadata["status"] == "complete"
    assert metadata["fetched"] == 3
    assert metadata["total"] == 3


@pytest.mark.asyncio
async def test_fetch_all_jobs_uses_sector_cache_and_refetches_stale_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine.token = "fake-token"
    engine.stop_requested = False

    query_sig = hashlib.md5(json.dumps({"keywords": ["data"]}, sort_keys=True).encode()).hexdigest()
    cache_dir = tmp_path / "cache_data"
    cache_dir.mkdir()
    cache_file = cache_dir / f"search_{query_sig}.json"
    cache_file.write_text(json.dumps([{"id": 1, "sectors": ["Education"]}]))

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        cached = await tracker.fetch_all_jobs({"keywords": ["data"]})
        mock_post.assert_not_awaited()
    assert cached == [{"id": 1, "sectors": ["Education"]}]

    cache_file.write_text(json.dumps([{"id": 2, "occupation_id": "old"}]))
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"count": 1, "items": [{"id": 3, "sectors": ["Research"]}]}

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = response
        refreshed = await tracker.fetch_all_jobs({"keywords": ["data"]})

    assert refreshed == [{"id": 3, "sectors": ["Research"]}]
    assert mock_post.await_count == 1


@pytest.mark.asyncio
async def test_fetch_all_jobs_requires_complete_cache_for_backfill(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine.token = "fake-token"
    engine.stop_requested = False

    query_sig = hashlib.md5(json.dumps({"keywords": ["data"]}, sort_keys=True).encode()).hexdigest()
    cache_dir = tmp_path / "cache_data"
    cache_dir.mkdir()
    cache_file = cache_dir / f"search_{query_sig}.json"
    cache_file.write_text(json.dumps([{"id": 1, "sectors": ["Education"]}]))

    probe = MagicMock()
    probe.status_code = 200
    probe.json.return_value = {"count": 3, "items": [{"id": 1, "sectors": ["Education"]}]}
    first = MagicMock()
    first.status_code = 200
    first.json.return_value = {
        "count": 3,
        "items": [
            {"id": 1, "sectors": ["Education"]},
            {"id": 2, "sectors": ["Research"]},
        ],
    }
    second = MagicMock()
    second.status_code = 200
    second.json.return_value = {"count": 3, "items": [{"id": 3, "sectors": ["Manufacturing"]}]}

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [probe, first, second]
        result = await tracker.fetch_all_jobs(
            {"keywords": ["data"]},
            page_size=2,
            retry_backoff_seconds=0,
            require_complete_cache=True,
        )

    assert [job["id"] for job in result] == [1, 2, 3]
    assert mock_post.await_count == 3
    assert mock_post.await_args_list[0].kwargs["params"] == {"page": 1, "page_size": 1}
    metadata = json.loads((cache_dir / f"search_{query_sig}.meta.json").read_text())
    assert metadata["status"] == "complete"
    assert metadata["fetched"] == 3
    assert metadata["total"] == 3


@pytest.mark.asyncio
async def test_fetch_all_jobs_refreshes_when_complete_cache_count_changed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine.token = "fake-token"
    engine.stop_requested = False

    filters = {"keywords": ["data"]}
    query_sig = hashlib.md5(json.dumps(filters, sort_keys=True).encode()).hexdigest()
    cache_dir = tmp_path / "cache_data"
    cache_dir.mkdir()
    cache_file = cache_dir / f"search_{query_sig}.json"
    meta_file = cache_dir / f"search_{query_sig}.meta.json"
    cache_file.write_text(json.dumps([
        {"id": 1, "sectors": ["Education"]},
        {"id": 2, "sectors": ["Research"]},
    ]))
    meta_file.write_text(json.dumps({
        "filters": filters,
        "page_size": 2,
        "fetched": 2,
        "total": 2,
        "status": "complete",
    }))

    probe = MagicMock()
    probe.status_code = 200
    probe.json.return_value = {"count": 3, "items": [{"id": 1, "sectors": ["Education"]}]}
    first = MagicMock()
    first.status_code = 200
    first.json.return_value = {
        "count": 3,
        "items": [
            {"id": 1, "sectors": ["Education"]},
            {"id": 2, "sectors": ["Research"]},
        ],
    }
    second = MagicMock()
    second.status_code = 200
    second.json.return_value = {"count": 3, "items": [{"id": 3, "sectors": ["Manufacturing"]}]}

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [probe, first, second]
        result = await tracker.fetch_all_jobs(
            filters,
            page_size=2,
            retry_backoff_seconds=0,
            require_complete_cache=True,
        )

    assert [job["id"] for job in result] == [1, 2, 3]
    assert mock_post.await_count == 3
    metadata = json.loads(meta_file.read_text())
    assert metadata["status"] == "complete"
    assert metadata["fetched"] == 3
    assert metadata["total"] == 3


@pytest.mark.asyncio
async def test_fetch_all_jobs_uses_complete_cache_when_api_count_matches(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine.token = "fake-token"
    engine.stop_requested = False

    filters = {"keywords": ["data"]}
    query_sig = hashlib.md5(json.dumps(filters, sort_keys=True).encode()).hexdigest()
    cache_dir = tmp_path / "cache_data"
    cache_dir.mkdir()
    cache_file = cache_dir / f"search_{query_sig}.json"
    meta_file = cache_dir / f"search_{query_sig}.meta.json"
    cached_jobs = [
        {"id": 1, "sectors": ["Education"]},
        {"id": 2, "sectors": ["Research"]},
    ]
    cache_file.write_text(json.dumps(cached_jobs))
    meta_file.write_text(json.dumps({
        "filters": filters,
        "page_size": 2,
        "fetched": 2,
        "total": 2,
        "status": "complete",
    }))

    probe = MagicMock()
    probe.status_code = 200
    probe.json.return_value = {"count": 2, "items": [{"id": 1, "sectors": ["Education"]}]}

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = probe
        result = await tracker.fetch_all_jobs(
            filters,
            page_size=2,
            retry_backoff_seconds=0,
            require_complete_cache=True,
        )

    assert result == cached_jobs
    assert mock_post.await_count == 1
    assert mock_post.await_args.kwargs["params"] == {"page": 1, "page_size": 1}


@pytest.mark.asyncio
async def test_analyze_market_data_empty_jobs():
    """Testa il metodo _empty_res (Coverage dei rami edge)."""
    result = await market.analyze_market_data([])
    assert result["total_jobs"] == 0
    assert result["rankings"]["skills"] == []


@pytest.mark.asyncio
async def test_analyze_market_data_unclassified_sector():
    """Verifica il fallback 'Settore non specificato' se manca occupation_id."""
    mock_jobs = [{"skills": ["s1"]}]  # Manca occupation_id
    engine.skill_map = {"s1": {"label": "Test", "is_green": False, "is_digital": False, "sectors": "[]"}}
    engine.sector_map = {}

    result = await market.analyze_market_data(mock_jobs)
    assert result["rankings"]["sectors"][0]['name'] == "Sector not specified"

# ==========================================
# 5. INTEGRATION: ENDPOINT EMERGING SKILLS
# ==========================================

@pytest.mark.integration
def test_endpoint_emerging_skills_structure():
    """Verifica la struttura JSON dell'endpoint trend."""
    with patch.object(tracker, 'fetch_all_jobs', new_callable=AsyncMock) as m_fetch:
        m_fetch.return_value = []
        response = client.post("/projector/emerging-skills", data={
            "min_date": "2024-01-01", "max_date": "2024-01-31"
        })
        assert response.status_code == 200
        assert "market_health" in response.json()["insights"]


import csv
from pathlib import Path

# ==========================================
# 1.b TWIN TRANSITION CSV LOOKUP
# ==========================================

def test_load_skill_uris_from_csv_reads_concept_uri(tmp_path):
    """
    Verifica che il loader legga correttamente la colonna conceptUri
    e costruisca il set degli URI.
    """
    csv_file = tmp_path / "green_skills.csv"
    csv_file.write_text(
        "conceptType,conceptUri,preferredLabel\n"
        "KnowledgeSkillCompetence,http://data.europa.eu/esco/skill/g1,green skill one\n"
        "KnowledgeSkillCompetence,http://data.europa.eu/esco/skill/g2,green skill two\n",
        encoding="utf-8"
    )

    uris = loader._load_skill_uris_from_csv(str(csv_file))

    assert uris == {
        "http://data.europa.eu/esco/skill/g1",
        "http://data.europa.eu/esco/skill/g2",
    }


def test_load_skill_uris_from_csv_missing_file_returns_empty_set():
    """
    Se il CSV non esiste, il loader deve restituire un set vuoto.
    """
    uris = loader._load_skill_uris_from_csv("path/that/does/not/exist.csv")
    assert uris == set()


def test_load_skill_uris_from_csv_ignores_empty_concept_uri(tmp_path):
    """
    Le righe senza conceptUri valido devono essere ignorate.
    """
    csv_file = tmp_path / "digital_skills.csv"
    csv_file.write_text(
        "conceptType,conceptUri,preferredLabel\n"
        "KnowledgeSkillCompetence,,missing uri\n"
        "KnowledgeSkillCompetence,http://data.europa.eu/esco/skill/d1,digital skill one\n",
        encoding="utf-8"
    )

    uris = loader._load_skill_uris_from_csv(str(csv_file))

    assert uris == {"http://data.europa.eu/esco/skill/d1"}


@pytest.mark.asyncio
@pytest.mark.skip("Green and Digital Skill Not Implemented")
async def test_fetch_skill_names_uses_csv_lookup_green_only():
    """
    Verifica che fetch_skill_names assegni i flag usando gli URI caricati dal CSV:
    skill presente solo nel set green.
    """
    engine.skill_map = {}
    engine.token = "fake_token"
    engine.stop_requested = False

    engine.green_skill_uris = {"http://data.europa.eu/esco/skill/s1"}
    engine.digital_skill_uris = set()

    target_uri = "http://data.europa.eu/esco/skill/s1"

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"id": target_uri, "label": "Some label not used for tagging"}]
        }
        mock_post.return_value = mock_response

        await tracker.fetch_skill_names([target_uri])

        assert target_uri in engine.skill_map
        entry = engine.skill_map[target_uri]
        assert entry["label"] == "Some label not used for tagging"
        assert entry["is_green"] is True
        assert entry["is_digital"] is False


@pytest.mark.asyncio
@pytest.mark.skip("Green and Digital Skill Not Implemented")
async def test_fetch_skill_names_uses_csv_lookup_digital_only():
    """
    Skill presente solo nel set digital.
    """
    engine.skill_map = {}
    engine.token = "fake_token"
    engine.stop_requested = False

    engine.green_skill_uris = set()
    engine.digital_skill_uris = {"http://data.europa.eu/esco/skill/s2"}

    target_uri = "http://data.europa.eu/esco/skill/s2"

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"id": target_uri, "label": "Another label"}]
        }
        mock_post.return_value = mock_response

        await tracker.fetch_skill_names([target_uri])

        entry = engine.skill_map[target_uri]
        assert entry["is_green"] is False
        assert entry["is_digital"] is True


@pytest.mark.asyncio
@pytest.mark.skip("Green and Digital Skill Not Implemented")
async def test_fetch_skill_names_uses_csv_lookup_both_green_and_digital():
    """
    Skill presente in entrambi i set.
    """
    engine.skill_map = {}
    engine.token = "fake_token"
    engine.stop_requested = False

    target_uri = "http://data.europa.eu/esco/skill/s3"
    engine.green_skill_uris = {target_uri}
    engine.digital_skill_uris = {target_uri}

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"id": target_uri, "label": "Hybrid skill"}]
        }
        mock_post.return_value = mock_response

        await tracker.fetch_skill_names([target_uri])

        entry = engine.skill_map[target_uri]
        assert entry["is_green"] is True
        assert entry["is_digital"] is True


@pytest.mark.asyncio
@pytest.mark.skip("Green and Digital Skill Not Implemented")
async def test_fetch_skill_names_returns_false_false_when_uri_not_in_any_csv():
    """
    Se l'URI non è presente né nel CSV green né in quello digital,
    i flag devono andare a False/False.
    """
    engine.skill_map = {}
    engine.token = "fake_token"
    engine.stop_requested = False

    engine.green_skill_uris = set()
    engine.digital_skill_uris = set()

    target_uri = "http://data.europa.eu/esco/skill/s4"

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"id": target_uri, "label": "Unclassified skill"}]
        }
        mock_post.return_value = mock_response

        await tracker.fetch_skill_names([target_uri])

        entry = engine.skill_map[target_uri]
        assert entry["is_green"] is False
        assert entry["is_digital"] is False


@pytest.mark.asyncio
async def test_fetch_skill_names_does_not_requery_already_cached_skill():
    """
    Se una skill è già in skill_map, non deve essere richiesta di nuovo.
    """
    target_uri = "http://data.europa.eu/esco/skill/s5"

    engine.skill_map = {
        target_uri: {
            "label": "Already cached",
            "is_green": False,
            "is_digital": True,
        }
    }
    engine.token = "fake_token"
    engine.stop_requested = False
    engine.green_skill_uris = set()
    engine.digital_skill_uris = {target_uri}

    with patch.object(engine.client, "post", new_callable=AsyncMock) as mock_post:
        await tracker.fetch_skill_names([target_uri])

        mock_post.assert_not_called()
        assert engine.skill_map[target_uri]["label"] == "Already cached"


@pytest.mark.asyncio
async def test_engine_analyze_market_data_logic_with_csv_based_tags():
    """
    Verifica end-to-end che analyze_market_data propaghi correttamente
    i flag derivati dal lookup CSV.
    """
    mock_jobs = [
        {
            "organization_name": "Google",
            "title": "Dev",
            "location_code": "IT",
            "skills": ["http://data.europa.eu/esco/skill/s1"],
            "occupation_id": "occ_1",
        }
    ]

    engine.sector_map = {"occ_1": "Tech"}
    engine.skill_map = {
        "http://data.europa.eu/esco/skill/s1": {
            "label": "Python",
            "is_green": False,
            "is_digital": True,
        }
    }
    engine.stop_requested = False

    result = await market.analyze_market_data(mock_jobs)

    skill_entry = result["rankings"]["skills"][0]
    assert skill_entry["name"] == "Python"
    assert skill_entry["is_green"] is False
    assert skill_entry["is_digital"] is True

@pytest.mark.asyncio
@pytest.mark.skip
async def test_fetch_skill_names_enriched_logic():
    """Verifica che il tagging riconosca parole tecniche come 'renewable'."""
    engine.skill_map = {}
    engine.token = "fake_token"

    with patch.object(engine.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"id": "s1", "label": "Renewable energy systems installation"}]
        }
        mock_post.return_value = mock_response

        await tracker.fetch_skill_names(["s1"])

        entry = engine.skill_map["s1"]
        # Ora deve essere True perché 'renewable' e 'energy' sono nel set Green
        assert entry["is_green"] is True
        assert entry["label"] == "Renewable energy systems installation"


@pytest.mark.asyncio
async def test_calculate_smart_trends_intelligence_overlap():
    """Verifica che il settore primario sia presente nei risultati dei trend."""
    # Mock jobs con settori specifici
    mock_jobs_a = [{"occupation_id": "occ_1", "skills": ["s1"], "sectors": ["Automotive"]}]
    mock_jobs_b = [{"occupation_id": "occ_1", "skills": ["s1"], "sectors": ["Automotive"], "organization_name": "Test"}]

    engine.token = "fake"
    engine.skill_map = {"s1": {"label": "Battery Tech", "is_green": True, "is_digital": False}}

    with patch.object(tracker, 'fetch_all_jobs', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = [mock_jobs_a, mock_jobs_b]

        result = await trends.calculate_smart_trends({}, "2024-01-01", "2024-01-04")

        # Verifica che il trend contenga il settore automotive
        skill_trend = result["trends"][0]
        assert skill_trend["primary_sector"] == "Automotive"
        assert skill_trend["is_green"] is True


@pytest.mark.integration
def test_dashboard_phase1_contract():
    """
    TEST: Verifica che l'output per la Dashboard contenga
    i dati di Intelligence e la distribuzione settoriale.
    """
    form_data = {"keywords": ["data scientist"], "min_date": "2024-01-01", "max_date": "2024-01-02"}

    with patch.object(tracker, 'fetch_all_jobs', new_callable=AsyncMock) as m_fetch:
        # New sector model: sectors arrive directly from the Tracker job payload.
        m_fetch.return_value = [{"skills": ["s1"], "sectors": ["Information Technology"]}]
        engine.skill_map = {"s1": {"label": "AI", "is_green": False, "is_digital": True}}

        response = client.post("/projector/analyze-skills", data=form_data)
        res_data = response.json()

        # Verifica campi per Tabella Skill (Tab 1)
        skill_sample = res_data["insights"]["ranking"][0]
        assert "is_green" in skill_sample
        assert "is_digital" in skill_sample
        assert "sector_spread" in skill_sample
        assert skill_sample["sector_spread"] == 1
        assert skill_sample["primary_sector"] == "Information Technology"

        # Verifica dati per Grafico Settori (Nuova Tab 4)
        assert "sectors" in res_data["insights"]
        assert res_data["insights"]["sectors"][0]["name"] == "Information Technology"


@pytest.mark.integration
def test_endpoint_analyze_skills_single_fetch_consistency():
    """Verifica che l'endpoint restituisca sia le skill che i trend in un'unica chiamata."""
    form_data = {
        "keywords": ["developer"],
        "min_date": "2024-01-01",
        "max_date": "2024-01-10"
    }

    # Mocking per evitare fetch reali
    with patch.object(tracker, 'fetch_all_jobs', new_callable=AsyncMock) as m_fetch:
        m_fetch.return_value = [
            {"upload_date": "2024-01-02", "skills": ["s1"], "occupation_id": "occ_1"},
            {"upload_date": "2024-01-08", "skills": ["s1", "s1"], "occupation_id": "occ_1"}
        ]

        response = client.post("/projector/analyze-skills", data=form_data)
        assert response.status_code == 200

        data = response.json()
        # Verifica che i trend siano "dentro" la risposta di analyze-skills
        assert "trends" in data["insights"]
        assert data["insights"]["trends"]["market_health"]["volume_growth_percentage"] == 0.0


import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_fetch_occupation_labels_specific_esco():
    """
    Verifica che l'ID ESCO del Sales Account Manager venga
    correttamente tradotto e salvato nella sector_map.
    """
    target_uri = "http://data.europa.eu/esco/occupation/2eac08c2-a81a-46fc-8d75-eb0e0f3e0f6d"
    expected_label = "sales account manager"

    engine.sector_map = {}
    engine.token = "fake_token"
    engine.stop_requested = False

    mock_response_data = {"items": [{"id": target_uri, "label": expected_label}]}

    with patch.object(engine.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = mock_response_data
        mock_post.return_value = mock_res

        await tracker.fetch_occupation_labels([target_uri])

        assert mock_post.called
        args, kwargs = mock_post.call_args
        # FIX: Cerchiamo 'json' invece di 'data' perché siamo passati a JSON in produzione
        assert target_uri in kwargs['data']['ids']
        assert engine.sector_map[target_uri] == expected_label


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Skipping test in CI environment"
)
async def test_fetch_occupation_labels_integration_real():
    load_dotenv()
    if not os.getenv("TRACKER_API") or not os.getenv("TRACKER_USERNAME") or not os.getenv("TRACKER_PASSWORD"):
        pytest.skip("Real Tracker integration requires TRACKER_* environment variables")
    """
    INTEGRATION TEST (No Mock):
    Verifica il recupero reale dal server Tracker per l'ID ESCO specifico.
    """
    target_uri = "http://data.europa.eu/esco/occupation/2eac08c2-a81a-46fc-8d75-eb0e0f3e0f6d"
    expected_label = "sales account manager"

    # RESET TOTALE: Questo impedisce ai mock precedenti di rompere il test reale
    engine.sector_map = {}
    engine.token = None  # <--- CRUCIALE: forza l'engine a fare un login vero
    engine.stop_requested = False

    # Esecuzione
    await tracker.fetch_occupation_labels([target_uri])

    # Verifica
    assert target_uri in engine.sector_map, "La mappa è vuota! Il login o la richiesta sono falliti."

    actual_label = engine.sector_map[target_uri].lower()
    assert actual_label == expected_label, f"Ricevuto '{actual_label}' invece di '{expected_label}'"


@pytest.mark.asyncio
async def test_regional_decomposition_logic():
    """
    Verifica che i job siano raggruppati correttamente sia nella
    strategia RAW che in quella NUTS gerarchica.
    """
    # Mock jobs con codici che simulano NUTS (ITC4C è NUTS3, ITC4 è NUTS2, ITC è NUTS1)
    mock_jobs = [
        {"location_code": "ITC4C", "skills": ["s1", "s2"]}, # Milano (NUTS3)
        {"location_code": "ITC4C", "skills": ["s1"]},      # Milano (NUTS3)
        {"location_code": "SOUTH", "skills": ["s2"]}       # Codice non NUTS (Raw)
    ]

    # Prepariamo la skill_map minima
    engine.skill_map = {
        "s1": {"label": "Python"},
        "s2": {"label": "SQL"}
    }

    # Esecuzione della nuova funzione duale
    results = regional.get_regional_projections(mock_jobs)

    # 1. VERIFICA STRATEGIA RAW (NORTH/SOUTH o codici completi)
    raw_results = results["raw"]

    # Check ITC4C (Raw)
    milano = next(r for r in raw_results if r["code"] == "ITC4C")
    assert milano["total_jobs"] == 2
    # Verifichiamo Python (s1) in ITC4C
    python_entry = next(s for s in milano["top_skills"] if s["skill"] == "Python")
    assert python_entry["count"] == 2

    # Check SOUTH (Raw)
    south = next(r for r in raw_results if r["code"] == "SOUTH")
    assert south["total_jobs"] == 1
    assert south["top_skills"][0]["skill"] == "SQL"

    # 2. VERIFICA STRATEGIA NUTS (Gerarchica)
    # ITC4C deve aver popolato anche NUTS2 (ITC4) e NUTS1 (ITC)

    # Check NUTS2 (Regione: ITC4 - Lombardia)
    nuts2_results = results["nuts2"]
    lombardia = next(r for r in nuts2_results if r["code"] == "ITC4")
    assert lombardia["total_jobs"] == 2

    # Check NUTS1 (Area: ITC - Nord-Ovest)
    nuts1_results = results["nuts1"]
    nord_ovest = next(r for r in nuts1_results if r["code"] == "ITC")
    assert nord_ovest["total_jobs"] == 2

    # 3. VERIFICA SPECIALIZZAZIONE (Location Quotient)
    # In questo mock, SQL compare 2 volte su 3 job totali (66%).
    # A SOUTH compare 1 volta su 1 job (100%).
    # LQ = 100% / 66% = ~1.5 (Specializzazione alta)
    sql_south = next(s for s in south["top_skills"] if s["skill"] == "SQL")
    assert sql_south["specialization"] >= 1.0

    # ==========================================
    # 6. LOCAL ESCO SUPPORT LOADING
    # ==========================================

def test_load_local_esco_support_populates_maps(monkeypatch, tmp_path):
    """
    Verifica che il loader locale popoli correttamente:
    - occupation_meta
    - skill_hierarchy
    - occ_skill_relations
    - occupation_group_labels
    """
    from app.core.container import ProjectorEngine

    # --- 1. Creo la cartella corretta ---
    data_dir = tmp_path / "complementary_data"
    data_dir.mkdir()

    # --- 2. Creo file CSV minimi di test ---
    occupations_file = data_dir / "occupations_en.csv"
    occupations_file.write_text(
        "conceptUri,preferredLabel,iscoGroup,naceCode\n"
        "occ_1,Software developer,isco_2512,J62\n"
        "occ_2,Data analyst,isco_2421,J62\n",
        encoding="utf-8"
    )

    skills_hierarchy_file = data_dir / "skillsHierarchy_en.csv"
    skills_hierarchy_file.write_text(
        "conceptUri,ESCO Level 1,ESCO Level 2,ESCO Level 3\n"
        "skill_1,S5,S5.1,S5.1.1\n"
        "skill_2,S2,S2.3,S2.3.4\n",
        encoding="utf-8"
    )

    occ_skill_rel_file = data_dir / "occupationSkillRelations_en.csv"
    occ_skill_rel_file.write_text(
        "occupationUri,skillUri\n"
        "occ_1,skill_1\n"
        "occ_1,skill_2\n"
        "occ_2,skill_2\n",
        encoding="utf-8"
    )

    isco_groups_file = data_dir / "ISCOGroups_en.csv"
    isco_groups_file.write_text(
        "conceptUri,preferredLabel\n"
        "isco_2512,Software developers\n"
        "isco_2421,Business professionals\n",
        encoding="utf-8"
    )

    monkeypatch.chdir(tmp_path)

    engine = ProjectorEngine()
    loader = EscoLoader(engine)
    engine.occupation_meta = {}
    engine.skill_hierarchy = {}
    engine.occ_skill_relations = defaultdict(set)
    engine.occupation_group_labels = {}
    engine.matrix_profiles = {}

    loader.load_local_esco_support()

    assert "occ_1" in engine.occupation_meta
    assert engine.occupation_meta["occ_1"]["label"] == "Software developer"
    assert engine.occupation_meta["occ_1"]["isco_group"] == "isco_2512"
    assert engine.occupation_meta["occ_1"]["nace_code"] == "J62"

    assert "occ_2" in engine.occupation_meta
    assert engine.occupation_meta["occ_2"]["label"] == "Data analyst"

    assert "skill_1" in engine.skill_hierarchy
    assert engine.skill_hierarchy["skill_1"]["level_1"] == "S5"
    assert engine.skill_hierarchy["skill_1"]["level_2"] == "S5.1"
    assert engine.skill_hierarchy["skill_1"]["level_3"] == "S5.1.1"

    assert "skill_2" in engine.skill_hierarchy
    assert engine.skill_hierarchy["skill_2"]["level_1"] == "S2"

    assert "occ_1" in engine.occ_skill_relations
    assert engine.occ_skill_relations["occ_1"] == {"skill_1", "skill_2"}

    assert "occ_2" in engine.occ_skill_relations
    assert engine.occ_skill_relations["occ_2"] == {"skill_2"}

    assert engine.occupation_group_labels["isco_2512"] == "Software developers"
    assert engine.occupation_group_labels["isco_2421"] == "Business professionals"

def test_load_local_esco_support_missing_files_is_safe(monkeypatch, tmp_path):
    """
    Verifica che il loader non fallisca se i CSV non esistono.
    """
    from app.core.container import ProjectorEngine

    monkeypatch.chdir(tmp_path)

    engine = ProjectorEngine()
    loader = EscoLoader(engine)
    engine.occupation_meta = {}
    engine.skill_hierarchy = {}
    engine.occ_skill_relations = defaultdict(set)
    engine.occupation_group_labels = {}
    engine.matrix_profiles = {}

    # Non deve alzare eccezioni
    loader.load_local_esco_support()

    assert engine.occupation_meta == {}
    assert engine.skill_hierarchy == {}
    assert dict(engine.occ_skill_relations) == {}
    assert engine.occupation_group_labels == {}

def test_load_local_esco_support_ignores_incomplete_rows(monkeypatch, tmp_path):
    """
    Verifica che righe incomplete o senza ID vengano ignorate.
    """
    from app.core.container import ProjectorEngine

    data_dir = tmp_path / "complementary_data"
    data_dir.mkdir()

    occupations_file = data_dir / "occupations_en.csv"
    occupations_file.write_text(
        "conceptUri,preferredLabel,iscoGroup,naceCode\n"
        ",Missing ID,isco_x,J00\n"
        "occ_valid,Valid occupation,isco_ok,J62\n",
        encoding="utf-8"
    )

    skills_hierarchy_file = data_dir / "skillsHierarchy_en.csv"
    skills_hierarchy_file.write_text(
        "conceptUri,ESCO Level 1,ESCO Level 2,ESCO Level 3\n"
        ",S1,S1.1,S1.1.1\n"
        "skill_valid,S2,S2.1,S2.1.1\n",
        encoding="utf-8"
    )

    occ_skill_rel_file = data_dir / "occupationSkillRelations_en.csv"
    occ_skill_rel_file.write_text(
        "occupationUri,skillUri\n"
        ",skill_x\n"
        "occ_valid,\n"
        "occ_valid,skill_valid\n",
        encoding="utf-8"
    )

    monkeypatch.chdir(tmp_path)

    engine = ProjectorEngine()
    loader = EscoLoader(engine)
    engine.occupation_meta = {}
    engine.skill_hierarchy = {}
    engine.occ_skill_relations = defaultdict(set)
    engine.occupation_group_labels = {}
    engine.matrix_profiles = {}

    loader.load_local_esco_support()

    assert list(engine.occupation_meta.keys()) == ["occ_valid"]
    assert list(engine.skill_hierarchy.keys()) == ["skill_valid"]
    assert engine.occ_skill_relations["occ_valid"] == {"skill_valid"}

def test_load_local_esco_support_accepts_alternative_column_names(monkeypatch, tmp_path):
    """
    Verifica i fallback sui nomi colonna alternativi previsti nel loader.
    """
    from app.core.container import ProjectorEngine

    data_dir = tmp_path / "complementary_data"
    data_dir.mkdir()

    occupations_file = data_dir / "occupations_en.csv"
    occupations_file.write_text(
        "id,label,iscoGroup,naceCode\n"
        "occ_alt,Alt occupation,isco_alt,J63\n",
        encoding="utf-8"
    )

    skills_hierarchy_file = data_dir / "skillsHierarchy_en.csv"
    skills_hierarchy_file.write_text(
        "id,level1,level2,level3\n"
        "skill_alt,S9,S9.1,S9.1.1\n",
        encoding="utf-8"
    )

    occ_skill_rel_file = data_dir / "occupationSkillRelations_en.csv"
    occ_skill_rel_file.write_text(
        "occupation,skill\n"
        "occ_alt,skill_alt\n",
        encoding="utf-8"
    )

    isco_groups_file = data_dir / "ISCOGroups_en.csv"
    isco_groups_file.write_text(
        "id,label\n"
        "isco_alt,Alt group label\n",
        encoding="utf-8"
    )

    monkeypatch.chdir(tmp_path)

    engine = ProjectorEngine()
    loader = EscoLoader(engine)
    engine.occupation_meta = {}
    engine.skill_hierarchy = {}
    engine.occ_skill_relations = defaultdict(set)
    engine.occupation_group_labels = {}
    engine.matrix_profiles = {}

    loader.load_local_esco_support()

    assert engine.occupation_meta["occ_alt"]["label"] == "Alt occupation"
    assert engine.skill_hierarchy["skill_alt"]["level_1"] == "S9"
    assert engine.occ_skill_relations["occ_alt"] == {"skill_alt"}
    assert engine.occupation_group_labels["isco_alt"] == "Alt group label"

# ==========================================
# 7. OCCUPATION -> SECTOR RESOLUTION
# ==========================================

def test_get_primary_occupation_id_prefers_occupations_list():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)

    job = {
        "occupations": ["occ_new"],
        "occupation_id": "occ_old"
    }

    assert occupations.get_primary_occupation_id(job) == "occ_new"


def test_get_primary_occupation_id_falls_back_to_legacy_field():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)

    job = {
        "occupation_id": "occ_legacy"
    }

    assert occupations.get_primary_occupation_id(job) == "occ_legacy"


def test_get_primary_occupation_id_returns_empty_string_when_missing():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)

    job = {"title": "No occupation"}

    assert occupations.get_primary_occupation_id(job) == ""


def test_get_sector_from_occupation_uses_local_isco_group_label():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Software developer",
            "isco_group": "isco_2512",
            "nace_code": "J62"
        }
    }
    engine.occupation_group_labels = {
        "isco_2512": "Software developers"
    }
    engine.sector_map = {}

    result = occupations.get_sector_from_occupation("occ_1", level="isco_group")
    assert result == "Software developers"


def test_get_sector_from_occupation_falls_back_to_isco_group_code():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Software developer",
            "isco_group": "isco_2512",
            "nace_code": "J62"
        }
    }
    engine.occupation_group_labels = {}
    engine.sector_map = {}

    result = occupations.get_sector_from_occupation("occ_1", level="isco_group")
    assert result == "isco_2512"


def test_get_sector_from_occupation_can_return_label():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Software developer",
            "isco_group": "isco_2512",
            "nace_code": "J62"
        }
    }
    engine.occupation_group_labels = {}
    engine.sector_map = {}

    result = occupations.get_sector_from_occupation("occ_1", level="label")
    assert result == "Software developer"


def test_get_sector_from_occupation_can_return_nace_code():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Software developer",
            "isco_group": "isco_2512",
            "nace_code": "http://data.europa.eu/ux2/nace2.1/6201"
        }
    }
    engine.occupation_group_labels = {}
    engine.sector_map = {}

    result = occupations.get_sector_from_occupation("occ_1", level="nace_code")
    assert result == "62.01"


def test_get_sector_from_occupation_can_return_nace_hierarchy_levels():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Food processor",
            "isco_group": "isco_8160",
            "nace_code": "http://data.europa.eu/ux2/nace2.1/1011"
        }
    }
    engine.occupation_group_labels = {}
    engine.sector_map = {}

    assert occupations.get_sector_from_occupation("occ_1", level="nace_section") == "C"
    assert occupations.get_sector_from_occupation("occ_1", level="nace_division") == "10"
    assert occupations.get_sector_from_occupation("occ_1", level="nace_group") == "10.1"
    assert occupations.get_sector_from_occupation("occ_1", level="nace_class") == "10.11"


def test_get_sector_from_occupation_nace_hierarchy_falls_back_when_code_is_short():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Software developer",
            "isco_group": "isco_2512",
            "nace_code": "6201"
        }
    }
    engine.occupation_group_labels = {}
    engine.sector_map = {}

    assert occupations.get_sector_from_occupation("occ_1", level="nace_section") == "J"
    assert occupations.get_sector_from_occupation("occ_1", level="nace_division") == "62"
    assert occupations.get_sector_from_occupation("occ_1", level="nace_group") == "62.0"
    assert occupations.get_sector_from_occupation("occ_1", level="nace_class") == "62.01"


def test_normalize_nace_code_supports_uri_and_numeric_shapes():
    from app.core.container import ProjectorEngine

    occupations = OccupationAnalytics(ProjectorEngine())

    assert occupations.normalize_nace_code("http://data.europa.eu/ux2/nace2.1/9031") == "90.31"
    assert occupations.normalize_nace_code("242") == "24.2"
    assert occupations.normalize_nace_code("01") == "01"
    assert occupations.normalize_nace_code("A") == "A"


def test_get_nace_mappings_from_job_reads_tracker_sectors_field():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)

    job = {
        "sectors": [
            {"code": "http://data.europa.eu/ux2/nace2.1/6201", "label": "Computer programming activities"},
            {"naceCode": "J63.1", "naceLabel": "Data processing, hosting and related activities"},
            "M70.22",
        ]
    }

    assert occupations.get_sector_keys_from_job(job, level="nace_section") == ["J", "M"]
    assert occupations.get_sector_keys_from_job(job, level="nace_division") == ["62", "63", "70"]
    assert occupations.get_sector_keys_from_job(job, level="nace_class") == ["62.01", "63.1", "70.22"]


def test_get_sector_label_uses_nace_dictionary_in_nace_mode():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.nace_labels = {"10.11": "Processing and preserving of meat, except of poultry meat"}
    engine.occupation_group_labels = {"10.11": "THIS MUST NOT BE USED"}

    assert occupations.get_sector_label("10.11", system="nace") == "Processing and preserving of meat, except of poultry meat"


def test_get_sector_label_nace_missing_falls_back_to_normalized_code_not_isco():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.nace_labels = {}
    engine.occupation_group_labels = {"90.31": "ISCO label that must be ignored"}

    assert occupations.get_sector_label("http://data.europa.eu/ux2/nace2.1/9031", system="nace") == "90.31"


def test_get_sector_label_uses_official_nace_section_lookup():
    from app.core.container import ProjectorEngine

    occupations = OccupationAnalytics(ProjectorEngine())
    assert occupations.get_sector_label("J", system="nace") == "Information and communication"


def test_nace_section_derivation_follows_official_division_ranges():
    from app.core.container import ProjectorEngine

    occupations = OccupationAnalytics(ProjectorEngine())

    assert occupations.get_sector_from_occupation("occ_missing", level="nace_section") == "Sector not specified"
    assert occupations._get_nace_level_code("01", "nace_section") == "A"
    assert occupations._get_nace_level_code("35", "nace_section") == "D"
    assert occupations._get_nace_level_code("62.01", "nace_section") == "J"
    assert occupations._get_nace_level_code("99", "nace_section") == "U"


def test_loader_crosswalk_supports_one_to_many_occupation_nace_mapping():
    openpyxl = pytest.importorskip("openpyxl")
    from app.core.container import ProjectorEngine

    with tempfile.TemporaryDirectory() as tmpdir:
        comp_dir = os.path.join(tmpdir, "complementary_data")
        os.makedirs(comp_dir, exist_ok=True)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["ESCO URI", "NACE code", "NACE title"])
        ws.append(["occ_1", "J62", "Computer programming, consultancy and related activities"])
        ws.append(["occ_1", "J59.11", "Motion picture, video and television programme production activities"])
        ws.append(["occ_1", "J62", "Computer programming, consultancy and related activities"])  # duplicate
        wb.save(os.path.join(comp_dir, "ESCO-NACE rev. 2.1 crosswalk (1).xlsx"))

        engine = ProjectorEngine()
        local_loader = EscoLoader(engine)
        prev_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            local_loader.load_esco_nace_crosswalk()
        finally:
            os.chdir(prev_cwd)

    assert "occ_1" in engine.occupation_nace_map
    mapped_codes = sorted(item["code"] for item in engine.occupation_nace_map["occ_1"])
    assert mapped_codes == ["59.11", "62"]


def test_nace_mode_never_returns_isco_label_when_crosswalk_label_missing():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_group_labels = {"J62": "ISCO label"}
    engine.nace_labels = {}

    assert occupations.get_sector_label("J62", system="nace") == "J62"


def test_compute_skill_breadth_and_concentration_returns_expected_shape():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter, {
        "S1": Counter({"skill_a": 3, "skill_b": 1}),
        "S2": Counter({"skill_a": 1}),
    })

    out = sectoral.compute_skill_breadth_and_concentration()
    assert out["skill_a"]["sector_breadth"] == 2
    assert out["skill_a"]["dominant_sector"] == "S1"
    assert out["skill_a"]["dominant_share"] == 0.75
    assert out["skill_a"]["top_sectors"][0]["sector"] == "S1"


def test_compute_sector_skill_dominance_uses_top_k_share():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter, {
        "S1": Counter({"a": 5, "b": 3, "c": 2}),
    })

    out = sectoral.compute_sector_skill_dominance("S1", top_k=2)
    assert out == 0.8


def test_compute_isco_skill_gap_and_stability():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter, {"ICT": Counter({"skill_a": 2, "skill_b": 1})})
    engine.sector_skill_canonical = defaultdict(Counter, {"ICT": Counter({"skill_b": 4, "skill_c": 1})})

    out = sectoral.compute_isco_skill_gap_and_stability("ICT")
    assert out["emerging_skills"] == ["skill_a"]
    assert out["missing_skills"] == ["skill_c"]
    assert out["stability_overlap"] == pytest.approx(1 / 3, rel=1e-6)
    assert out["overlap_skill_count"] == 1


def test_get_sector_from_occupation_falls_back_to_tracker_sector_map():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {}
    engine.occupation_group_labels = {}
    engine.sector_map = {
        "occ_tracker": "ICT professionals"
    }

    result = occupations.get_sector_from_occupation("occ_tracker")
    assert result == "ICT professionals"


def test_get_sector_from_occupation_returns_default_when_unknown():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {}
    engine.occupation_group_labels = {}
    engine.sector_map = {}

    result = occupations.get_sector_from_occupation("unknown_occ")
    assert result == "Sector not specified"

# ==========================================
# 8. OBSERVED OCCUPATION -> SKILL MATRIX
# ==========================================

def test_build_observed_occupation_skill_matrix_counts_correctly():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_observed = defaultdict(Counter)

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_a", "skill_b"]},
        {"occupation_id": "occ_1", "skills": ["skill_a"]},
        {"occupation_id": "occ_2", "skills": ["skill_b"]},
    ]

    matrix = sectoral.build_observed_occupation_skill_matrix(jobs)

    assert matrix["occ_1"]["skill_a"] == 2
    assert matrix["occ_1"]["skill_b"] == 1
    assert matrix["occ_2"]["skill_b"] == 1


def test_build_observed_occupation_skill_matrix_prefers_occupations_list():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_observed = defaultdict(Counter)

    jobs = [
        {"occupations": ["occ_new"], "occupation_id": "occ_old", "skills": ["skill_x"]},
    ]

    matrix = sectoral.build_observed_occupation_skill_matrix(jobs)

    assert "occ_new" in matrix
    assert "occ_old" in matrix
    assert matrix["occ_new"]["skill_x"] == 1


def test_build_observed_occupation_skill_matrix_skips_jobs_without_occupation():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_observed = defaultdict(Counter)

    jobs = [
        {"skills": ["skill_a"]},
        {"occupation_id": "", "skills": ["skill_b"]},
    ]

    matrix = sectoral.build_observed_occupation_skill_matrix(jobs)

    assert dict(matrix) == {}


def test_build_observed_occupation_skill_matrix_skips_empty_skill_ids():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_observed = defaultdict(Counter)

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_a", "", "   "]},
    ]

    matrix = sectoral.build_observed_occupation_skill_matrix(jobs)

    assert matrix["occ_1"]["skill_a"] == 1
    assert "" not in matrix["occ_1"]


def test_get_observed_skills_for_occupation_returns_sorted_counts():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_observed = defaultdict(Counter)
    engine.occ_skill_observed["occ_1"]["skill_a"] = 3
    engine.occ_skill_observed["occ_1"]["skill_b"] = 1

    result = sectoral.get_observed_skills_for_occupation("occ_1")

    assert result[0]["skill_id"] == "skill_a"
    assert result[0]["count"] == 3
    assert result[1]["skill_id"] == "skill_b"
    assert result[1]["count"] == 1


def test_get_observed_skills_for_occupation_can_resolve_labels():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_observed = defaultdict(Counter)
    engine.skill_map = {
        "skill_a": {"label": "Python"}
    }
    engine.occ_skill_observed["occ_1"]["skill_a"] = 2

    result = sectoral.get_observed_skills_for_occupation("occ_1", resolve_labels=True)

    assert result[0]["skill_id"] == "skill_a"
    assert result[0]["label"] == "Python"
    assert result[0]["count"] == 2


def test_build_observed_sector_skill_matrix_counts_correctly():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "isco_2512", "nace_code": "J62"},
        "occ_2": {"label": "Data analyst", "isco_group": "isco_2512", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "isco_2512": "Software developers"
    }
    engine.sector_map = {}

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_a", "skill_b"]},
        {"occupation_id": "occ_2", "skills": ["skill_a"]},
    ]

    matrix = sectoral.build_observed_sector_skill_matrix(jobs, sector_level="isco_group")

    assert matrix["Software developers"]["skill_a"] == 2
    assert matrix["Software developers"]["skill_b"] == 1


def test_get_observed_skills_for_sector_returns_sorted_counts():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter)
    engine.sector_skill_observed["ICT"]["skill_x"] = 4
    engine.sector_skill_observed["ICT"]["skill_y"] = 1

    result = sectoral.get_observed_skills_for_sector("ICT")

    assert result[0]["skill_id"] == "skill_x"
    assert result[0]["count"] == 4
    assert result[1]["skill_id"] == "skill_y"
    assert result[1]["count"] == 1

# ==========================================
# 9. OBSERVED SECTOR SKILL SUMMARIES
# ==========================================

def test_summarize_observed_sector_skills_returns_sorted_sectors():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter)

    engine.sector_skill_observed["Sector A"]["skill_1"] = 5
    engine.sector_skill_observed["Sector A"]["skill_2"] = 1
    engine.sector_skill_observed["Sector B"]["skill_3"] = 2

    result = sectoral.summarize_observed_sector_skills()

    assert result[0]["sector"] == "Sector A"
    assert result[0]["total_skill_mentions"] == 6
    assert result[1]["sector"] == "Sector B"
    assert result[1]["total_skill_mentions"] == 2


def test_summarize_observed_sector_skills_computes_frequencies():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter)

    engine.sector_skill_observed["ICT"]["skill_a"] = 3
    engine.sector_skill_observed["ICT"]["skill_b"] = 1

    result = sectoral.summarize_observed_sector_skills(top_k=10)

    ict = result[0]
    assert ict["sector"] == "ICT"
    assert ict["total_skill_mentions"] == 4
    assert ict["unique_skills"] == 2

    top_skills = ict["top_skills"]
    assert top_skills[0]["skill_id"] == "skill_a"
    assert top_skills[0]["count"] == 3
    assert top_skills[0]["frequency"] == 0.75

    assert top_skills[1]["skill_id"] == "skill_b"
    assert top_skills[1]["count"] == 1
    assert top_skills[1]["frequency"] == 0.25


def test_summarize_observed_sector_skills_can_resolve_labels_and_flags():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter)
    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
        "skill_b": {"label": "Solar design", "is_green": True, "is_digital": False},
    }

    engine.sector_skill_observed["ICT"]["skill_a"] = 2
    engine.sector_skill_observed["ICT"]["skill_b"] = 1

    result = sectoral.summarize_observed_sector_skills(resolve_labels=True)

    top_skills = result[0]["top_skills"]

    assert top_skills[0]["label"] == "Python"
    assert top_skills[0]["is_digital"] is True
    assert top_skills[0]["is_green"] is False

    assert top_skills[1]["label"] == "Solar design"
    assert top_skills[1]["is_green"] is True
    assert top_skills[1]["is_digital"] is False


def test_build_and_summarize_observed_sector_skills_from_jobs():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "isco_2512", "nace_code": "J62"},
        "occ_2": {"label": "Data analyst", "isco_group": "isco_2512", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "isco_2512": "Software developers"
    }
    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
        "skill_b": {"label": "SQL", "is_green": False, "is_digital": True},
    }

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_a", "skill_b"]},
        {"occupation_id": "occ_2", "skills": ["skill_a"]},
    ]

    result = sectoral.build_and_summarize_observed_sector_skills(
        jobs=jobs,
        sector_level="isco_group",
        resolve_labels=True,
        top_k=10
    )

    assert len(result) == 1
    sector = result[0]

    assert sector["sector"] == "Software developers"
    assert sector["total_skill_mentions"] == 3
    assert sector["unique_skills"] == 2

    assert sector["top_skills"][0]["skill_id"] == "skill_a"
    assert sector["top_skills"][0]["label"] == "Python"
    assert sector["top_skills"][0]["count"] == 2
    assert sector["top_skills"][0]["frequency"] == round(2 / 3, 6)


def test_summarize_single_sector_returns_one_sector_summary():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter)
    engine.skill_map = {
        "skill_x": {"label": "Docker", "is_green": False, "is_digital": True}
    }

    engine.sector_skill_observed["ICT"]["skill_x"] = 4

    result = sectoral.summarize_single_sector("ICT", resolve_labels=True)

    assert result["sector"] == "ICT"
    assert result["total_skill_mentions"] == 4
    assert result["unique_skills"] == 1
    assert result["top_skills"][0]["skill_id"] == "skill_x"
    assert result["top_skills"][0]["label"] == "Docker"
    assert result["top_skills"][0]["count"] == 4
    assert result["top_skills"][0]["frequency"] == 1.0

# ==========================================
# 10. CANONICAL SECTOR SKILLS
# ==========================================

def test_get_canonical_skills_for_occupation_returns_csv_skills():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_relations = defaultdict(set)
    engine.occ_skill_relations["occ_1"] = {"skill_a", "skill_b"}

    result = sectoral.get_canonical_skills_for_occupation("occ_1")

    returned_ids = {x["skill_id"] for x in result}
    assert returned_ids == {"skill_a", "skill_b"}


def test_get_canonical_skills_for_occupation_can_resolve_labels():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_relations = defaultdict(set)
    engine.occ_skill_relations["occ_1"] = {"skill_a"}
    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True}
    }

    result = sectoral.get_canonical_skills_for_occupation("occ_1", resolve_labels=True)

    assert result[0]["skill_id"] == "skill_a"
    assert result[0]["label"] == "Python"
    assert result[0]["is_digital"] is True
    assert result[0]["is_green"] is False


def test_build_canonical_sector_skill_matrix_counts_correctly():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_canonical = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "isco_2512", "nace_code": "J62"},
        "occ_2": {"label": "Data analyst", "isco_group": "isco_2512", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "isco_2512": "Software developers"
    }
    engine.occ_skill_relations = defaultdict(set)
    engine.occ_skill_relations["occ_1"] = {"skill_a", "skill_b"}
    engine.occ_skill_relations["occ_2"] = {"skill_a"}

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_x"]},
        {"occupation_id": "occ_2", "skills": ["skill_y"]},
    ]

    matrix = sectoral.build_canonical_sector_skill_matrix(jobs, sector_level="isco_group")

    assert matrix["Software developers"]["skill_a"] == 2
    assert matrix["Software developers"]["skill_b"] == 1


def test_get_canonical_skills_for_sector_returns_sorted_counts():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_canonical = defaultdict(Counter)
    engine.sector_skill_canonical["ICT"]["skill_a"] = 4
    engine.sector_skill_canonical["ICT"]["skill_b"] = 1

    result = sectoral.get_canonical_skills_for_sector("ICT")

    assert result[0]["skill_id"] == "skill_a"
    assert result[0]["count"] == 4
    assert result[1]["skill_id"] == "skill_b"
    assert result[1]["count"] == 1


def test_summarize_canonical_sector_skills_computes_frequencies():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_canonical = defaultdict(Counter)
    engine.sector_skill_canonical["ICT"]["skill_a"] = 3
    engine.sector_skill_canonical["ICT"]["skill_b"] = 1

    result = sectoral.summarize_canonical_sector_skills(top_k=10)

    ict = result[0]
    assert ict["sector"] == "ICT"
    assert ict["total_skill_mentions"] == 4
    assert ict["unique_skills"] == 2

    assert ict["top_skills"][0]["skill_id"] == "skill_a"
    assert ict["top_skills"][0]["frequency"] == 0.75
    assert ict["top_skills"][1]["skill_id"] == "skill_b"
    assert ict["top_skills"][1]["frequency"] == 0.25


def test_build_and_summarize_canonical_sector_skills_from_jobs():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_canonical = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "isco_2512", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "isco_2512": "Software developers"
    }
    engine.occ_skill_relations = defaultdict(set)
    engine.occ_skill_relations["occ_1"] = {"skill_a", "skill_b"}
    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
        "skill_b": {"label": "SQL", "is_green": False, "is_digital": True},
    }

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_x"]},
        {"occupation_id": "occ_1", "skills": ["skill_y"]},
    ]

    result = sectoral.build_and_summarize_canonical_sector_skills(
        jobs=jobs,
        sector_level="isco_group",
        resolve_labels=True,
        top_k=10
    )

    assert len(result) == 1
    sector = result[0]

    assert sector["sector"] == "Software developers"
    assert sector["total_skill_mentions"] == 4
    assert sector["unique_skills"] == 2


def test_compare_observed_and_canonical_for_sector_returns_both_views():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skill_observed = defaultdict(Counter)
    engine.sector_skill_canonical = defaultdict(Counter)
    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
        "skill_b": {"label": "SQL", "is_green": False, "is_digital": True},
    }

    engine.sector_skill_observed["ICT"]["skill_a"] = 3
    engine.sector_skill_canonical["ICT"]["skill_b"] = 2

    result = sectoral.compare_observed_and_canonical_for_sector(
        "ICT",
        resolve_labels=True,
        top_k=10
    )

    assert result["sector"] == "ICT"
    assert result["observed"]["sector"] == "ICT"
    assert result["canonical"]["sector"] == "ICT"

    assert result["observed"]["top_skills"][0]["skill_id"] == "skill_a"
    assert result["canonical"]["top_skills"][0]["skill_id"] == "skill_b"

    # ==========================================
    # 11. SECTOR -> SKILL GROUP MATRICES
    # ==========================================

def test_get_skill_group_returns_level_2_by_default():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.skill_hierarchy = {
        "skill_a": {
            "level_1": "S5",
            "level_2": "S5.1",
            "level_3": "S5.1.2"
        }
    }

    result = sectoral.get_skill_group("skill_a")
    assert result == "S5.1"

def test_get_skill_group_can_return_level_1():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.skill_hierarchy = {
        "skill_a": {
            "level_1": "S5",
            "level_2": "S5.1",
            "level_3": "S5.1.2"
        }
    }

    result = sectoral.get_skill_group("skill_a", level=1)
    assert result == "S5"

def test_get_skill_group_falls_back_to_label():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.skill_hierarchy = {}
    engine.skill_map = {
        "skill_a": {"label": "Python"}
    }

    result = sectoral.get_skill_group("skill_a", level=2)
    assert result == "Python"

def test_build_observed_sector_skillgroup_matrix_counts_correctly():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skillgroup_observed = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "isco_2512", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "isco_2512": "Software developers"
    }
    engine.skill_hierarchy = {
        "skill_a": {"level_1": "S5", "level_2": "S5.1", "level_3": "S5.1.2"},
        "skill_b": {"level_1": "S5", "level_2": "S5.1", "level_3": "S5.1.3"},
        "skill_c": {"level_1": "S2", "level_2": "S2.4", "level_3": "S2.4.1"},
    }

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_a", "skill_b", "skill_c"]},
        {"occupation_id": "occ_1", "skills": ["skill_a"]},
    ]

    matrix = sectoral.build_observed_sector_skillgroup_matrix(
        jobs=jobs,
        sector_level="isco_group",
        skill_group_level=2
    )

    assert matrix["Software developers"]["S5.1"] == 3
    assert matrix["Software developers"]["S2.4"] == 1

def test_build_canonical_sector_skillgroup_matrix_counts_correctly():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skillgroup_canonical = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "isco_2512", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "isco_2512": "Software developers"
    }
    engine.occ_skill_relations = defaultdict(set)
    engine.occ_skill_relations["occ_1"] = {"skill_a", "skill_b"}
    engine.skill_hierarchy = {
        "skill_a": {"level_1": "S5", "level_2": "S5.1", "level_3": "S5.1.2"},
        "skill_b": {"level_1": "S2", "level_2": "S2.4", "level_3": "S2.4.1"},
    }

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_x"]},
        {"occupation_id": "occ_1", "skills": ["skill_y"]},
    ]

    matrix = sectoral.build_canonical_sector_skillgroup_matrix(
        jobs=jobs,
        sector_level="isco_group",
        skill_group_level=2
    )

    assert matrix["Software developers"]["S5.1"] == 2
    assert matrix["Software developers"]["S2.4"] == 2

def test_summarize_observed_sector_skillgroups_returns_frequencies():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skillgroup_observed = defaultdict(Counter)
    engine.sector_skillgroup_observed["ICT"]["S5.1"] = 3
    engine.sector_skillgroup_observed["ICT"]["S2.4"] = 1

    result = sectoral.summarize_observed_sector_skillgroups(top_k=10)

    ict = result[0]
    assert ict["sector"] == "ICT"
    assert ict["total_group_mentions"] == 4
    assert ict["unique_groups"] == 2
    assert ict["top_groups"][0]["group_id"] == "S5.1"
    assert ict["top_groups"][0]["frequency"] == 0.75

def test_summarize_canonical_sector_skillgroups_returns_frequencies():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skillgroup_canonical = defaultdict(Counter)
    engine.sector_skillgroup_canonical["ICT"]["S5.1"] = 2
    engine.sector_skillgroup_canonical["ICT"]["S2.4"] = 2

    result = sectoral.summarize_canonical_sector_skillgroups(top_k=10)

    ict = result[0]
    assert ict["sector"] == "ICT"
    assert ict["total_group_mentions"] == 4
    assert ict["unique_groups"] == 2
    assert ict["top_groups"][0]["frequency"] == 0.5

def test_compare_observed_and_canonical_groups_for_sector_returns_both_views():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skillgroup_observed = defaultdict(Counter)
    engine.sector_skillgroup_canonical = defaultdict(Counter)

    engine.sector_skillgroup_observed["ICT"]["S5.1"] = 3
    engine.sector_skillgroup_canonical["ICT"]["S2.4"] = 2

    result = sectoral.compare_observed_and_canonical_groups_for_sector("ICT", top_k=10)

    assert result["sector"] == "ICT"
    assert result["observed_groups"]["top_groups"][0]["group_id"] == "S5.1"
    assert result["canonical_groups"]["top_groups"][0]["group_id"] == "S2.4"

# ==========================================
# 12. OFFICIAL ESCO MATRIX
# ==========================================

def test_get_esco_matrix_sheet_name():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)

    assert occupations.get_esco_matrix_sheet_name(1, 1) == "Matrix 1.1"
    assert occupations.get_esco_matrix_sheet_name(2, 3) == "Matrix 2.3"

def test_get_occupation_group_id_for_matrix_reduces_to_requested_level():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Software developer",
            "isco_group": "C2512",
            "nace_code": "J62"
        }
    }

    assert occupations.get_occupation_group_id_for_matrix("occ_1", occupation_level=1) == "C2"
    assert occupations.get_occupation_group_id_for_matrix("occ_1", occupation_level=2) == "C25"
    assert occupations.get_occupation_group_id_for_matrix("occ_1", occupation_level=3) == "C251"
    assert occupations.get_occupation_group_id_for_matrix("occ_1", occupation_level=4) == "C2512"

def test_get_official_esco_profile_for_occupation_returns_profile():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "J62"}
    }
    engine.esco_matrix_profiles = {
        ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
            "occupation_group_label": "Professionals",
            "profile": {
                "skill_group_a": 0.4,
                "skill_group_b": 0.6
            }
        }
    }

    result = occupations.get_official_esco_profile_for_occupation(
        "occ_1",
        skill_group_level=1,
        occupation_level=1
    )

    assert result["sheet_name"] == "Matrix 1.1"
    assert result["occupation_group_label"] == "Professionals"
    assert result["profile"]["skill_group_a"] == 0.4

def test_build_official_matrix_sector_skillgroup_profile_counts_correctly():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.matrix_profiles = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "J62"},
        "occ_2": {"label": "Data analyst", "isco_group": "C2", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "C2": "Professionals"
    }
    engine.esco_matrix_profiles = {
        ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
            "occupation_group_label": "Professionals",
            "profile": {
                "group_x": 0.3,
                "group_y": 0.7
            }
        }
    }

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_a"]},
        {"occupation_id": "occ_2", "skills": ["skill_b"]},
    ]

    matrix = sectoral.build_official_matrix_sector_skillgroup_profile(
        jobs=jobs,
        sector_level="isco_group",
        skill_group_level=1,
        occupation_level=1
    )

    assert matrix["Professionals"]["group_x"] == 0.6
    assert matrix["Professionals"]["group_y"] == 1.4

def test_summarize_official_matrix_sector_skillgroups_returns_sorted_groups():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.matrix_profiles = defaultdict(Counter)
    engine.matrix_profiles["ICT"]["group_a"] = 0.9
    engine.matrix_profiles["ICT"]["group_b"] = 0.1

    result = sectoral.summarize_official_matrix_sector_skillgroups(top_k=10)

    ict = result[0]
    assert ict["sector"] == "ICT"
    assert ict["top_groups"][0]["group_id"] == "group_a"
    assert ict["top_groups"][0]["frequency"] == 0.9

def test_compare_all_group_profiles_for_sector_returns_three_views():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.sector_skillgroup_observed = defaultdict(Counter)
    engine.sector_skillgroup_canonical = defaultdict(Counter)
    engine.matrix_profiles = defaultdict(Counter)

    engine.sector_skillgroup_observed["ICT"]["obs_group"] = 3
    engine.sector_skillgroup_canonical["ICT"]["can_group"] = 2
    engine.matrix_profiles["ICT"]["off_group"] = 1.5

    result = sectoral.compare_all_group_profiles_for_sector("ICT", top_k=10)

    assert result["sector"] == "ICT"
    assert result["observed_groups"]["top_groups"][0]["group_id"] == "obs_group"
    assert result["canonical_groups"]["top_groups"][0]["group_id"] == "can_group"
    assert result["official_matrix_groups"]["top_groups"][0]["group_id"] == "off_group"

# ==========================================
# 13. UNIFIED SECTORAL INTELLIGENCE
# ==========================================

def test_build_single_sector_intelligence_returns_all_sections():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
        "skill_b": {"label": "SQL", "is_green": False, "is_digital": True},
    }

    engine.sector_skill_observed = defaultdict(Counter)
    engine.sector_skillgroup_observed = defaultdict(Counter)

    engine.sector_skill_observed["ICT"]["skill_a"] = 3
    engine.sector_skillgroup_observed["ICT"]["S5.1"] = 3

    result = sectoral.build_single_sector_intelligence(
        sector_name="ICT",
        resolve_labels=True,
        top_k_skills=10,
        top_k_groups=10
    )

    assert result["sector"] == "ICT"
    assert "observed_skills" in result
    assert "observed_groups" in result
    assert "sector_metrics" in result
    assert "skill_transversal_insights" in result
    assert "canonical_skills" not in result
    assert "canonical_groups" not in result
    assert "matrix_groups" not in result

    assert result["observed_skills"]["top_skills"][0]["skill_id"] == "skill_a"
    assert result["observed_groups"]["top_groups"][0]["group_id"] == "S5.1"
    assert result["sector_metrics"]["coverage_unique_skills"] == 1


def test_build_sectoral_intelligence_from_jobs_builds_all_layers():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)

    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
        "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
    }

    engine.skill_hierarchy = {
        "skill_a": {"level_1": "S1", "level_2": "S1.1", "level_3": "S1.1.1"},
        "skill_obs": {"level_1": "S3", "level_2": "S3.1", "level_3": "S3.1.1"},
    }

    jobs = [
        {"skills": ["skill_obs"], "sectors": ["ICT"]},
        {"skills": ["skill_obs", "skill_a"], "sectors": ["ICT"]},
    ]

    result = sectoral.build_sectoral_intelligence(
        jobs=jobs,
        sector_level="nace_section",
        skill_group_level=1,
        occupation_level=1,
        resolve_labels=True,
        top_k_skills=10,
        top_k_groups=10,
        reset=True
    )

    assert len(result) == 1
    sector = result[0]

    assert sector["sector"] == "ICT"

    # observed skills
    assert sector["observed_skills"]["total_skill_mentions"] == 3
    assert sector["observed_skills"]["top_skills"][0]["label"] == "Docker"

    assert len(sector["observed_groups"]["top_groups"]) > 0
    assert "canonical_skills" not in sector
    assert "canonical_groups" not in sector
    assert "matrix_groups" not in sector
    assert "skill_transversal_insights" in sector

# ==========================================
# 14. MATRIX / SCHEMA CONTRACT / EDGE CASES
# ==========================================

def test_get_occupation_group_id_for_matrix_accepts_numeric_isco_group():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Numerical ISCO occupation",
            "isco_group": "2654",
            "nace_code": "J59"
        }
    }

    assert occupations.get_occupation_group_id_for_matrix("occ_1", occupation_level=1) == "C2"
    assert occupations.get_occupation_group_id_for_matrix("occ_1", occupation_level=2) == "C26"
    assert occupations.get_occupation_group_id_for_matrix("occ_1", occupation_level=3) == "C265"
    assert occupations.get_occupation_group_id_for_matrix("occ_1", occupation_level=4) == "C2654"


def test_get_official_esco_profile_for_occupation_accepts_numeric_isco_group():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    engine.occupation_meta = {
        "occ_1": {
            "label": "Numerical ISCO occupation",
            "isco_group": "2654",
            "nace_code": "J59"
        }
    }
    engine.esco_matrix_profiles = {
        ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
            "occupation_group_label": "Professionals",
            "profile": {"S1": 0.8}
        }
    }

    result = occupations.get_official_esco_profile_for_occupation(
        "occ_1",
        skill_group_level=1,
        occupation_level=1
    )

    assert result is not None
    assert result["occupation_group_id"] == "http://data.europa.eu/esco/isco/C2"
    assert result["profile"]["S1"] == 0.8


def test_build_official_matrix_sector_skillgroup_profile_uses_sector_label_key():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.matrix_profiles = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "J62"},
        "occ_2": {"label": "Data analyst", "isco_group": "C2", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {
        "C2": "Professionals"
    }
    engine.esco_matrix_profiles = {
        ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
            "occupation_group_label": "Professionals",
            "profile": {
                "group_x": 0.3,
                "group_y": 0.7
            }
        }
    }

    jobs = [
        {"occupation_id": "occ_1", "skills": ["skill_a"]},
        {"occupation_id": "occ_2", "skills": ["skill_b"]},
    ]

    matrix = sectoral.build_official_matrix_sector_skillgroup_profile(
        jobs=jobs,
        sector_level="isco_group",
        skill_group_level=1,
        occupation_level=1
    )

    assert "Professionals" in matrix
    assert "C2" not in matrix
    assert matrix["Professionals"]["group_x"] == 0.6
    assert matrix["Professionals"]["group_y"] == 1.4


def test_get_skill_group_label_resolves_short_code_and_uri():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.skill_group_labels = {
        "S4.8": "working with computers",
        "http://data.europa.eu/esco/skill-group/S4.8": "working with computers",
    }

    assert sectoral.get_skill_group_label("S4.8") == "working with computers"
    assert sectoral.get_skill_group_label("http://data.europa.eu/esco/skill-group/S4.8") == "working with computers"


def test_read_group_counter_includes_group_label():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.skill_group_labels = {
        "S1": "communication",
        "S2": "information skills",
    }

    counter = Counter({"S1": 3, "S2": 1})
    result = sectoral._read_group_counter(counter, top_k=10)

    assert result["total_mentions"] == 4
    assert result["unique_groups"] == 2
    assert result["top_groups"][0]["group_id"] == "S1"
    assert result["top_groups"][0]["group_label"] == "communication"
    assert result["top_groups"][0]["frequency"] == 0.75


def test_get_official_matrix_groups_for_sector_returns_group_labels():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.matrix_profiles = defaultdict(Counter)
    engine.skill_group_labels = {
        "S1": "communication",
        "S2": "information skills",
    }

    engine.matrix_profiles["ICT"]["S1"] = 0.8
    engine.matrix_profiles["ICT"]["S2"] = 0.2

    result = sectoral.get_official_matrix_groups_for_sector("ICT", top_k=10)

    assert result["sector"] == "ICT"
    assert result["total_group_mentions"] == 1.0
    assert result["unique_groups"] == 2
    assert result["top_groups"][0]["group_id"] == "S1"
    assert result["top_groups"][0]["group_label"] == "communication"


def test_compare_all_group_profiles_for_sector_returns_group_labels_in_all_views():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.skill_group_labels = {
        "S1": "communication",
        "S2": "information skills",
        "S3": "management",
    }

    engine.sector_skillgroup_observed = defaultdict(Counter)
    engine.sector_skillgroup_canonical = defaultdict(Counter)
    engine.matrix_profiles = defaultdict(Counter)

    engine.sector_skillgroup_observed["ICT"]["S1"] = 3
    engine.sector_skillgroup_canonical["ICT"]["S2"] = 2
    engine.matrix_profiles["ICT"]["S3"] = 1.5

    result = sectoral.compare_all_group_profiles_for_sector("ICT", top_k=10)

    assert result["observed_groups"]["top_groups"][0]["group_label"] == "communication"
    assert result["canonical_groups"]["top_groups"][0]["group_label"] == "information skills"
    assert result["official_matrix_groups"]["top_groups"][0]["group_label"] == "management"


def test_build_single_sector_intelligence_contains_sector_label_and_matrix_groups():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occupation_group_labels = {"ICT": "Information and communication technologies"}
    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
        "skill_b": {"label": "SQL", "is_green": False, "is_digital": True},
    }

    engine.sector_skill_observed = defaultdict(Counter)
    engine.sector_skillgroup_observed = defaultdict(Counter)

    engine.sector_skill_observed["ICT"]["skill_a"] = 3
    engine.sector_skillgroup_observed["ICT"]["S5.1"] = 3

    result = sectoral.build_single_sector_intelligence(
        sector_name="ICT",
        resolve_labels=True,
        top_k_skills=10,
        top_k_groups=10
    )

    assert result["sector"] == "ICT"
    assert "sector_label" in result
    assert "matrix_groups" not in result
    assert "observed_groups" in result
    assert result["sector_metrics"]["coverage_unique_skills"] == 1


@pytest.mark.integration
def test_endpoint_analyze_skills_sectoral_contract_with_matrix_groups():
    form_data = {
        "keywords": ["developer"],
        "min_date": "2024-01-01",
        "max_date": "2024-01-10",
        "include_sectoral": True,
        "skill_group_level": 1,
        "occupation_level": 1,
    }

    fake_jobs = [
            {
                "skills": ["skill_obs"],
                "sectors": ["Information Technology"],
                "upload_date": "2024-01-02",
            },
            {
                "skills": ["skill_obs", "skill_a"],
                "sectors": ["Information Technology"],
                "upload_date": "2024-01-08",
            },
    ]

    with patch.object(tracker, "fetch_all_jobs", new_callable=AsyncMock) as m_fetch, \
         patch.object(tracker, "fetch_skill_names", new_callable=AsyncMock) as m_fetch_skills, \
         patch.object(tracker, "fetch_occupation_labels", new_callable=AsyncMock) as m_fetch_occ:

        m_fetch.return_value = fake_jobs
        m_fetch_skills.return_value = None
        m_fetch_occ.return_value = None

        engine.occupation_meta = {
            "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "J62"},
        }
        engine.occupation_group_labels = {"C2": "C2"}
        engine.occ_skill_relations = defaultdict(set)
        engine.occ_skill_relations["occ_1"] = {"skill_a", "skill_b"}
        engine.skill_map = {
            "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
            "skill_b": {"label": "SQL", "is_green": False, "is_digital": True},
            "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
        }
        engine.skill_hierarchy = {
            "skill_a": {"level_1": "S1", "level_2": "S1.1", "level_3": "S1.1.1"},
            "skill_b": {"level_1": "S2", "level_2": "S2.2", "level_3": "S2.2.1"},
            "skill_obs": {"level_1": "S3", "level_2": "S3.1", "level_3": "S3.1.1"},
        }
        engine.esco_matrix_profiles = {
            ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
                "occupation_group_label": "Professionals",
                "profile": {"S1": 0.4, "S2": 0.6}
            }
        }

        response = client.post("/projector/analyze-skills", data=form_data)
        assert response.status_code == 200

        data = response.json()
        assert "sectoral" in data["insights"]
        assert isinstance(data["insights"]["sectoral"], list)
        assert len(data["insights"]["sectoral"]) == 1

        sector = data["insights"]["sectoral"][0]
        assert "sector" in sector
        assert "sector_label" in sector
        assert "observed_skills" in sector
        assert "observed_groups" in sector
        assert "sector_metrics" in sector
        assert "skill_transversal_insights" in sector
        assert "canonical_skills" not in sector
        assert "canonical_groups" not in sector
        assert "matrix_groups" not in sector
        assert sector["sector"] == "Information Technology"


@pytest.mark.integration
def test_endpoint_analyze_skills_sectoral_top_groups_include_group_label():
    form_data = {
        "keywords": ["developer"],
        "min_date": "2024-01-01",
        "max_date": "2024-01-10",
        "include_sectoral": True,
        "skill_group_level": 1,
        "occupation_level": 1,
    }

    fake_jobs = [
            {
                "skills": ["skill_obs"],
                "sectors": ["Information Technology"],
                "upload_date": "2024-01-02",
            }
    ]

    with patch.object(tracker, "fetch_all_jobs", new_callable=AsyncMock) as m_fetch, \
         patch.object(tracker, "fetch_skill_names", new_callable=AsyncMock) as m_fetch_skills, \
         patch.object(tracker, "fetch_occupation_labels", new_callable=AsyncMock) as m_fetch_occ:

        m_fetch.return_value = fake_jobs
        m_fetch_skills.return_value = None
        m_fetch_occ.return_value = None

        engine.occupation_meta = {
            "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "J62"},
        }
        engine.occupation_group_labels = {"C2": "C2"}
        engine.occ_skill_relations = defaultdict(set)
        engine.occ_skill_relations["occ_1"] = {"skill_a"}
        engine.skill_map = {
            "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
            "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
        }
        engine.skill_hierarchy = {
            "skill_a": {"level_1": "S1", "level_2": "S1.1", "level_3": "S1.1.1"},
            "skill_obs": {"level_1": "S3", "level_2": "S3.1", "level_3": "S3.1.1"},
        }
        engine.skill_group_labels = {
            "S1": "communication",
            "S3": "digital content creation",
        }
        engine.esco_matrix_profiles = {
            ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
                "occupation_group_label": "Professionals",
                "profile": {"S1": 1.0}
            }
        }

        response = client.post("/projector/analyze-skills", data=form_data)
        assert response.status_code == 200

        data = response.json()
        sector = data["insights"]["sectoral"][0]

        assert "group_label" in sector["observed_groups"]["top_groups"][0]
        assert "canonical_groups" not in sector
        assert "matrix_groups" not in sector


@pytest.mark.integration
def test_endpoint_analyze_skills_sectoral_uses_tracker_sector_labels_without_hierarchy():
    form_data = {
        "keywords": ["developer"],
        "min_date": "2024-01-01",
        "max_date": "2024-01-10",
        "include_sectoral": True,
        "sector_system": "nace",
        "sector_level": "nace_class",
        "skill_group_level": 1,
        "occupation_level": 1,
    }

    fake_jobs = [
        {
            "skills": ["skill_obs"],
            "sectors": ["Professional services"],
            "upload_date": "2024-01-02",
        }
    ]

    with patch.object(tracker, "fetch_all_jobs", new_callable=AsyncMock) as m_fetch, \
         patch.object(tracker, "fetch_skill_names", new_callable=AsyncMock) as m_fetch_skills, \
         patch.object(tracker, "fetch_occupation_labels", new_callable=AsyncMock) as m_fetch_occ:

        m_fetch.return_value = fake_jobs
        m_fetch_skills.return_value = None
        m_fetch_occ.return_value = None

        engine.occupation_meta = {
            "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "C10.11"},
        }
        engine.occupation_group_labels = {"C2": "C2"}
        engine.occ_skill_relations = defaultdict(set)
        engine.occ_skill_relations["occ_1"] = {"skill_a"}
        engine.skill_map = {
            "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
            "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
        }
        engine.skill_hierarchy = {
            "skill_a": {"level_1": "S1", "level_2": "S1.1", "level_3": "S1.1.1"},
            "skill_obs": {"level_1": "S3", "level_2": "S3.1", "level_3": "S3.1.1"},
        }
        engine.esco_matrix_profiles = {
            ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
                "occupation_group_label": "Professionals",
                "profile": {"S1": 1.0}
            }
        }

        response = client.post("/projector/analyze-skills", data=form_data)
        assert response.status_code == 200

        data = response.json()
        sector = data["insights"]["sectoral"][0]
        assert sector["sector"] == "Professional services"
        assert data["insights"]["sectoral_views"]["nace"]["sector_level"] == "tracker_sector"
        assert "levels" not in data["insights"]["sectoral_views"]["nace"]
        assert sector["sector_metrics"]["coverage_unique_skills"] >= 1
        assert "dominance_top10_share" in sector["sector_metrics"]
        assert len(sector["skill_transversal_insights"]) >= 1
        assert "sector_breadth" in sector["skill_transversal_insights"][0]


@pytest.mark.integration
def test_endpoint_analyze_skills_sectoral_prefers_tracker_job_sectors_for_nace():
    form_data = {
        "keywords": ["developer"],
        "min_date": "2024-01-01",
        "max_date": "2024-01-10",
        "include_sectoral": True,
        "sector_system": "nace",
        "sector_level": "nace_class",
        "skill_group_level": 1,
        "occupation_level": 1,
    }

    fake_jobs = [
        {
            "occupation_id": "occ_1",
            "skills": ["skill_obs"],
            "sectors": [{"code": "M70.22", "label": "Business and other management consultancy activities"}],
            "upload_date": "2024-01-02",
        }
    ]

    with patch.object(tracker, "fetch_all_jobs", new_callable=AsyncMock) as m_fetch, \
         patch.object(tracker, "fetch_skill_names", new_callable=AsyncMock) as m_fetch_skills, \
         patch.object(tracker, "fetch_occupation_labels", new_callable=AsyncMock) as m_fetch_occ:

        m_fetch.return_value = fake_jobs
        m_fetch_skills.return_value = None
        m_fetch_occ.return_value = None

        engine.occupation_meta = {
            "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "C10.11"},
        }
        engine.occupation_group_labels = {"C2": "C2"}
        engine.occ_skill_relations = defaultdict(set)
        engine.occ_skill_relations["occ_1"] = {"skill_a"}
        engine.skill_map = {
            "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
            "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
        }
        engine.skill_hierarchy = {
            "skill_a": {"level_1": "S1", "level_2": "S1.1", "level_3": "S1.1.1"},
            "skill_obs": {"level_1": "S3", "level_2": "S3.1", "level_3": "S3.1.1"},
        }
        engine.esco_matrix_profiles = {
            ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
                "occupation_group_label": "Professionals",
                "profile": {"S1": 1.0}
            }
        }

        response = client.post("/projector/analyze-skills", data=form_data)
        assert response.status_code == 200

        data = response.json()
        sector = data["insights"]["sectoral"][0]
        assert sector["sector"] == "M"
        assert sector["sector_label"] == "Professional, scientific and technical activities"
        assert data["insights"]["sectors"][0]["name"] == "M"

@pytest.mark.integration
def test_endpoint_analyze_skills_sectoral_forces_tracker_sector_view_when_sector_system_is_isco():
    form_data = {
        "keywords": ["developer"],
        "min_date": "2024-01-01",
        "max_date": "2024-01-10",
        "include_sectoral": True,
        "sector_system": "isco",
        "sector_level": "nace_class",
        "skill_group_level": 1,
        "occupation_level": 1,
    }

    fake_jobs = [
        {
            "skills": ["skill_obs"],
            "sectors": ["Information Technology"],
            "upload_date": "2024-01-02",
        }
    ]

    with patch.object(tracker, "fetch_all_jobs", new_callable=AsyncMock) as m_fetch, \
         patch.object(tracker, "fetch_skill_names", new_callable=AsyncMock) as m_fetch_skills, \
         patch.object(tracker, "fetch_occupation_labels", new_callable=AsyncMock) as m_fetch_occ:

        m_fetch.return_value = fake_jobs
        m_fetch_skills.return_value = None
        m_fetch_occ.return_value = None

        engine.occupation_meta = {
            "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "C10.11"},
        }
        engine.occupation_group_labels = {"C2": "C2"}
        engine.occ_skill_relations = defaultdict(set)
        engine.occ_skill_relations["occ_1"] = {"skill_a"}
        engine.skill_map = {
            "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
            "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
        }
        engine.skill_hierarchy = {
            "skill_a": {"level_1": "S1", "level_2": "S1.1", "level_3": "S1.1.1"},
            "skill_obs": {"level_1": "S3", "level_2": "S3.1", "level_3": "S3.1.1"},
        }
        engine.esco_matrix_profiles = {
            ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
                "occupation_group_label": "Professionals",
                "profile": {"S1": 1.0}
            }
        }

        response = client.post("/projector/analyze-skills", data=form_data)
        assert response.status_code == 200

        data = response.json()
        sector = data["insights"]["sectoral"][0]
        assert data["insights"]["sectoral_mode"] == "nace"
        assert set(data["insights"]["sectoral_views"].keys()) == {"nace"}
        assert sector["sector"] == "Information Technology"
        assert "isco_interpretation" not in sector


@pytest.mark.integration
def test_endpoint_analyze_skills_sectoral_exposes_tracker_nace_view_only():
    form_data = {
        "keywords": ["developer"],
        "min_date": "2024-01-01",
        "max_date": "2024-01-10",
        "include_sectoral": True,
        "sector_system": "both",
        "sector_level": "nace_class",
        "skill_group_level": 1,
        "occupation_level": 1,
    }

    fake_jobs = [
        {
            "skills": ["skill_obs"],
            "sectors": ["Information Technology"],
            "upload_date": "2024-01-02",
        }
    ]

    with patch.object(tracker, "fetch_all_jobs", new_callable=AsyncMock) as m_fetch, \
         patch.object(tracker, "fetch_skill_names", new_callable=AsyncMock) as m_fetch_skills, \
         patch.object(tracker, "fetch_occupation_labels", new_callable=AsyncMock) as m_fetch_occ:

        m_fetch.return_value = fake_jobs
        m_fetch_skills.return_value = None
        m_fetch_occ.return_value = None

        engine.occupation_meta = {
            "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "C10.11"},
        }
        engine.occupation_group_labels = {"C2": "C2"}
        engine.occ_skill_relations = defaultdict(set)
        engine.occ_skill_relations["occ_1"] = {"skill_a"}
        engine.skill_map = {
            "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
            "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
        }
        engine.skill_hierarchy = {
            "skill_a": {"level_1": "S1", "level_2": "S1.1", "level_3": "S1.1.1"},
            "skill_obs": {"level_1": "S3", "level_2": "S3.1", "level_3": "S3.1.1"},
        }
        engine.esco_matrix_profiles = {
            ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
                "occupation_group_label": "Professionals",
                "profile": {"S1": 1.0}
            }
        }

        response = client.post("/projector/analyze-skills", data=form_data)
        assert response.status_code == 200

        data = response.json()
        assert data["insights"]["sectoral_mode"] == "nace"
        assert set(data["insights"]["sectoral_views"].keys()) == {"nace"}
        assert data["insights"]["sectoral_views"]["nace"]["sector_level"] == "tracker_sector"
        assert data["insights"]["sectoral_views"]["nace"]["items"][0]["sector"] == "Information Technology"
        assert "levels" not in data["insights"]["sectoral_views"]["nace"]
        # Backward compatibility: primary `sectoral` remains list format.
        assert isinstance(data["insights"]["sectoral"], list)


@pytest.mark.integration
def test_endpoint_analyze_skills_sectoral_tracker_labels_define_sector_keys():
    form_data = {
        "keywords": ["developer"],
        "min_date": "2024-01-01",
        "max_date": "2024-01-10",
        "include_sectoral": True,
        "sector_system": "both",
        "sector_level": "nace_section",
        "skill_group_level": 1,
        "occupation_level": 1,
    }

    fake_jobs = [
        {"skills": ["skill_obs"], "sectors": ["Manufacturing"], "upload_date": "2024-01-02"},
        {"skills": ["skill_obs"], "sectors": ["Information and communication"], "upload_date": "2024-01-03"},
    ]

    with patch.object(tracker, "fetch_all_jobs", new_callable=AsyncMock) as m_fetch, \
         patch.object(tracker, "fetch_skill_names", new_callable=AsyncMock) as m_fetch_skills, \
         patch.object(tracker, "fetch_occupation_labels", new_callable=AsyncMock) as m_fetch_occ:
        m_fetch.return_value = fake_jobs
        m_fetch_skills.return_value = None
        m_fetch_occ.return_value = None

        engine.occupation_meta = {
            "occ_1": {"label": "Developer", "isco_group": "C2", "nace_code": "C10.11"},
            "occ_2": {"label": "Programmer", "isco_group": "C2", "nace_code": "J62.01"},
        }
        engine.occupation_group_labels = {"C2": "C2"}
        engine.occ_skill_relations = defaultdict(set)
        engine.occ_skill_relations["occ_1"] = {"skill_a"}
        engine.occ_skill_relations["occ_2"] = {"skill_b"}
        engine.skill_map = {
            "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
            "skill_b": {"label": "SQL", "is_green": False, "is_digital": True},
            "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
        }
        engine.skill_hierarchy = {
            "skill_a": {"level_1": "S1", "level_2": "S1.1", "level_3": "S1.1.1"},
            "skill_b": {"level_1": "S2", "level_2": "S2.1", "level_3": "S2.1.1"},
            "skill_obs": {"level_1": "S3", "level_2": "S3.1", "level_3": "S3.1.1"},
        }
        engine.esco_matrix_profiles = {
            ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {"occupation_group_label": "Professionals", "profile": {"S1": 1.0}}
        }

        response = client.post("/projector/analyze-skills", data=form_data)
        assert response.status_code == 200
        data = response.json()

        nace_view = data["insights"]["sectoral_views"]["nace"]
        assert nace_view["sector_level"] == "tracker_sector"
        assert "levels" not in nace_view
        assert {x["sector"] for x in nace_view["items"]} == {
            "Manufacturing",
            "Information and communication",
        }


@pytest.mark.integration
def test_endpoint_sectoral_intelligence_selected_period_contract():
    form_data = {
        "keywords": ["developer"],
        "data_source": "live",
        "mode": "selected_period",
        "min_date": "2024-01-01",
        "max_date": "2024-01-10",
        "skill_group_level": 1,
        "occupation_level": 1,
    }

    fake_jobs = [
        {
            "skills": ["skill_obs"],
            "sectors": ["Information Technology"],
            "upload_date": "2024-01-02",
        }
    ]

    with patch.object(tracker, "fetch_all_jobs", new_callable=AsyncMock) as m_fetch, \
         patch.object(tracker, "fetch_skill_names", new_callable=AsyncMock) as m_fetch_skills:
        m_fetch.return_value = fake_jobs
        m_fetch_skills.return_value = None
        engine.skill_map = {
            "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
        }
        engine.skill_hierarchy = {
            "skill_obs": {"level_1": "S3", "level_2": "S3.1", "level_3": "S3.1.1"},
        }
        engine.skill_group_labels = {"S3": "digital content creation"}

        response = client.post("/projector/sectoral-intelligence", data=form_data)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "completed"
        assert data["data_source"] == "live"
        assert data["mode"] == "selected_period"
        assert data["sector_filter"] == []
        assert data["sector_level"] == "tracker_sector"
        assert data["window"] == {
            "label": "Selected period",
            "min_date": "2024-01-01",
            "max_date": "2024-01-10",
        }
        assert data["items"][0]["sector"] == "Information Technology"
        assert data["items"][0]["observed_skills"]["total_skill_mentions"] == 1
        assert data["sector_view_names"]["latest"] == "Last six months"


@pytest.mark.integration
def test_endpoint_sectoral_snapshot_contract():
    form_data = {
        "year": 2024,
    }

    fake_jobs = [
        {
            "title": "Backend Developer",
            "skills": ["skill_obs"],
            "sectors": ["Information Technology"],
            "upload_date": "2024-01-02",
        }
    ]

    with patch.object(service, "sector_snapshot_store", None), \
         patch.object(tracker, "load_cached_jobs") as m_cache, \
         patch.object(tracker, "fetch_skill_names", new_callable=AsyncMock) as m_fetch_skills:
        m_cache.return_value = fake_jobs
        m_fetch_skills.return_value = None
        engine.skill_map = {
            "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
        }

        response = client.post("/projector/sectoral-snapshot", data=form_data)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "completed"
        assert data["year"] == 2024
        assert data["reference_year"] == 2023
        assert data["data_source"] == "cache"
        assert data["window"] == {
            "label": "2024 snapshot",
            "min_date": "2024-01-01",
            "max_date": "2024-12-31",
        }
        assert data["total_jobs"] == 1
        assert data["sectors"][0]["sector"] == "Information Technology"
        assert data["sectors"][0]["job_count"] == 1
        assert data["sectors"][0]["top_skills"][0]["label"] == "Docker"
        assert data["sectors"][0]["top_skills"][0]["share_in_sector"] == 1.0
        assert data["sectors"][0]["top_skills"][0]["rank"] == 1
        assert data["sectors"][0]["top_skills"][0]["growth_vs_reference_year"] == "new_entry"
        assert data["sectors"][0]["top_skills"][0]["sector_breadth"] == 1
        assert data["sectors"][0]["all_skills"][0]["label"] == "Docker"
        assert data["sectors"][0]["top_job_titles"] == [
            {"name": "Backend Developer", "count": 1}
        ]


@pytest.mark.integration
def test_endpoint_sector_skills_comparison_contract():
    store = _FakeSectorSnapshotStore({
        "by_year": {
            2023: {
                "status": "completed",
                "year": 2023,
                "data_source": "postgres",
                "window": {"label": "2023 snapshot", "min_date": "2023-01-01", "max_date": "2023-12-31"},
                "total_jobs": 10,
                "sector_filter": [],
                "sectors": [
                    {
                        "sector": "ICT",
                        "sector_label": "ICT",
                        "job_count": 10,
                        "job_share": 1.0,
                        "total_skill_mentions": 10,
                        "unique_skills": 1,
                        "top_skills": [{"skill_id": "skill-python", "label": "Python", "count": 2, "frequency": 0.2}],
                        "all_skills": [{"skill_id": "skill-python", "label": "Python", "count": 2, "frequency": 0.2}],
                        "top_job_titles": [],
                    }
                ],
            },
            2024: {
                "status": "completed",
                "year": 2024,
                "data_source": "postgres",
                "window": {"label": "2024 snapshot", "min_date": "2024-01-01", "max_date": "2024-12-31"},
                "total_jobs": 20,
                "sector_filter": [],
                "sectors": [
                    {
                        "sector": "ICT",
                        "sector_label": "ICT",
                        "job_count": 20,
                        "job_share": 1.0,
                        "total_skill_mentions": 20,
                        "unique_skills": 1,
                        "top_skills": [{"skill_id": "skill-python", "label": "Python", "count": 6, "frequency": 0.3}],
                        "all_skills": [{"skill_id": "skill-python", "label": "Python", "count": 6, "frequency": 0.3}],
                        "top_job_titles": [],
                    }
                ],
            },
        }
    })

    with patch.object(service, "sector_snapshot_store", store):
        response = client.post(
            "/projector/sector-skills-comparison",
            data={"year": 2024, "locations": "IT", "sectors": "ICT", "metric": "share"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["reference_year"] == 2023
    assert data["metric"] == "share"
    assert data["sectors"] == ["ICT"]
    assert data["skills"] == ["Python"]
    assert data["matrix"][0]["sector"] == "ICT"
    assert data["matrix"][0]["label"] == "Python"
    assert data["matrix"][0]["share"] == 0.3


def test_build_observed_occupation_skill_matrix_accumulates_when_reset_false():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.occ_skill_observed = defaultdict(Counter)

    jobs_a = [{"occupation_id": "occ_1", "skills": ["skill_a"]}]
    jobs_b = [{"occupation_id": "occ_1", "skills": ["skill_a", "skill_b"]}]

    sectoral.build_observed_occupation_skill_matrix(jobs_a, reset=True)
    sectoral.build_observed_occupation_skill_matrix(jobs_b, reset=False)

    assert engine.occ_skill_observed["occ_1"]["skill_a"] == 2
    assert engine.occ_skill_observed["occ_1"]["skill_b"] == 1


def test_build_official_matrix_sector_skillgroup_profile_accumulates_when_reset_false():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)
    engine.matrix_profiles = defaultdict(Counter)

    engine.occupation_meta = {
        "occ_1": {"label": "Software developer", "isco_group": "C2", "nace_code": "J62"},
    }
    engine.occupation_group_labels = {"C2": "Professionals"}
    engine.esco_matrix_profiles = {
        ("Matrix 1.1", "http://data.europa.eu/esco/isco/C2"): {
            "occupation_group_label": "Professionals",
            "profile": {"group_x": 0.3}
        }
    }

    jobs = [{"occupation_id": "occ_1", "skills": ["skill_a"]}]

    sectoral.build_official_matrix_sector_skillgroup_profile(
        jobs=jobs,
        sector_level="isco_group",
        skill_group_level=1,
        occupation_level=1,
        reset=True
    )
    sectoral.build_official_matrix_sector_skillgroup_profile(
        jobs=jobs,
        sector_level="isco_group",
        skill_group_level=1,
        occupation_level=1,
        reset=False
    )

    assert engine.matrix_profiles["Professionals"]["group_x"] == 0.6


def test_build_sectoral_intelligence_and_single_sector_are_consistent():
    from app.core.container import ProjectorEngine

    engine = ProjectorEngine()
    occupations = OccupationAnalytics(engine)
    sectoral = SectoralAnalytics(engine, occupations)

    engine.skill_map = {
        "skill_a": {"label": "Python", "is_green": False, "is_digital": True},
        "skill_obs": {"label": "Docker", "is_green": False, "is_digital": True},
    }
    engine.skill_hierarchy = {
        "skill_a": {"level_1": "S1", "level_2": "S1.1", "level_3": "S1.1.1"},
        "skill_obs": {"level_1": "S3", "level_2": "S3.1", "level_3": "S3.1.1"},
    }

    jobs = [
        {"skills": ["skill_obs"], "sectors": ["Information Technology"]},
        {"skills": ["skill_obs", "skill_a"], "sectors": ["Information Technology"]},
    ]

    result = sectoral.build_sectoral_intelligence(
        jobs=jobs,
        sector_level="nace_section",
        skill_group_level=1,
        occupation_level=1,
        resolve_labels=True,
        top_k_skills=10,
        top_k_groups=10,
        reset=True
    )

    assert len(result) == 1
    sector = result[0]
    single = sectoral.build_single_sector_intelligence(
        sector_name=sector["sector"],
        resolve_labels=True,
        top_k_skills=10,
        top_k_groups=10
    )

    assert single["sector"] == sector["sector"]
    assert single["observed_skills"]["total_skill_mentions"] == sector["observed_skills"]["total_skill_mentions"]
    assert single["observed_groups"]["unique_groups"] == sector["observed_groups"]["unique_groups"]
    assert single["sector_metrics"] == sector["sector_metrics"]
    assert "canonical_skills" not in single
    assert "matrix_groups" not in single
