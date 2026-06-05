# Database

PostgreSQL stores yearly sector snapshots used by Sector Overview and Sector Skills Comparison.

Related issues: #44, #54.

## Local DB

```bash
docker compose up -d projector-db
```

```text
DATABASE_URL=postgresql://skillab:skillab@localhost:5433/skillab_projector
```

The local Docker DB runs migrations from:

```text
migrations/
```

## Tables

### `sector_snapshot_runs`

One row per refresh run.

| Column | Type | Meaning |
| --- | --- | --- |
| `id` | `BIGSERIAL` | run id |
| `year` | `INTEGER` | snapshot year |
| `location_code` | `TEXT` | optional region/location |
| `version` | `INTEGER` | version for year/location |
| `status` | `TEXT` | run status |
| `period_start` | `DATE` | start date |
| `period_end` | `DATE` | end date |
| `total_jobs` | `INTEGER` | jobs processed |
| `created_at` | `TIMESTAMPTZ` | run creation |
| `completed_at` | `TIMESTAMPTZ` | run completion |
| `message` | `TEXT` | optional note |

Indexes:

```text
ux_sector_snapshot_runs_version(year, location_code, version)
ix_sector_snapshot_runs_latest(year, location_code, status, completed_at, id)
```

### `sector_yearly_snapshots`

One row per sector in a completed run.

| Column | Type | Meaning |
| --- | --- | --- |
| `run_id` | `BIGINT` | parent run |
| `year` | `INTEGER` | snapshot year |
| `location_code` | `TEXT` | optional region/location |
| `sector` | `TEXT` | Tracker sector |
| `sector_label` | `TEXT` | display label |
| `job_count` | `INTEGER` | jobs linked to sector |
| `job_share` | `DOUBLE PRECISION` | sector share |
| `total_skill_mentions` | `INTEGER` | sector-skill events |
| `unique_skills` | `INTEGER` | distinct sector skills |
| `top_skills` | `JSONB` | top-10 skills |
| `all_skills` | `JSONB` | full skill list |
| `top_job_titles` | `JSONB` | top titles |

Primary key:

```text
(run_id, sector)
```

Lookup index:

```text
ix_sector_yearly_snapshots_lookup(year, location_code, job_count)
```

## Read Behavior

The API reads:

```text
latest completed run for (year, location_code)
```

Failed or running runs do not affect dashboard users.

## Write Behavior

Single-year refresh:

```bash
python scripts/refresh_sectoral_snapshot.py --year 2024
```

Regional refresh:

```bash
python scripts/refresh_sectoral_snapshot.py --year 2024 --location-code IT
```

Full backfill:

```bash
python scripts/backfill_sectoral_snapshots.py --start-year 2020 --end-year 2024
```

This fetches each year once, derives available `location_code` values from Tracker jobs, then writes:

- one global snapshot per year
- one regional snapshot per detected location and year

Tracker job fetch is resumable. During each paginated fetch, partial results are saved to:

```text
cache_data/search_<query_hash>.partial.json
```

If connection fails, rerun the same command. The fetch resumes from the last completed page instead of starting from page 1. Completed fetches are promoted to:

```text
cache_data/search_<query_hash>.json
```

The partial checkpoint is then removed.

Backfill logs include Tracker fetch progress, per-year elapsed time and rotating file logs:

```bash
python scripts/backfill_sectoral_snapshots.py \
  --start-year 2020 \
  --end-year 2024 \
  --log-file logs/sector_snapshot_backfill.log
```

Use `--debug` for DEBUG-level console logs. The log file always receives DEBUG, INFO and ERROR entries and rotates automatically.

For large years, fetch Tracker pages in parallel:

```bash
python scripts/backfill_sectoral_snapshots.py \
  --start-year 2024 \
  --end-year 2024 \
  --page-size 500 \
  --page-concurrency 8 \
  --max-retries 5
```

Use moderate concurrency first (`4` or `8`). Higher values can overload Tracker or trigger rate limits.

Recurring refresh:

```bash
python scripts/schedule_sectoral_snapshot_refresh.py --interval-months 3
```

This runs the backfill logic repeatedly. By default it refreshes the current year every 3 months.

Docker scheduler service:

```bash
docker compose up -d projector-db projector-snapshot-refresh
```

It runs the scheduler as a long-running container. Defaults:

- current year
- run immediately on start
- repeat every 3 months
- global snapshot plus detected regions
- resumable cache in `/workspace/cache_data`
- rotating logs in `/workspace/logs`

Configure with environment variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `SNAPSHOT_INTERVAL_MONTHS` | `3` | scheduler interval |
| `SNAPSHOT_START_YEAR` | current year | first year |
| `SNAPSHOT_END_YEAR` | current year | last year |
| `SNAPSHOT_REGIONS` | auto | comma-separated location codes |
| `SNAPSHOT_SKIP_GLOBAL` | `false` | skip global snapshot |
| `SNAPSHOT_RUN_IMMEDIATELY` | `true` | run at startup |
| `SNAPSHOT_PAGE_SIZE` | `500` | Tracker page size |
| `SNAPSHOT_PAGE_CONCURRENCY` | `4` | parallel Tracker pages |
| `SNAPSHOT_MAX_RETRIES` | `5` | retries per page |

Example:

```bash
SNAPSHOT_START_YEAR=2024 \
SNAPSHOT_END_YEAR=2024 \
SNAPSHOT_PAGE_CONCURRENCY=8 \
docker compose up -d projector-snapshot-refresh
```

Logs:

```bash
docker compose logs -f projector-snapshot-refresh
```

Stop scheduler only:

```bash
docker compose stop projector-snapshot-refresh
```

Each refresh/write:

1. fetches Tracker jobs for the year/location
2. resolves skill labels
3. aggregates sectors, skills and job titles
4. writes a new versioned run
5. marks the run `completed`

## Demo Data

Migrations seed demo data for:

- years `2020-2024`
- global snapshots
- demo/regional snapshots

Reset demo DB:

```bash
docker compose down -v
docker compose up -d projector-db
```
