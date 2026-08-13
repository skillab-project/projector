import argparse
import asyncio
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.config import DATABASE_URL
from app.core.container import engine, tracker, occupations, regional, market, trends, sectoral
from app.services.projector_service import ProjectorService
from app.services.sector_snapshot_store import SectorSnapshotStore


def build_projector_service():
    store = SectorSnapshotStore(DATABASE_URL)
    if not store.enabled:
        raise RuntimeError("DATABASE_URL not configured")

    return ProjectorService(
        engine,
        tracker,
        occupations,
        regional,
        market,
        trends,
        sectoral,
        store,
    )


def year_window(year: int):
    return f"{year:04d}-01-01", f"{year:04d}-12-31"


def filter_jobs_by_location(jobs: Iterable[dict], location_code: str | None):
    if not location_code:
        return list(jobs)
    return [
        job for job in jobs
        if str(job.get("location_code") or "").strip() == location_code
    ]


def available_location_codes(jobs: Iterable[dict]):
    return sorted({
        str(job.get("location_code") or "").strip()
        for job in jobs
        if str(job.get("location_code") or "").strip()
    })


async def fetch_jobs_for_year(year: int, location_code: str | None = None):
    return await tracker.fetch_all_jobs(year_filters(year, location_code))


def year_filters(year: int, location_code: str | None = None):
    min_date = f"{year:04d}-01-01"
    max_date = f"{year:04d}-12-31"
    filters = {
        "min_upload_date": min_date,
        "max_upload_date": max_date,
    }
    if location_code:
        filters["location_code"] = [location_code]
    return filters


async def write_snapshot_from_jobs(
        service: ProjectorService,
        year: int,
        jobs: list[dict],
        location_code: str | None,
):
    min_date, max_date = year_window(year)
    await service._ensure_skill_labels(jobs)
    sectors = service._build_sector_snapshot_rows(jobs)

    run_id = service.sector_snapshot_store.write_snapshot(
        year=year,
        location_code=location_code,
        period_start=min_date,
        period_end=max_date,
        total_jobs=len(jobs),
        sectors=sectors,
    )
    return run_id, len(jobs), len(sectors)


async def refresh_snapshot(year: int, location_code: str | None):
    service = build_projector_service()
    jobs = await fetch_jobs_for_year(year, location_code)
    result = await write_snapshot_from_jobs(service, year, jobs, location_code)
    tracker.clear_completed_jobs_cache(year_filters(year, location_code))
    return result


def main():
    parser = argparse.ArgumentParser(description="Refresh yearly sector snapshot dataset")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--location-code", default=None)
    args = parser.parse_args()

    run_id, job_count, sector_count = asyncio.run(
        refresh_snapshot(args.year, args.location_code)
    )
    print(
        f"sector snapshot refreshed: run_id={run_id} "
        f"year={args.year} jobs={job_count} sectors={sector_count}"
    )


if __name__ == "__main__":  # pragma: no cover
    main()
