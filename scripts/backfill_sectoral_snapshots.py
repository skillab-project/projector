import argparse
import asyncio
import logging
import sys
import time
from datetime import date, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.refresh_sectoral_snapshot import (
    available_location_codes,
    build_projector_service,
    filter_jobs_by_location,
    year_window,
    write_snapshot_from_jobs,
)


LOGGER_NAME = "sector_snapshot_backfill"
logger = logging.getLogger(LOGGER_NAME)
DEFAULT_PROGRESS_BAR_WIDTH = 24
DEFAULT_PAGE_SIZE = 500
DEFAULT_PAGE_CONCURRENCY = 1
DEFAULT_MAX_RETRIES = 5


def setup_logging(log_file: str, debug: bool):
    log_path = Path(log_file)
    if not log_path.is_absolute():
        log_path = REPO_ROOT / log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if debug else logging.INFO)
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)
    logger.info("logging initialized: file=%s debug=%s", log_path, debug)


def progress_bar(current: int, total: int, width: int | None = None):
    if width is None:
        width = DEFAULT_PROGRESS_BAR_WIDTH
    if total <= 0:
        return "[------------------------] 0/0"
    filled = round(width * current / total)
    bar = "#" * filled + "-" * (width - filled)
    return f"[{bar}] {current}/{total}"


def fetch_progress_message(year: int, progress: dict, started_at: float):
    fetched = int(progress.get("fetched", 0) or 0)
    total = int(progress.get("total", 0) or 0)
    page = progress.get("page", "?")
    concurrency = progress.get("page_concurrency", 1)
    source = progress.get("source", "tracker")
    elapsed = time.perf_counter() - started_at
    return (
        f"year {year}: fetching Tracker jobs "
        f"{progress_bar(fetched, total)} page={page} "
        f"concurrency={concurrency} source={source} elapsed={elapsed:.1f}s"
    )


def year_filters(year: int):
    min_date, max_date = year_window(year)
    return {
        "min_upload_date": min_date,
        "max_upload_date": max_date,
    }


async def fetch_jobs_for_year_with_progress(
        service,
        year: int,
        page_size: int,
        page_concurrency: int,
        max_retries: int,
):
    min_date, max_date = year_window(year)
    filters = year_filters(year)
    started_at = time.perf_counter()
    latest_progress = {
        "fetched": 0,
        "total": 0,
        "page": None,
        "source": "tracker",
    }

    def on_progress(progress: dict):
        latest_progress.update(progress)
        message = fetch_progress_message(year, progress, started_at)
        if progress.get("done"):
            logger.info(message)
        else:
            logger.info(message)
            logger.debug("year %s fetch progress payload=%s", year, progress)

    logger.info("year %s: fetch started window=%s..%s", year, min_date, max_date)
    try:
        jobs = await service.tracker.fetch_all_jobs(
            filters,
            page_size=page_size,
            progress_callback=on_progress,
            page_concurrency=page_concurrency,
            max_retries=max_retries,
            require_complete_cache=True,
        )
    except Exception as exc:
        store = getattr(service, "sector_snapshot_store", None)
        if store and getattr(store, "enabled", False):
            store.write_refresh_status(
                year=year,
                location_code=None,
                status="failed",
                last_error=str(exc),
                last_checkpoint_page=latest_progress.get("page"),
                fetched_jobs=int(latest_progress.get("fetched") or 0),
                expected_jobs=int(latest_progress.get("total") or 0),
                source=latest_progress.get("source"),
            )
        raise
    elapsed = time.perf_counter() - started_at
    logger.info("year %s: fetch completed jobs=%s elapsed=%.1fs", year, len(jobs), elapsed)
    return jobs, elapsed


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
        page_size: int,
        page_concurrency: int,
        max_retries: int,
):
    service = build_projector_service()
    jobs, fetch_elapsed = await fetch_jobs_for_year_with_progress(
        service,
        year,
        page_size,
        page_concurrency,
        max_retries,
    )
    logger.info("year %s: fetched %s jobs in %.1fs", year, len(jobs), fetch_elapsed)
    selected_regions = regions or available_location_codes(jobs)
    logger.info(
        "year %s: selected %s region(s) %s",
        year,
        len(selected_regions),
        "from CLI" if regions else "from Tracker jobs",
    )
    results = []
    total_targets = len(selected_regions) + (1 if include_global else 0)
    current_target = 0

    if include_global:
        current_target += 1
        logger.info(
            "year %s: %s writing GLOBAL snapshot",
            year,
            progress_bar(current_target, total_targets),
        )
        run_id, job_count, sector_count = await write_snapshot_from_jobs(
            service,
            year,
            jobs,
            None,
        )
        results.append((year, "GLOBAL", run_id, job_count, sector_count))
        logger.info(
            "year %s: GLOBAL done run_id=%s jobs=%s sectors=%s",
            year,
            run_id,
            job_count,
            sector_count,
        )

    for region in selected_regions:
        current_target += 1
        region_jobs = filter_jobs_by_location(jobs, region)
        logger.info(
            "year %s: %s writing region=%s jobs=%s",
            year,
            progress_bar(current_target, total_targets),
            region,
            len(region_jobs),
        )
        run_id, job_count, sector_count = await write_snapshot_from_jobs(
            service,
            year,
            region_jobs,
            region,
        )
        results.append((year, region, run_id, job_count, sector_count))
        logger.info(
            "year %s: region=%s done run_id=%s jobs=%s sectors=%s",
            year,
            region,
            run_id,
            job_count,
            sector_count,
        )

    service.tracker.clear_completed_jobs_cache(year_filters(year))
    logger.info("year %s: completed raw Tracker jobs cache deleted", year)

    return results


