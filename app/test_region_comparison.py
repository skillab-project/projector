from datetime import date
import time

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from app.schemas.responses import RegionalComparisonResponse
from app.services.analytics.market import MarketAnalytics
from app.services.projector_service import ProjectorService


def _wait_for_task(client, status_url):
    for _ in range(1000):
        response = client.get(status_url)
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.001)
    raise AssertionError(f"Task at {status_url} did not finish during the test")


class _Engine:
    def __init__(self):
        self.stop_requested = False
        self.skill_map = {
            "s1": {"label": "Python", "is_green": False, "is_digital": True},
            "s2": {"label": "SQL", "is_green": False, "is_digital": True},
            "s3": {"label": "Project management", "is_green": False, "is_digital": False},
        }


class _Tracker:
    def __init__(self, jobs):
        self.jobs = jobs
        self.payload = None

    async def fetch_all_jobs(self, payload):
        self.payload = payload
        return self.jobs

    async def fetch_skill_names(self, skill_ids):
        return None


class _Occupations:
    def get_sector_keys_from_job(self, job, level="nace_section"):
        return job.get("sector_names", [])


class _Dummy:
    pass


def _service(jobs):
    engine = _Engine()
    tracker = _Tracker(jobs)
    occupations = _Occupations()
    market = MarketAnalytics(engine, tracker, occupations)
    service = ProjectorService(
        engine,
        tracker,
        occupations,
        _Dummy(),
        market,
        _Dummy(),
        _Dummy(),
        None,
    )
    return service, tracker


@pytest.mark.asyncio
async def test_compare_regions_filters_real_nuts_fields_and_keyword():
    jobs = [
        {
            "nuts2": "DK03",
            "location_code": "DK",
            "skills": ["s1", "s2"],
            "organization_name": "A",
            "title": "Data Engineer",
            "sector_names": ["ICT"],
        },
        {
            "nuts2": "DK03",
            "location_code": "DK",
            "skills": ["s1"],
            "organization_name": "B",
            "title": "Developer",
            "sector_names": ["ICT"],
        },
        {
            "nuts2": "ITF4",
            "location_code": "IT",
            "skills": ["s2", "s3"],
            "organization_name": "C",
            "title": "Analyst",
            "sector_names": ["Consulting"],
        },
        {
            "nuts2": "ITF4",
            "location_code": "IT",
            "skills": ["s3"],
            "organization_name": "C",
            "title": "PM",
            "sector_names": ["Consulting"],
        },
        {
            "nuts2": "DE60",
            "location_code": "DE",
            "skills": ["s1"],
            "organization_name": "X",
            "title": "Other",
            "sector_names": ["ICT"],
        },
    ]
    service, tracker = _service(jobs)

    result = await service.compare_regions(
        region_a="DK03",
        region_b="ITF4",
        min_date="2026-01-01",
        max_date="2026-09-23",
        keyword="ai",
    )

    RegionalComparisonResponse.model_validate(result)
    assert tracker.payload == {
        "location_code": ["DK", "IT"],
        "min_upload_date": "2026-01-01",
        "max_upload_date": "2026-09-23",
        "keywords": ["ai"],
    }
    assert result["scope"] == "keyword"
    assert result["nuts_level"] == "nuts2"
    assert result["region_a"]["total_jobs"] == 2
    assert result["region_b"]["total_jobs"] == 2

    python = next(item for item in result["comparison"]["skills"] if item["skill_id"] == "s1")
    assert python["region_a_count"] == 2
    assert python["region_b_count"] == 0
    assert python["count_difference"] == -2


@pytest.mark.asyncio
async def test_compare_regions_defaults_to_last_twelve_months():
    service, tracker = _service([])
    service._today = lambda: date(2026, 9, 23)

    result = await service.compare_regions("DK03", "ITF4")

    assert result["window"] == {
        "min_date": "2025-09-23",
        "max_date": "2026-09-23",
    }
    assert tracker.payload["min_upload_date"] == "2025-09-23"
    assert tracker.payload["max_upload_date"] == "2026-09-23"


@pytest.mark.asyncio
async def test_compare_regions_rejects_mixed_nuts_levels():
    service, _ = _service([])

    with pytest.raises(ValueError, match="same NUTS level"):
        await service.compare_regions("DK0", "ITF4")


