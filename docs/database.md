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

Recurring refresh:

```bash
python scripts/schedule_sectoral_snapshot_refresh.py --interval-months 3
```

This runs the backfill logic repeatedly. By default it refreshes the current year every 3 months.

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
