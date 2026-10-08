import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.container import service as container_service
from app.main import app
from app.services.analytics.market import MarketAnalytics
from app.services.analytics.regional import RegionalAnalytics
from app.services.analytics.sectoral import SectoralAnalytics
from app.services.analytics.trends import TrendAnalytics
from app.services.projector_service import ProjectorService
from app.services.sector_snapshot_store import SectorSnapshotStore


class _Engine:
    def __init__(self):
        self.stop_requested = False
        self.skill_map = {
            "s1": {"label": "Python", "is_green": False, "is_digital": True},
            "s2": {"label": "Solar", "is_green": True, "is_digital": False},
            "s3": {"label": "Legacy", "is_green": False, "is_digital": False},
        }
        self.sector_skill_observed = defaultdict(Counter)
        self.sector_skillgroup_observed = defaultdict(Counter)


class _Tracker:
    def __init__(self, jobs=None, responses=None):
        self.jobs = list(jobs or [])
        self.responses = list(responses or [])
        self.payloads = []

    async def fetch_all_jobs(self, payload):
        self.payloads.append(payload)
        if self.responses:
            return self.responses.pop(0)
        return self.jobs

    async def fetch_skill_names(self, skill_ids):
        return None


class _Occupations:
    def get_sector_keys_from_job(self, job, level="nace_section"):
        return list(job.get("sectors", []) or [])

    def get_occupation_ids(self, job):
        return list(job.get("occupation_ids", []) or [])

    def get_sector_keys_from_occupation(self, occupation_id, level="nace_section"):
        return []


def _components(jobs=None, responses=None):
    engine = _Engine()
    tracker = _Tracker(jobs=jobs, responses=responses)
    occupations = _Occupations()
    market = MarketAnalytics(engine, tracker, occupations)
    regional = RegionalAnalytics(engine)
    trends = TrendAnalytics(engine, tracker, market)
    sectoral = SectoralAnalytics(engine, occupations)
    projector = ProjectorService(
        engine,
        tracker,
        occupations,
        regional,
        market,
        trends,
        sectoral,
        None,
    )
    return engine, tracker, market, regional, trends, sectoral, projector


def _wait_for_task(client, status_url):
    for _ in range(1000):
        payload = client.get(status_url).json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.001)
    raise AssertionError("D3.3 compliance task did not finish")


@pytest.mark.asyncio
async def test_d33_cs01_global_skill_ranking_share_and_one_count_per_job():
    jobs = [
        {"skills": ["s1", " s1 ", "s2"], "organization_name": "A", "title": "Dev"},
        {"skills": ["s1"], "organization_name": "B", "title": "Analyst"},
    ]
    _, _, market, _, _, _, _ = _components(jobs)

    result = await market.analyze_market_data(jobs)
    skills = {item["skill_id"]: item for item in result["rankings"]["skills"]}

    assert skills["s1"]["frequency"] == 2
    assert skills["s1"]["share"] == 1.0
    assert skills["s2"]["share"] == 0.5


@pytest.mark.asyncio
async def test_d33_cs02_trends_expose_counts_delta_and_classification():
    jobs = [
        {"upload_date": "2024-01-01", "skills": ["s1", "s1"]},
        {"upload_date": "2024-01-03", "skills": ["s1", "s2"]},
        {"upload_date": "2024-01-04", "skills": ["s1"]},
    ]
    _, _, _, _, trends, _, _ = _components(jobs)

    result = await trends.calculate_trends_from_data(jobs, "2024-01-01", "2024-01-04")
    by_name = {item["name"]: item for item in result["trends"]}

    assert by_name["Python"]["previous_count"] == 1
    assert by_name["Python"]["current_count"] == 2
    assert by_name["Python"]["delta"] == 1
    assert by_name["Python"]["trend_type"] == "emerging"


