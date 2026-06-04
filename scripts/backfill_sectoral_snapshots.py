import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.refresh_sectoral_snapshot import (
    available_location_codes,
    build_projector_service,
    fetch_jobs_for_year,
    filter_jobs_by_location,
    write_snapshot_from_jobs,
)


def parse_regions(values: list[str] | None):
    if not values:
        return None
    regions = []
    for value in values:
        regions.extend(part.strip() for part in value.split(",") if part.strip())
    return sorted(set(regions))


async def backfill_year(
        year: int,
        regions: list[str] | None,
        include_global: bool,
):
    service = build_projector_service()
    jobs = await fetch_jobs_for_year(year)
    selected_regions = regions or available_location_codes(jobs)
    results = []

    if include_global:
        run_id, job_count, sector_count = await write_snapshot_from_jobs(
            service,
            year,
            jobs,
            None,
        )
        results.append((year, "GLOBAL", run_id, job_count, sector_count))

    for region in selected_regions:
        region_jobs = filter_jobs_by_location(jobs, region)
        run_id, job_count, sector_count = await write_snapshot_from_jobs(
            service,
            year,
            region_jobs,
            region,
        )
        results.append((year, region, run_id, job_count, sector_count))

    return results


async def backfill_snapshots(
        start_year: int,
        end_year: int,
        regions: list[str] | None,
        include_global: bool,
):
    all_results = []
    for year in range(start_year, end_year + 1):
        year_results = await backfill_year(year, regions, include_global)
        all_results.extend(year_results)
        for result in year_results:
            year, region, run_id, job_count, sector_count = result
            print(
                "sector snapshot backfilled: "
                f"year={year} region={region} run_id={run_id} "
                f"jobs={job_count} sectors={sector_count}"
            )
    return all_results


def main():
    current_year = date.today().year
    parser = argparse.ArgumentParser(
        description="Backfill yearly sector snapshots for all available Tracker regions."
    )
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, default=current_year)
    parser.add_argument(
        "--regions",
        nargs="*",
        default=None,
        help="Optional region/location codes. Omit to use all location_code values found in the yearly jobs.",
    )
    parser.add_argument(
        "--skip-global",
        action="store_true",
        help="Do not write the global yearly snapshot.",
    )
    args = parser.parse_args()

    if args.end_year < args.start_year:
        raise ValueError("--end-year must be greater than or equal to --start-year")

    asyncio.run(
        backfill_snapshots(
            start_year=args.start_year,
            end_year=args.end_year,
            regions=parse_regions(args.regions),
            include_global=not args.skip_global,
        )
    )


if __name__ == "__main__":
    main()
