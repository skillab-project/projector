import argparse
import asyncio
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.config import DATABASE_URL
from app.services.sector_snapshot_store import SectorSnapshotStore
from scripts.backfill_sectoral_snapshots import backfill_snapshots, parse_regions


SECONDS_PER_MONTH = 30 * 24 * 60 * 60
SECONDS_PER_DAY = 24 * 60 * 60


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


def normalize_completed_at(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def snapshot_targets(start_year: int, end_year: int, regions: list[str] | None, include_global: bool):
    targets = []
    for year in range(start_year, end_year + 1):
        if include_global:
            targets.append((year, None))
        for region in regions or []:
            targets.append((year, region))
    return targets


def due_targets(
        store: SectorSnapshotStore,
        start_year: int,
        end_year: int,
        regions: list[str] | None,
        include_global: bool,
        interval_months: int,
        now: datetime | None = None,
):
    now = now or datetime.now(timezone.utc)
    threshold_seconds = interval_months * SECONDS_PER_MONTH
    targets = snapshot_targets(start_year, end_year, regions, include_global)
    if not targets:
        return [("unknown", "auto")]

    due = []
    for year, location_code in targets:
        completed_at = normalize_completed_at(store.latest_completed_at(year, location_code))
        if not completed_at:
            due.append((year, location_code or "GLOBAL"))
            continue
        if (now - completed_at).total_seconds() >= threshold_seconds:
            due.append((year, location_code or "GLOBAL"))
    return due


async def run_scheduled_refresh(
        start_year: int,
        end_year: int,
        interval_months: int,
        check_interval_days: int,
        regions: list[str] | None,
        include_global: bool,
        run_immediately: bool,
        page_size: int,
        page_concurrency: int,
        max_retries: int,
):
    if interval_months <= 0:
        raise ValueError("--interval-months must be greater than 0")
    if check_interval_days <= 0:
        raise ValueError("--check-interval-days must be greater than 0")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not configured")

    store = SectorSnapshotStore(DATABASE_URL)
    check_interval_seconds = check_interval_days * SECONDS_PER_DAY

    if not run_immediately:
        await asyncio.sleep(check_interval_seconds)

    while True:
        started_at = datetime.now().isoformat(timespec="seconds")
        due = due_targets(
            store,
            start_year,
            end_year,
            regions,
            include_global,
            interval_months,
        )
        if due:
            print(
                "scheduled sector snapshot refresh due: "
                f"at={started_at} years={start_year}-{end_year} "
                f"interval_months={interval_months} due={due}"
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
        else:
            print(
                "scheduled sector snapshot refresh skipped: "
                f"at={started_at} years={start_year}-{end_year} "
                f"interval_months={interval_months} next_check_days={check_interval_days}"
            )
        await asyncio.sleep(check_interval_seconds)


def main():
    current_year = date.today().year
    parser = argparse.ArgumentParser(
        description="Run recurring sector snapshot refreshes every N months."
    )
    parser.add_argument("--interval-months", type=int, default=env_int("SNAPSHOT_INTERVAL_MONTHS", 3))
    parser.add_argument("--check-interval-days", type=int, default=env_int("SNAPSHOT_CHECK_INTERVAL_DAYS", 1))
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
    if args.interval_months < 1:
        raise ValueError("--interval-months must be greater than 0")
    if args.check_interval_days < 1:
        raise ValueError("--check-interval-days must be greater than 0")
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
                check_interval_days=args.check_interval_days,
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