@pytest.mark.asyncio
async def test_d33_cs03_job_title_and_employer_shares_use_jobs_analyzed():
    jobs = [
        {"skills": [], "organization_name": "A", "title": "Dev"},
        {"skills": [], "organization_name": "A", "title": "Analyst"},
        {"skills": [], "organization_name": "B", "title": "Dev"},
    ]
    _, _, market, _, _, _, _ = _components(jobs)

    result = await market.analyze_market_data(jobs)

    employers = {item["name"]: item for item in result["rankings"]["employers"]}
    titles = {item["name"]: item for item in result["rankings"]["job_titles"]}
    assert employers["A"]["share"] == round(2 / 3, 6)
    assert titles["Dev"]["share"] == round(2 / 3, 6)


def test_d33_cs04_regional_output_exposes_share_baseline_and_specialization():
    jobs = [
        {"location_code": "IT", "nuts1": "ITC", "skills": ["s1", "s1"]},
        {"location_code": "IT", "nuts1": "ITC", "skills": ["s1"]},
        {"location_code": "DE", "nuts1": "DE1", "skills": ["s2"]},
    ]
    _, _, _, regional, _, _, _ = _components(jobs)

    result = regional.get_regional_projections(jobs)
    italy = next(area for area in result["raw"] if area["code"] == "IT")
    python = next(item for item in italy["top_skills"] if item["skill"] == "Python")

    assert python["count"] == 2
    assert python["share"] == 1.0
    assert python["baseline_share"] == round(2 / 3, 6)
    assert python["specialization"] == 1.5


@pytest.mark.asyncio
async def test_d33_cs05_skill_explorer_combines_skill_time_and_nuts_level():
    jobs = [
        {"upload_date": "2024-01-10", "location_code": "IT", "nuts2": "ITC4", "skills": ["s1", "s1"]},
        {"upload_date": "2024-01-11", "location_code": "IT", "nuts2": "ITC4", "skills": ["s2"]},
        {"upload_date": "2024-01-12", "location_code": "DE", "nuts2": "DE11", "skills": ["s1"]},
    ]
    _, _, _, _, _, _, projector = _components(jobs)

    result = await projector.skill_explorer(
        skill_id="s1",
        mode="live",
        min_date="2024-01-01",
        max_date="2024-01-31",
        region_level="nuts2",
    )
    italy = next(item for item in result["regions"] if item["code"] == "ITC4")

    assert result["region_level"] == "nuts2"
    assert result["total_mentions"] == 2
    assert italy["count"] == 1
    assert italy["share"] == 0.5
    assert italy["baseline_share"] == round(2 / 3, 6)
    assert italy["specialization"] == 0.75
    assert italy["rank"] == 1


@pytest.mark.asyncio
async def test_d33_cs06_region_comparison_exposes_combined_baseline():
    jobs = [
        {"location_code": "DK", "nuts2": "DK03", "skills": ["s1", "s1"], "sectors": ["ICT"]},
        {"location_code": "IT", "nuts2": "ITF4", "skills": ["s2"], "sectors": ["Energy"]},
    ]
    _, _, _, _, _, _, projector = _components(jobs)

    result = await projector.compare_regions("DK03", "ITF4", "2024-01-01", "2024-12-31")
    python = next(item for item in result["region_a"]["top_skills"] if item["skill_id"] == "s1")
    delta = next(item for item in result["comparison"]["skills"] if item["skill_id"] == "s1")

    assert python["baseline_share"] == 0.5
    assert python["specialization"] == 2.0
    assert delta["baseline_share"] == 0.5
    assert delta["region_a_rank"] == 1


def test_d33_cs07_sector_skill_cooccurrences_deduplicate_and_keep_fallback_sector():
    _, _, _, _, _, sectoral, _ = _components()

    matrix = sectoral.build_observed_sector_skill_matrix(
        [{"skills": ["s1", "s1", " s1 "]}],
        sector_level="nace_section",
    )

    assert matrix["Sector not specified"]["s1"] == 1


