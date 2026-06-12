import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.refresh_sectoral_snapshot import build_projector_service, refresh_snapshot


REQUIRED_SECTOR_FIELDS = {
    "sector",
    "sector_label",
    "job_count",
    "job_share",
    "total_skill_mentions",
    "unique_skills",
    "top_skills",
    "all_skills",
    "top_job_titles",
}


def location_payload(location_code: Optional[str]):
    return [location_code] if location_code else None


def assert_completed_snapshot(payload: dict, year: int, min_sectors: int):
    if not payload:
        raise RuntimeError(f"No completed DB snapshot found for year={year}")
    if payload.get("status") != "completed":
        raise RuntimeError(f"Snapshot status is not completed: {payload.get('status')}")
    if payload.get("data_source") != "postgres":
        raise RuntimeError(f"Snapshot is not DB-backed: {payload.get('data_source')}")
    if int(payload.get("year") or 0) != int(year):
        raise RuntimeError(f"Snapshot year mismatch: {payload.get('year')} != {year}")

    sectors = payload.get("sectors") or []
    if len(sectors) < min_sectors:
        raise RuntimeError(f"Snapshot has too few sectors: {len(sectors)} < {min_sectors}")

    missing = REQUIRED_SECTOR_FIELDS - set(sectors[0])
    if missing:
        raise RuntimeError(f"Snapshot sector row misses fields: {sorted(missing)}")
    return sectors


def assert_comparison_payload(payload: dict, year: int):
    if payload.get("status") != "completed":
        raise RuntimeError(f"Comparison status is not completed: {payload.get('status')}")
    if payload.get("data_source") != "postgres":
        raise RuntimeError(f"Comparison is not DB-backed: {payload.get('data_source')}")
    if int(payload.get("year") or 0) != int(year):
        raise RuntimeError(f"Comparison year mismatch: {payload.get('year')} != {year}")
    if not payload.get("matrix"):
        raise RuntimeError("Comparison matrix is empty")


def assert_http_response(response, endpoint: str):
    if response.status_code != 200:
        raise RuntimeError(f"{endpoint} returned HTTP {response.status_code}: {response.text[:500]}")
    return response.json()


def post_form(api_base_url: str, endpoint: str, data: dict, timeout_seconds: int):
    url = f"{api_base_url.rstrip('/')}/projector/{endpoint.lstrip('/')}"
    return assert_http_response(requests.post(url, data=data, timeout=timeout_seconds), endpoint)


async def validate_pipeline(
        year: int,
        location_code: Optional[str] = None,
        reference_year: Optional[int] = None,
        min_sectors: int = 1,
        api_base_url: Optional[str] = None,
        timeout_seconds: int = 60,
        run_refresh: bool = False,
):
    if run_refresh:
        await refresh_snapshot(year, location_code)

    service = build_projector_service()
    service.sector_snapshot_store.ensure_schema()
    locations = location_payload(location_code)

    db_snapshot = service.sector_snapshot_store.read_latest(year, location_code)
    sectors = assert_completed_snapshot(db_snapshot, year, min_sectors)

    service_snapshot = await service.sectoral_snapshot(
        year=year,
        reference_year=reference_year,
        locations=locations,
    )
    assert_completed_snapshot(service_snapshot, year, min_sectors)

    selected_sector = sectors[0]["sector_label"]
    selected_skill_row = (sectors[0].get("all_skills") or sectors[0].get("top_skills") or [{}])[0]
    selected_skill = selected_skill_row.get("label") or selected_skill_row.get("skill_id")
    comparison = await service.sector_skills_comparison(
        year=year,
        reference_year=reference_year,
        locations=locations,
        sectors=[selected_sector],
        skills=[selected_skill] if selected_skill else None,
        metric="share",
    )
    assert_comparison_payload(comparison, year)

    http_snapshot = None
    http_comparison = None
    if api_base_url:
        form = {"year": year}
        if reference_year is not None:
            form["reference_year"] = reference_year
        if location_code:
            form["locations"] = location_code
        http_snapshot = post_form(api_base_url, "sectoral-snapshot", form, timeout_seconds)
        assert_completed_snapshot(http_snapshot, year, min_sectors)

        comparison_form = {**form, "sectors": selected_sector, "metric": "share"}
        if selected_skill:
            comparison_form["skills"] = selected_skill
        http_comparison = post_form(api_base_url, "sector-skills-comparison", comparison_form, timeout_seconds)
        assert_comparison_payload(http_comparison, year)

    return {
        "status": "completed",
        "year": year,
        "location_code": location_code,
        "reference_year": reference_year,
        "sectors": len(sectors),
        "total_jobs": db_snapshot.get("total_jobs", 0),
        "sample_sector": selected_sector,
        "sample_skill": selected_skill,
        "db_snapshot": True,
        "service_snapshot": True,
        "service_comparison": True,
        "http_snapshot": bool(http_snapshot),
        "http_comparison": bool(http_comparison),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Validate the sector snapshot refresh pipeline end-to-end."
    )
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--location-code", default=None)
    parser.add_argument("--reference-year", type=int, default=None)
    parser.add_argument("--min-sectors", type=int, default=1)
    parser.add_argument("--api-base-url", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Fetch Tracker data and refresh the DB snapshot before validating.",
    )
    args = parser.parse_args()

    if args.min_sectors < 1:
        raise ValueError("--min-sectors must be greater than 0")
    if args.timeout_seconds < 1:
        raise ValueError("--timeout-seconds must be greater than 0")

    result = asyncio.run(
        validate_pipeline(
            year=args.year,
            location_code=args.location_code,
            reference_year=args.reference_year,
            min_sectors=args.min_sectors,
            api_base_url=args.api_base_url,
            timeout_seconds=args.timeout_seconds,
            run_refresh=args.refresh,
        )
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":  # pragma: no cover
    main()