@pytest.mark.asyncio
async def test_comparison_keeps_counts_below_other_regions_top_ten():
    jobs = [
        {"nuts2": "DK03", "skills": [f"s{i}"], "title": f"Title {i}",
         "organization_name": f"Employer {i}", "sector_names": [f"Sector {i}"]}
        for i in range(11) for _ in range(2 if i < 10 else 1)
    ] + [
        {"nuts2": "ITF4", "skills": ["s10"], "title": "Title 10",
         "organization_name": "Employer 10", "sector_names": ["Sector 10"]}
        for _ in range(5)
    ]
    service, _ = _service(jobs)
    result = await service.compare_regions("DK03", "ITF4")
    assert len(result["region_a"]["top_skills"]) == 10
    skill = next(row for row in result["comparison"]["skills"] if row["skill_id"] == "s10")
    assert skill["region_a_count"] == 1
    assert skill["region_a_rank"] == 11
    assert skill["count_difference"] == 4
    assert skill["region_a_share"] == round(100 / 21, 2)
    for key in ("sectors", "job_titles", "employers"):
        row = result["comparison"][key][0]
        assert row["region_a_count"] == 1
        assert row["region_b_count"] == 5
        assert row["count_difference"] == 4


@pytest.mark.parametrize("data", [
    {"region_a": "DK03", "region_b": "DK03"},
    {"region_a": "DK0", "region_b": "ITF4"},
    {"region_a": "DK", "region_b": "IT"},
    {"region_a": "DK!3", "region_b": "ITF4"},
    {"region_a": "DK03", "region_b": "ITF4", "min_date": "2024-01-01"},
    {"region_a": "DK03", "region_b": "ITF4", "min_date": "2024-02-01", "max_date": "2024-01-01"},
    {"region_a": "DK03", "region_b": "ITF4", "min_date": "invalid", "max_date": "2024-01-01"},
])
def test_compare_regions_endpoint_validation(data, monkeypatch):
    from app.main import app
    from app.core.container import tracker
    fetch = AsyncMock(return_value=[])
    monkeypatch.setattr(tracker, "fetch_all_jobs", fetch)
    response = TestClient(app).post("/projector/compare-regions", data=data)
    assert response.status_code == 422
    fetch.assert_not_awaited()


@pytest.mark.integration
@pytest.mark.e2e
def test_compare_regions_endpoint_full_flow(monkeypatch):
    from app.main import app
    from app.core.container import tracker, engine
    jobs = [
        {"nuts2": "DK03", "location_code": "DK", "skills": ["s1", "s2"],
         "sectors": ["Education"], "title": "Teacher", "organization_name": "School"},
        {"nuts2": "ITF4", "location_code": "IT", "skills": ["s2"],
         "sectors": ["Education"], "title": "Trainer", "organization_name": "College"},
        {"nuts2": "DE60", "location_code": "DE", "skills": ["s1"]},
    ]
    fetch = AsyncMock(return_value=jobs)
    monkeypatch.setattr(tracker, "fetch_all_jobs", fetch)
    monkeypatch.setattr(tracker, "fetch_skill_names", AsyncMock())
    monkeypatch.setattr(engine, "skill_map", _Engine().skill_map)
    with TestClient(app) as client:
        for path in ("/projector/compare-regions", "/compare-regions"):
            response = client.post(path, data={"region_a": " dk03 ", "region_b": "itf4",
                                              "min_date": "2024-01-01", "max_date": "2024-12-31", "keyword": "teacher"})
            assert response.status_code == 202
            task = _wait_for_task(client, response.json()["status_url"])
            assert task["status"] == "completed"
            data = task["result"]
            RegionalComparisonResponse.model_validate(data)
            assert data["region_a"]["code"] == "DK03"
            assert data["region_a"]["total_jobs"] == data["region_b"]["total_jobs"] == 1
            assert data["comparison"]["total_jobs_difference"] == 0
            python = next(row for row in data["comparison"]["skills"] if row["skill_id"] == "s1")
            assert python["share_difference_percentage_points"] == -100
            assert python["region_a_specialization"] == 2
            assert data["comparison"]["sectors"][0]["name"] == "Education"
        assert "/projector/compare-regions" in client.get("/openapi.json").json()["paths"]
    assert fetch.call_args.args[0]["keywords"] == ["teacher"]


@pytest.mark.asyncio
async def test_compare_regions_missing_and_legacy_nuts():
    service, _ = _service([{ "location_code": "ITF43", "skills": ["s1"]}])
    result = await service.compare_regions("DK03", "ITF4")
    assert result["region_b"]["total_jobs"] == 1
    assert result["comparison"]["total_jobs_difference_percentage"] == "new_entry"
    empty_service, _ = _service([])
    empty = await empty_service.compare_regions("DK03", "ITF4")
    assert empty["message"]
    assert empty["comparison"]["skills"] == []
    assert empty["comparison"]["total_jobs_difference_percentage"] == 0
