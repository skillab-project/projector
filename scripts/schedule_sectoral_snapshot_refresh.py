import argparse
import asyncio
import os
import sys
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.backfill_sectoral_snapshots import backfill_snapshots, parse_regions


SECONDS_PER_MONTH = 30 * 24 * 60 * 60


def env_int(name: str, default: int):
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return int(value)


def env_bool(name: str, default: bool):
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_regions(name: str):
    value = os.getenv(name)
    if not value:
        return None
    return parse_regions([value])


async def run_scheduled_refresh(
        start_year: int,
        end_year: int,
        interval_months: int,
        regions: list[str] | None,
        include_global: bool,
        run_immediately: bool,
        page_size: int,
        page_concurrency: int,
        max_retries: int,
):
    if interval_months <= 0:
        raise ValueError("--interval-months must be greater than 0")

    interval_seconds = interval_months * SECONDS_PER_MONTH

    if not run_immediately:
        await asyncio.sleep(interval_seconds)

    while True:
        started_at = datetime.now().isoformat(timespec="seconds")
        print(
            "scheduled sector snapshot refresh started: "
            f"at={started_at} years={start_year}-{end_year} "
            f"interval_months={interval_months}"
        )
        await backfill_snapshots(
            start_year=start_year,
            end_year=end_year,
            regions=regions,
            include_global=include_global,
            page_size=page_size,
            page_concurrency=page_concurrency,
            max_retries=max_retries,
        )
        finished_at = datetime.now().isoformat(timespec="seconds")
        print(f"scheduled sector snapshot refresh completed: at={finished_at}")
        await asyncio.sleep(interval_seconds)


def main():
    current_year = date.today().year
    parser = argparse.ArgumentParser(
        description="Run recurring sector snapshot refreshes every N months."
    )
    parser.add_argument("--interval-months", type=int, default=env_int("SNAPSHOT_INTERVAL_MONTHS", 3))
    parser.add_argument("--start-year", type=int, default=env_int("SNAPSHOT_START_YEAR", current_year))
    parser.add_argument("--end-year", type=int, default=env_int("SNAPSHOT_END_YEAR", current_year))
    parser.add_argument(
        "--regions",
        nargs="*",
        default=env_regions("SNAPSHOT_REGIONS"),
        help="Optional region/location codes. Omit to use all location_code values found in the yearly jobs.",
    )
    parser.add_argument(
        "--skip-global",
        action="store_true",
        default=env_bool("SNAPSHOT_SKIP_GLOBAL", False),
        help="Do not write the global yearly snapshot.",
    )
    parser.add_argument(
        "--no-run-immediately",
        action="store_true",
        default=not env_bool("SNAPSHOT_RUN_IMMEDIATELY", True),
        help="Wait one interval before the first refresh.",
    )
    parser.add_argument("--page-size", type=int, default=env_int("SNAPSHOT_PAGE_SIZE", 500))
    parser.add_argument("--page-concurrency", type=int, default=env_int("SNAPSHOT_PAGE_CONCURRENCY", 4))
    parser.add_argument("--max-retries", type=int, default=env_int("SNAPSHOT_MAX_RETRIES", 5))
    args = parser.parse_args()

    if args.end_year < args.start_year:
        raise ValueError("--end-year must be greater than or equal to --start-year")
    if args.page_size < 1:
        raise ValueError("--page-size must be greater than 0")
    if args.page_concurrency < 1:
        raise ValueError("--page-concurrency must be greater than 0")
    if args.max_retries < 1:
        raise ValueError("--max-retries must be greater than 0")

    try:
        asyncio.run(
            run_scheduled_refresh(
                start_year=args.start_year,
                end_year=args.end_year,
                interval_months=args.interval_months,
                regions=parse_regions(args.regions),
                include_global=not args.skip_global,
                run_immediately=not args.no_run_immediately,
                page_size=args.page_size,
                page_concurrency=args.page_concurrency,
                max_retries=args.max_retries,
            )
        )
    except KeyboardInterrupt:
        print("scheduled sector snapshot refresh stopped")


if __name__ == "__main__":
    main()