def test_d33_cs08_annual_snapshot_contains_portfolio_titles_and_metadata():
    _, _, _, _, _, _, projector = _components()

    rows = projector._build_sector_snapshot_rows([
        {"title": "Developer", "skills": ["s1", "s1"], "sectors": []},
    ])

    assert rows[0]["sector"] == "Sector not specified"
    assert rows[0]["top_skills"][0]["snapshot_count"] == 1
    assert rows[0]["top_skills"][0]["rank_score"] == 1.0
    assert rows[0]["top_job_titles"][0]["share"] == 1.0


def test_d33_cs09_snapshot_evolution_reports_delta_growth_and_churn():
    _, _, _, _, _, _, projector = _components()
    current = [{
        "sector": "ICT",
        "sector_label": "ICT",
        "job_count": 4,
        "total_skill_mentions": 3,
        "top_job_titles": [],
        "all_skills": [{"skill_id": "s1", "count": 2}, {"skill_id": "s2", "count": 1}],
    }]
    previous = [{
        "sector": "ICT",
        "sector_label": "ICT",
        "job_count": 2,
        "total_skill_mentions": 2,
        "top_job_titles": [],
        "all_skills": [{"skill_id": "s1", "count": 1}, {"skill_id": "s3", "count": 1}],
    }]

    row = projector._enrich_sector_skill_metrics(current, previous, 2023, 4, 2)[0]
    evolution = row["evolution"]

    assert evolution["job_delta"] == 2
    assert evolution["new_skill_count"] == 1
    assert evolution["disappeared_skill_count"] == 1
    assert evolution["growing_skill_count"] == 1
    assert evolution["skill_churn"] > 0


def test_d33_cs10_sector_skill_matrix_has_count_share_rank_and_growth():
    _, _, _, _, _, _, projector = _components()
    sectors = [{
        "sector": "ICT",
        "sector_label": "ICT",
        "total_skill_mentions": 2,
        "all_skills": [{"skill_id": "s1", "label": "Python", "count": 2}],
    }]

    row = projector._build_sector_skill_comparison_matrix(
        sectors,
        [{"skill_id": "s1", "label": "Python", "is_green": False, "is_digital": True}],
        {"ICT": {"s1": 1}},
        "share",
    )[0]

    assert row["count"] == 2
    assert row["share"] == 1.0
    assert row["rank"] == 1
    assert row["rank_score"] == 1.0
    assert row["growth"] == 1.0


def test_d33_cs11_persisted_portfolio_is_enriched_with_rank_score_without_migration():
    _, _, _, _, _, _, projector = _components()
    payload = {
        "status": "completed",
        "total_jobs": 2,
        "sectors": [{
            "sector": "ICT",
            "sector_label": "ICT",
            "job_count": 2,
            "total_skill_mentions": 3,
            "top_job_titles": [],
            "all_skills": [{"skill_id": "s1", "count": 2}, {"skill_id": "s2", "count": 1}],
        }],
    }

    enriched = projector._enrich_sector_snapshot_payload(payload, {"total_jobs": 0, "sectors": []}, 2023)

    assert enriched["sectors"][0]["all_skills"][0]["rank_score"] == 1.0
    assert enriched["sectors"][0]["all_skills"][1]["rank_score"] == 0.5


def test_d33_cs12_persisted_sector_titles_receive_share_and_zero_denominator_guard():
    _, _, _, _, _, _, projector = _components()
    sectors = [{
        "sector": "ICT",
        "sector_label": "ICT",
        "job_count": 4,
        "total_skill_mentions": 0,
        "top_job_titles": [{"name": "Developer", "count": 2}],
        "all_skills": [],
    }, {
        "sector": "Empty",
        "sector_label": "Empty",
        "job_count": 0,
        "total_skill_mentions": 0,
        "top_job_titles": [{"name": "Unknown", "count": 1}],
        "all_skills": [],
    }]

    enriched = projector._enrich_sector_skill_metrics(sectors, [], 2023)

    assert enriched[0]["top_job_titles"][0]["share"] == 0.5
    assert enriched[1]["top_job_titles"][0]["share"] == 0.0