async def backfill_snapshots(
        start_year: int,
        end_year: int,
        regions: list[str] | None,
        include_global: bool,
        page_size: int | None = None,
        page_concurrency: int | None = None,
        max_retries: int | None = None,
):
    page_size = DEFAULT_PAGE_SIZE if page_size is None else page_size
    page_concurrency = DEFAULT_PAGE_CONCURRENCY if page_concurrency is None else page_concurrency
    max_retries = DEFAULT_MAX_RETRIES if max_retries is None else max_retries

    if not logger.handlers:
        setup_logging("logs/sector_snapshot_backfill.log", False)

    all_results = []
    years = list(range(start_year, end_year + 1))
    started_at = time.perf_counter()
    logger.info(
        "backfill started: years=%s-%s regions=%s include_global=%s",
        start_year,
        end_year,
        "auto" if regions is None else ",".join(regions),
        include_global,
    )
    logger.info(
        "fetch config: page_size=%s page_concurrency=%s max_retries=%s",
        page_size,
        page_concurrency,
        max_retries,
    )
    for index, year in enumerate(years, start=1):
        logger.info("year progress %s current=%s", progress_bar(index, len(years)), year)
        try:
            year_results = await backfill_year(
                year,
                regions,
                include_global,
                page_size,
                page_concurrency,
                max_retries,
            )
        except Exception:
            logger.exception("year %s: backfill failed", year)
            raise
        all_results.extend(year_results)
        for result in year_results:
            year, region, run_id, job_count, sector_count = result
            logger.info(
                "sector snapshot backfilled: year=%s region=%s run_id=%s jobs=%s sectors=%s",
                year,
                region,
                run_id,
                job_count,
                sector_count,
            )
    elapsed = time.perf_counter() - started_at
    logger.info("backfill completed: snapshots=%s elapsed=%.1fs", len(all_results), elapsed)
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
    parser.add_argument(
        "--log-file",
        default="logs/sector_snapshot_backfill.log",
        help="Rotating log file path.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable DEBUG logs on console and file.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=500,
        help="Requested Tracker page size.",
    )
    parser.add_argument(
        "--page-concurrency",
        type=int,
        default=1,
        help="Number of Tracker job pages to fetch in parallel.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Retries per Tracker page before checkpointing and failing.",
    )
    args = parser.parse_args()

    if args.end_year < args.start_year:
        raise ValueError("--end-year must be greater than or equal to --start-year")
    if args.page_size < 1:
        raise ValueError("--page-size must be greater than 0")
    if args.page_concurrency < 1:
        raise ValueError("--page-concurrency must be greater than 0")
    if args.max_retries < 1:
        raise ValueError("--max-retries must be greater than 0")

    setup_logging(args.log_file, args.debug)
    asyncio.run(
        backfill_snapshots(
            start_year=args.start_year,
            end_year=args.end_year,
            regions=parse_regions(args.regions),
            include_global=not args.skip_global,
            page_size=args.page_size,
            page_concurrency=args.page_concurrency,
            max_retries=args.max_retries,
        )
    )


if __name__ == "__main__":  # pragma: no cover
    main()
