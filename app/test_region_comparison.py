from datetime import date

import pytest

from app.schemas.responses import RegionalComparisonResponse
from app.services.analytics.market import MarketAnalytics
from app.services.projector_service import ProjectorService


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