def test_d33_cs13_new_entry_is_explicit_and_preserves_growth_sentinel():
    _, _, _, _, trends, _, _ = _components()
    result = trends._compare_periods(
        {"total_jobs": 1, "rankings": {"skills": []}},
        {"total_jobs": 1, "rankings": {"skills": [{
            "skill_id": "s1",
            "name": "Python",
            "frequency": 1,
            "primary_sector": "ICT",
            "is_green": False,
            "is_digital": True,
        }]}},
    )

    trend = result["trends"][0]
    assert trend["growth"] == "new_entry"
    assert trend["is_new_entry"] is True
    assert trend["previous_count"] == 0
    assert trend["current_count"] == 1


def test_d33_cs14_explicit_period_contract_and_legacy_split_are_disjoint():
    completed = {
        "status": "completed",
        "insights": {
            "market_health": {"status": "stable", "volume_growth_percentage": 0.0},
            "trends": [],
        },
    }
    with patch.object(container_service, "emerging_skills", new_callable=AsyncMock) as operation:
        operation.return_value = completed
        with TestClient(app) as client:
            accepted = client.post("/projector/emerging-skills", data={
                "period_a_min_date": "2024-01-01",
                "period_a_max_date": "2024-01-31",
                "period_b_min_date": "2024-02-01",
                "period_b_max_date": "2024-02-29",
            })
            task = _wait_for_task(client, accepted.json()["status_url"])
            overlap = client.post("/projector/emerging-skills", data={
                "period_a_min_date": "2024-01-01",
                "period_a_max_date": "2024-02-01",
                "period_b_min_date": "2024-02-01",
                "period_b_max_date": "2024-02-29",
            })
            mixed = client.post("/projector/emerging-skills", data={
                "min_date": "2024-01-01",
                "max_date": "2024-02-29",
                "period_a_min_date": "2024-01-01",
                "period_a_max_date": "2024-01-31",
                "period_b_min_date": "2024-02-01",
                "period_b_max_date": "2024-02-29",
            })

    assert accepted.status_code == 202
    assert task["status"] == "completed"
    assert operation.await_args.kwargs["period_b_min_date"] == "2024-02-01"
    assert overlap.status_code == 422
    assert overlap.json()["detail"]["error"]["code"] == "overlapping_trend_periods"
    assert mixed.status_code == 422
    assert mixed.json()["detail"]["error"]["code"] == "mixed_trend_periods"

    _, _, _, _, trends, _, _ = _components()
    period_a, period_b = trends._split_periods("2024-01-01", "2024-01-04")
    assert period_a == ("2024-01-01", "2024-01-02")
    assert period_b == ("2024-01-03", "2024-01-04")


def test_d33_snapshot_skill_explorer_does_not_double_count_multi_sector_jobs(monkeypatch):
    rows = []
    for location_code in (None, "ITC4"):
        for sector in ("ICT", "Education"):
            rows.append({
                "year": 2024,
                "run_id": f"2024-{location_code}",
                "location_code": location_code,
                "total_jobs": 1,
                "sector": sector,
                "sector_label": sector,
                "top_skills": [],
                "all_skills": [{
                    "skill_id": "s1",
                    "label": "Python",
                    "count": 1,
                    "snapshot_count": 1,
                }],
            })

    class _Result:
        def fetchall(self):
            return rows

    class _Connection:
        def execute(self, sql, params):
            return _Result()

    @contextmanager
    def fake_connect():
        yield _Connection()

    store = SectorSnapshotStore("postgresql://test")
    monkeypatch.setattr(store, "_connect", fake_connect)

    result = store.read_skill_distribution(
        skill_id="s1",
        start_year=2024,
        end_year=2024,
        region_level="nuts2",
    )

    assert result["total_mentions"] == 1
    assert result["regions"][0]["count"] == 1
    assert result["regions"][0]["share"] == 1.0
