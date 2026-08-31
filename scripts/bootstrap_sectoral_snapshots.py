import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.backfill_sectoral_snapshots import backfill_snapshots, parse_regions, setup_logging
from scripts.validate_sectoral_snapshot_pipeline import validate_pipeline


def validation_targets(backfill_results: list[tuple]):
    seen = set()
    targets = []
    for year, region, _run_id, _job_count, _sector_count in backfill_results:
        location_code = None if region == "GLOBAL" else region
        key = (int(year), location_code)
        if key not in seen:
            seen.add(key)
            targets.append(key)
    return targets


async def bootstrap_snapshots(
        start_year: int,
        end_year: int,
        regions: list[str] | None,
        include_global: bool,
        page_size: int,
        page_concurrency: int,
        max_retries: int,
        min_sectors: int,
        api_base_url: str | None,
        timeout_seconds: int,
):
    backfilled = await backfill_snapshots(
        start_year=start_year,
        end_year=end_year,
        regions=regions,
        include_global=include_global,
        page_size=page_size,
        page_concurrency=page_concurrency,
        max_retries=max_retries,
    )
    validations = []
    for year, location_code in validation_targets(backfilled):
        validations.append(
            await validate_pipeline(
                year=year,
                location_code=location_code,
                reference_year=year - 1,
                min_sectors=min_sectors,
                api_base_url=api_base_url,
                timeout_seconds=timeout_seconds,
                run_refresh=False,
            )
        )

    return {
        "status": "completed",
        "start_year": start_year,
        "end_year": end_year,
        "snapshots_written": len(backfilled),
        "snapshots_validated": len(validations),
        "backfilled": [
            {
                "year": year,
                "location_code": None if region == "GLOBAL" else region,
                "run_id": run_id,
                "jobs": job_count,
                "sectors": sector_count,
            }
            for year, region, run_id, job_count, sector_count in backfilled
        ],
        "validations": validations,
    }


def main():
    current_year = date.today().year
    parser = argparse.ArgumentParser(
        description="Backfill and validate production sector snapshots in one command."
    )
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, default=current_year)
    parser.add_argument(
        "--regions",
        nargs="*",
        default=None,
        help="Optional region/location codes. Omit to use all location_code values found in Tracker jobs.",
    )
    parser.add_argument("--skip-global", action="store_true")
    parser.add_argument("--page-size", type=int, default=500)
    parser.add_argument("--page-concurrency", type=int, default=4)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--min-sectors", type=int, default=1)
    parser.add_argument("--api-base-url", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--log-file", default="logs/sector_snapshot_bootstrap.log")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if args.end_year < args.start_year:
        raise ValueError("--end-year must be greater than or equal to --start-year")
    if args.page_size < 1:
        raise ValueError("--page-size must be greater than 0")
    if args.page_concurrency < 1:
        raise ValueError("--page-concurrency must be greater than 0")
    if args.max_retries < 1:
        raise ValueError("--max-retries must be greater than 0")
    if args.min_sectors < 1:
        raise ValueError("--min-sectors must be greater than 0")
    if args.timeout_seconds < 1:
        raise ValueError("--timeout-seconds must be greater than 0")

    setup_logging(args.log_file, args.debug)
    result = asyncio.run(
        bootstrap_snapshots(
            start_year=args.start_year,
            end_year=args.end_year,
            regions=parse_regions(args.regions),
            include_global=not args.skip_global,
            page_size=args.page_size,
            page_concurrency=args.page_concurrency,
            max_retries=args.max_retries,
            min_sectors=args.min_sectors,
            api_base_url=args.api_base_url,
            timeout_seconds=args.timeout_seconds,
        )
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":  # pragma: no cover
    main()
