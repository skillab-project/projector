import argparse
import asyncio
import sys
from datetime import date, datetime
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


def log(message: str):
    timestamp = datetime.now().isoformat(timespec="seconds")
    print(f"[{timestamp}] {message}", flush=True)


def progress_bar(current: int, total: int, width: int = 24):
    if total <= 0:
        return "[------------------------] 0/0"
    filled = round(width * current / total)
    bar = "#" * filled + "-" * (width - filled)
    return f"[{bar}] {current}/{total}"


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
    log(f"year {year}: fetching Tracker jobs")
    jobs = await fetch_jobs_for_year(year)
    log(f"year {year}: fetched {len(jobs)} jobs")
    selected_regions = regions or available_location_codes(jobs)
    log(
        f"year {year}: selected {len(selected_regions)} region(s)"
        f"{' from CLI' if regions else ' from Tracker jobs'}"
    )
    results = []
    total_targets = len(selected_regions) + (1 if include_global else 0)
    current_target = 0

    if include_global:
        current_target += 1
        log(f"year {year}: {progress_bar(current_target, total_targets)} writing GLOBAL snapshot")
        run_id, job_count, sector_count = await write_snapshot_from_jobs(
            service,
            year,
            jobs,
            None,
        )
        results.append((year, "GLOBAL", run_id, job_count, sector_count))
        log(
            f"year {year}: GLOBAL done run_id={run_id} "
            f"jobs={job_count} sectors={sector_count}"
        )

    for region in selected_regions:
        current_target += 1
        region_jobs = filter_jobs_by_location(jobs, region)
        log(
            f"year {year}: {progress_bar(current_target, total_targets)} "
            f"writing region={region} jobs={len(region_jobs)}"
        )
        run_id, job_count, sector_count = await write_snapshot_from_jobs(
            service,
            year,
            region_jobs,
            region,
        )
        results.append((year, region, run_id, job_count, sector_count))
        log(
            f"year {year}: region={region} done run_id={run_id} "
            f"jobs={job_count} sectors={sector_count}"
        )

    return results


async def backfill_snapshots(
        start_year: int,
        end_year: int,
        regions: list[str] | None,
        include_global: bool,
):
    all_results = []
    years = list(range(start_year, end_year + 1))
    log(
        "backfill started: "
        f"years={start_year}-{end_year} "
        f"regions={'auto' if regions is None else ','.join(regions)} "
        f"include_global={include_global}"
    )
    for index, year in enumerate(years, start=1):
        log(f"year progress {progress_bar(index, len(years))} current={year}")
        year_results = await backfill_year(year, regions, include_global)
        all_results.extend(year_results)
        for result in year_results:
            year, region, run_id, job_count, sector_count = result
            log(
                "sector snapshot backfilled: "
                f"year={year} region={region} run_id={run_id} "
                f"jobs={job_count} sectors={sector_count}"
            )
    log(f"backfill completed: snapshots={len(all_results)}")
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
