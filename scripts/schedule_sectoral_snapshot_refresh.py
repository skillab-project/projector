import argparse
import asyncio
import sys
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.backfill_sectoral_snapshots import backfill_snapshots, parse_regions


SECONDS_PER_MONTH = 30 * 24 * 60 * 60


async def run_scheduled_refresh(
        start_year: int,
        end_year: int,
        interval_months: int,
        regions: list[str] | None,
        include_global: bool,
        run_immediately: bool,
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
        )
        finished_at = datetime.now().isoformat(timespec="seconds")
        print(f"scheduled sector snapshot refresh completed: at={finished_at}")
        await asyncio.sleep(interval_seconds)


def main():
    current_year = date.today().year
    parser = argparse.ArgumentParser(
        description="Run recurring sector snapshot refreshes every N months."
    )
    parser.add_argument("--interval-months", type=int, default=3)
    parser.add_argument("--start-year", type=int, default=current_year)
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
    parser.add_argument(
        "--no-run-immediately",
        action="store_true",
        help="Wait one interval before the first refresh.",
    )
    args = parser.parse_args()

    if args.end_year < args.start_year:
        raise ValueError("--end-year must be greater than or equal to --start-year")

    try:
        asyncio.run(
            run_scheduled_refresh(
                start_year=args.start_year,
                end_year=args.end_year,
                interval_months=args.interval_months,
                regions=parse_regions(args.regions),
                include_global=not args.skip_global,
                run_immediately=not args.no_run_immediately,
            )
        )
    except KeyboardInterrupt:
        print("scheduled sector snapshot refresh stopped")


if __name__ == "__main__":
    main()
