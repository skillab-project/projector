import argparse
import asyncio

from app.core.config import DATABASE_URL
from app.core.container import engine, tracker, occupations, regional, market, trends, sectoral
from app.services.projector_service import ProjectorService
from app.services.sector_snapshot_store import SectorSnapshotStore


async def refresh_snapshot(year: int, location_code: str | None):
    store = SectorSnapshotStore(DATABASE_URL)
    if not store.enabled:
        raise RuntimeError("DATABASE_URL not configured")

    service = ProjectorService(
        engine,
        tracker,
        occupations,
        regional,
        market,
        trends,
        sectoral,
        store,
    )

    min_date = f"{year:04d}-01-01"
    max_date = f"{year:04d}-12-31"
    filters = {
        "min_upload_date": min_date,
        "max_upload_date": max_date,
    }
    if location_code:
        filters["location_code"] = [location_code]

    jobs = await tracker.fetch_all_jobs(filters)
    await service._ensure_skill_labels(jobs)
    sectors = service._build_sector_snapshot_rows(jobs)

    run_id = store.write_snapshot(
        year=year,
        location_code=location_code,
        period_start=min_date,
        period_end=max_date,
        total_jobs=len(jobs),
        sectors=sectors,
    )
    return run_id, len(jobs), len(sectors)


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


if __name__ == "__main__":
    main()
