# Production Sector Snapshots

Runbook for bootstrapping and maintaining PostgreSQL sector snapshots.

Related issues: #61, #54, #55, #13.

## Inputs

Required:

```text
DATABASE_URL
TRACKER_API_URL
TRACKER_API_TOKEN
```

Optional:

| Variable | Default | Meaning |
| --- | --- | --- |
| `SNAPSHOT_START_YEAR` | current year | first year to refresh |
| `SNAPSHOT_END_YEAR` | current year | last year to refresh |
| `SNAPSHOT_REGIONS` | auto | comma-separated region/location codes |
| `SNAPSHOT_INTERVAL_MONTHS` | `3` | refresh interval |
| `SNAPSHOT_CHECK_INTERVAL_DAYS` | `1` | scheduler check interval |
| `SNAPSHOT_PAGE_SIZE` | `500` | Tracker page size |
| `SNAPSHOT_PAGE_CONCURRENCY` | `4` | parallel Tracker pages |
| `SNAPSHOT_MAX_RETRIES` | `5` | retries per page |
| `SNAPSHOT_SCHEDULER_LOG_FILE` | `logs/sector_snapshot_scheduler.log` | rotating scheduler log |
| `SNAPSHOT_DEBUG` | `false` | verbose scheduler console logs |

## Bootstrap

Start DB:

```bash
docker compose up -d projector-db
```

Backfill real snapshots:

```bash
export DATABASE_URL=postgresql://skillab:skillab@localhost:5433/skillab_projector
python scripts/backfill_sectoral_snapshots.py \
  --start-year 2020 \
  --end-year 2024 \
  --page-size 500 \
  --page-concurrency 4 \
  --log-file logs/sector_snapshot_backfill.log
```

Omit `--regions` to write:

- one global snapshot per year
- one regional snapshot per `location_code` found in Tracker jobs

## Validate

DB only:

```bash
python scripts/validate_sectoral_snapshot_pipeline.py --year 2024
```

DB plus running API:

```bash
python scripts/validate_sectoral_snapshot_pipeline.py \
  --year 2024 \
  --api-base-url http://127.0.0.1:8000
```

Regional:

```bash
python scripts/validate_sectoral_snapshot_pipeline.py \
  --year 2024 \
  --location-code IT
```

## Scheduler

Local Python:

```bash
python scripts/schedule_sectoral_snapshot_refresh.py \
  --start-year 2020 \
  --end-year 2024 \
  --interval-months 3
```

Docker:

```bash
docker compose up -d projector-db projector-snapshot-refresh
```

The scheduler checks periodically and runs backfill only when the latest completed snapshot for a target is older than the configured interval.

## Logs

Backfill log:

```text
logs/sector_snapshot_backfill.log
```

Scheduler log:

```text
logs/sector_snapshot_scheduler.log
```

Docker logs:

```bash
docker compose logs -f projector-snapshot-refresh
```

Both scripts use rotating logs and emit `INFO`, `DEBUG`, and `ERROR` entries.

## Recovery

If Tracker fetch fails, rerun the same command. Partial page fetches are checkpointed in:

```text
cache_data/
```

Failed or running snapshot runs are ignored by dashboard reads. The API always reads the latest completed run for `(year, location_code)`.
